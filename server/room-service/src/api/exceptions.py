"""Global FastAPI exception handlers.

Every error path leaves the building through one of these handlers so the
client receives a structured, predictable JSON shape and never a raw stack
trace.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.security.jwt import InvalidTokenError

logger = logging.getLogger("room-service.exceptions")
TRACE_HEADER = "X-Request-Id"


def _safe(status_code: int, code: str, message: str, trace: str | None) -> JSONResponse:
    body = {"error": code, "message": message}
    if trace:
        body["trace_id"] = trace
    return JSONResponse(status_code=status_code, content=body)


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidTokenError)
    async def _bad_token(request: Request, exc: InvalidTokenError) -> JSONResponse:
        return _safe(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_token",
            "token is invalid or expired",
            request.headers.get(TRACE_HEADER),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": "request payload failed validation",
                "details": exc.errors(),
                "trace_id": request.headers.get(TRACE_HEADER),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        trace = request.headers.get(TRACE_HEADER)
        # If the endpoint passed a structured detail (dict) — e.g. the
        # "no_rooms_available" 409 — surface it verbatim. Otherwise fall
        # back to the generic shape.
        if isinstance(exc.detail, dict):
            body = {**exc.detail}
            if trace and "trace_id" not in body:
                body["trace_id"] = trace
            return JSONResponse(status_code=exc.status_code, content=body)
        return _safe(
            exc.status_code,
            f"http_{exc.status_code}",
            str(exc.detail) if exc.detail else "",
            trace,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        trace = request.headers.get(TRACE_HEADER)
        logger.exception("unhandled exception", extra={"trace_id": trace})
        return _safe(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "an internal error occurred",
            trace,
        )
