import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Record, now


class Order(Record, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("status IN ('PLACED','PROCESSING','SHIPPED','DELIVERED','CANCELLED')"),
        CheckConstraint("(status = 'CANCELLED') = (cancelled_at IS NOT NULL)"),
        Index("ix_orders_owner_created", "customer_id", "created_at"),
    )
    order_id: Mapped[str] = mapped_column(String(20), unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    product_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
