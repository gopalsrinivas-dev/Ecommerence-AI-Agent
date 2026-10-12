import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import StrictInput


class OrderArgs(StrictInput):
    order_id: str = Field(pattern=r"^ORD[0-9]{1,16}$")


class OrderResponse(BaseModel):
    id: uuid.UUID
    order_id: str
    product_name: str
    status: str
    updated_at: datetime
    version: int


class OrderPage(BaseModel):
    items: list[OrderResponse]
    next_cursor: str | None
