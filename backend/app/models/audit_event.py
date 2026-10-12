import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Record


class AuditEvent(Record, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        UniqueConstraint("action_id", "event_type"),
        Index("ix_audit_order_created", "order_id", "created_at"),
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"))
    action_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pending_actions.id"))
    event_type: Mapped[str] = mapped_column(String(50))
    request_id: Mapped[str] = mapped_column(String(36))
    safe_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
