import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Record


class Message(Record, Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "client_message_id"),
        CheckConstraint("role IN ('user','assistant','tool')"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    client_message_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("pending_actions.id"))
