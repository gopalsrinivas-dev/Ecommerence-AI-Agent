import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from starlette.routing import Match

from app.api.router import router
from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.logging import configure_logging, event, failure, request_context, request_id
from app.schemas.error import ErrorDetail, ErrorResponse

app = FastAPI(title="Parcel Support API", version="1.0.0")
settings()
configure_logging(settings())
app.include_router(router)


def envelope(code, message, status, retryable=False, headers=None):
    if request_context.get().get("action") == "login":
        event("login_failed", error_code=code, status_code=status)
    headers = dict(headers or {})
    if status == 429 and not any(key.lower() == "retry-after" for key in headers):
        headers["Retry-After"] = "60"
    return JSONResponse(
        ErrorResponse(
            error=ErrorDetail(code=code, message=message, retryable=retryable),
            request_id=request_id.get(),
        ).model_dump(),
        status_code=status,
        headers=headers,
    )


@app.middleware("http")
async def context(request: Request, call_next):
    identity = str(uuid.uuid4())
    token = request_id.set(identity)
    # FastAPI may lazily wrap included routers; match their concrete API routes.
    candidates = [*router.routes, *request.app.routes] if request.app is app else request.app.routes
    route = next((r for r in candidates if r.matches(request.scope)[0] == Match.FULL), None)
    template = getattr(route, "path", "<unmatched>")
    context_token = request_context.set(
        {
            "method": request.method
            if request.method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
            else "OTHER",
            "path": template,
            "route_template": template,
            "action": getattr(route, "name", "unmatched"),
        }
    )
    started = time.monotonic()
    event("request_started")
    try:
        try:
            response = await call_next(request)
        except Exception as exc:
            # Catch inside request context to avoid an unsafe duplicate Uvicorn traceback.
            response = await unexpected(request, exc)
        response.headers["X-Request-ID"] = identity
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        event(
            "request_completed",
            duration_ms=round((time.monotonic() - started) * 1000),
            status_code=response.status_code,
        )
        return response
    finally:
        request_context.reset(context_token)
        request_id.reset(token)


@app.exception_handler(DomainError)
async def domain(request, exc):
    event("request_rejected", error_code=exc.code, status_code=exc.status)
    return envelope(exc.code, exc.message, exc.status, exc.retryable)


@app.exception_handler(RequestValidationError)
async def validation(request, exc):
    return envelope("INVALID_INPUT", "Please check the request fields.", 422)


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    failure("database_failed", exc, "DATABASE_UNAVAILABLE")
    return envelope("DATABASE_UNAVAILABLE", "Service is temporarily unavailable. Please retry.", 503, True)


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return envelope(
        "HTTP_ERROR",
        "This request could not be completed.",
        exc.status_code,
        exc.status_code in {429, 502, 503, 504},
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def unexpected(request, exc):
    failure("unexpected_error", exc, "INTERNAL_ERROR")
    return envelope("INTERNAL_ERROR", "Something went wrong. Please retry.", 500)
