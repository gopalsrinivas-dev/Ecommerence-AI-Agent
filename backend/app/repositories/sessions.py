from sqlalchemy import select

from app.models.base import now
from app.models.session import Session


def active_session(db, token_hash):
    return db.scalar(
        select(Session).where(
            Session.token_hash == token_hash, Session.revoked_at.is_(None), Session.expires_at > now()
        )
    )
