"""Run periodically with the backend environment. Does not delete business audits or chat history."""

from sqlalchemy import delete, update

from app.core.config import settings
from app.core.logging import configure_logging, event
from app.db.session import SessionLocal
from app.models.action import PendingAction
from app.models.base import now
from app.models.rate_bucket import RateBucket
from app.models.session import Session


def cleanup():
    configure_logging(settings())
    with SessionLocal() as db:
        db.execute(delete(Session).where((Session.expires_at < now()) | Session.revoked_at.is_not(None)))
        db.execute(delete(RateBucket).where(RateBucket.window < int(now().timestamp()) // 60 - 2))
        expired = db.execute(
            update(PendingAction)
            .where(PendingAction.state == "PENDING", PendingAction.expires_at <= now())
            .values(state="EXPIRED")
            .returning(PendingAction.id, PendingAction.customer_id, PendingAction.conversation_id)
        ).all()
        db.commit()
        for action_id, actor_id, conversation_id in expired:
            event(
                "cancellation_expired",
                action_id=action_id,
                actor_id=actor_id,
                conversation_id=conversation_id,
            )
    print("Expired sessions, old rate windows, and pending action expiry processed.")


if __name__ == "__main__":
    cleanup()
