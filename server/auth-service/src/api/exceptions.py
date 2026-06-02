"""Global FastAPI exception handlers. No stack traces leak to clients."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.constants import TRACE_ID_HEADER
from src.core.security.jwt import InvalidTokenError
from src.services.auth_service import AuthenticationError

logger = logging.getLogger("auth-service.exceptions")


def _safe_response(status_code: int, code: str, message: str, trace_id: str | None) -> JSONResponse:
    body = {"error": code, "message": message}
    if trace_id:
        body["trace_id"] = trace_id
    return JSONResponse(status_code=status_code, content=body)


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthenticationError)
    async def _auth_error(request: Request, exc: AuthenticationError) -> JSONResponse:
        trace = request.headers.get(TRACE_ID_HEADER)
        return _safe_response(status.HTTP_401_UNAUTHORIZED, "unauthenticated", str(exc), trace)

    @app.exception_handler(InvalidTokenError)
    async def _bad_token(request: Request, exc: InvalidTokenError) -> JSONResponse:
        trace = request.headers.get(TRACE_ID_HEADER)
        return _safe_response(
            status.HTTP_401_UNAUTHORIZED, "invalid_token", "token is invalid or expired", trace
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        trace = request.headers.get(TRACE_ID_HEADER)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": "request payload failed validation",
                "details": exc.errors(),
                "trace_id": trace,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        trace = request.headers.get(TRACE_ID_HEADER)
        return _safe_response(
            exc.status_code,
            code=f"http_{exc.status_code}",
            message=str(exc.detail) if exc.detail else "",
            trace_id=trace,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        trace = request.headers.get(TRACE_ID_HEADER)
        logger.exception("unhandled exception", extra={"trace_id": trace})
        return _safe_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "an internal error occurred",
            trace,
        )
