import uuid
from datetime import datetime

from pydantic import BaseModel


class ActionResponse(BaseModel):
    id: uuid.UUID
    type: str
    order_id: str
    product_name: str
    state: str
    expires_at: datetime
    result: dict | None = None


class ConfirmationResponse(BaseModel):
    action_id: uuid.UUID
    state: str
    order_id: str
    order_status: str
    already_cancelled: bool
    request_id: str
