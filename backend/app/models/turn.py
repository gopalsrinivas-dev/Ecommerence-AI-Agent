import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Record


class Turn(Record, Base):
    __tablename__ = "chat_turns"
    __table_args__ = (
        UniqueConstraint("conversation_id", "client_message_id"),
        CheckConstraint("state IN ('EXECUTING','COMPLETED','FAILED')"),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    client_message_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    content_hash: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(20))
    lease_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    result: Mapped[dict | None] = mapped_column(JSONB)
