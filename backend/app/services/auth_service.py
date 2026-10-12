from datetime import timedelta

from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.logging import bind_context, event
from app.core.security import DUMMY_HASH, digest, token, verify
from app.models.base import now
from app.models.session import Session
from app.repositories import rate_limits, sessions, users


def rate_limit(db, key, limit):
    window = int(now().timestamp()) // 60
    count = rate_limits.increment_rate(db, digest(key), window)
    db.commit()
    if count > limit:
        raise DomainError("RATE_LIMITED", "Too many requests. Please retry in a minute.", 429, True)


def login(db, email, password):
    user = users.user_by_email(db, email.strip().lower())
    valid = verify(password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid:
        raise DomainError("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)
    raw, csrf = token(), token()
    session = Session(
        user_id=user.id,
        token_hash=digest(raw),
        csrf_hash=digest(csrf),
        expires_at=now() + timedelta(seconds=settings().session_ttl_seconds),
    )
    db.add(session)
    db.commit()
    bind_context(actor_id=user.id)
    event("login_succeeded", actor_id=user.id)
    return user, raw, csrf


def authenticate(db, raw):
    if not raw:
        raise DomainError("UNAUTHENTICATED", "Please sign in to continue.", 401)
    session = sessions.active_session(db, digest(raw))
    if not session:
        raise DomainError("UNAUTHENTICATED", "Please sign in to continue.", 401)
    bind_context(actor_id=session.user_id)
    return session


def logout(db, session):
    session.revoked_at = now()
    db.commit()
    event("logout_succeeded", actor_id=session.user_id)


def profile(db, session):
    user = users.user_by_id(db, session.user_id)
    return {"user": {"id": str(user.id), "email": user.email}, "provider_mode": settings().provider_mode}
