"""Photo upload validation and storage for cleaning proof."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

UPLOADS_DIR = Path("/app/uploads")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png"}
# JPEG: FF D8 FF, PNG: 89 50 4E 47
MAGIC_BYTES = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89\x50\x4e\x47": "image/png",
}


async def validate_image(file: UploadFile) -> None:
    """Validate file is a real JPEG/PNG under 5 MB."""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Faqat JPEG yoki PNG formatidagi rasmlar qabul qilinadi",
        )

    # Read first 4 bytes to check magic
    header = await file.read(4)
    await file.seek(0)
    valid = any(header.startswith(magic) for magic in MAGIC_BYTES)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Fayl haqiqiy rasm emas",
        )

    # Check size by reading fully
    content = await file.read()
    await file.seek(0)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rasm hajmi 5 MB dan oshmasligi kerak",
        )


async def save_photo(file: UploadFile, room_id: uuid.UUID) -> str:
    """Save photo to disk. Returns relative path."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    short_id = uuid.uuid4().hex[:8]
    ext = "jpg" if file.content_type == "image/jpeg" else "png"
    relative_dir = f"housekeeping/{room_id}"
    filename = f"{timestamp}_{short_id}.{ext}"
    relative_path = f"{relative_dir}/{filename}"

    full_dir = UPLOADS_DIR / relative_dir
    full_dir.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    (full_dir / filename).write_bytes(content)

    return relative_path
