FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY pyproject.toml ./
# Stub src/ so setuptools.packages.find can resolve at install time.
RUN mkdir -p src && touch src/__init__.py
RUN pip install --upgrade pip wheel && pip install --no-cache-dir .


FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY alembic.ini manage.py ./
COPY alembic ./alembic
COPY src ./src

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && uvicorn src.main:app --host 0.0.0.0 --port 8000"]
