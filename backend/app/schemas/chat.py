import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.action import ActionResponse
from app.schemas.base import StrictInput


class ChatInput(StrictInput):
    conversation_id: uuid.UUID
    client_message_id: uuid.UUID
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def nonblank_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message must contain text")
        return value


class ToolResult(BaseModel):
    found: bool = True
    order_id: str | None = None
    product_name: str | None = None
    status: str | None = None
    updated_at: str | None = None
    confirmation_required: bool = False
    action: dict | None = None
    error: str | None = None


class MessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    client_message_id: uuid.UUID | None = None
    action: ActionResponse | None = None


class MessagePage(BaseModel):
    items: list[MessageResponse]
    next_cursor: str | None


class ChatResponse(BaseModel):
    message: MessageResponse
    action: ActionResponse | None
    request_id: str


class ConversationResponse(BaseModel):
    conversation_id: uuid.UUID
