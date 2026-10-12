import secrets

from fastapi import Depends, Request

from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.security import digest
from app.db.session import SessionLocal, managed_session
from app.services.auth_service import authenticate


def database():
    with managed_session(SessionLocal) as db:
        yield db


def origin(request: Request):
    if request.headers.get("origin") != settings().frontend_origin:
        raise DomainError("ORIGIN_REJECTED", "This request origin is not allowed.", 403)


def session(request: Request, db=Depends(database)):
    result = authenticate(db, request.cookies.get(settings().session_cookie_name))
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin(request)
        csrf = request.headers.get("x-csrf-token", "")
        if not csrf or not secrets.compare_digest(digest(csrf), result.csrf_hash):
            raise DomainError("CSRF_REJECTED", "Refresh the page and try again.", 403)
    return result
