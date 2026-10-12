from sqlalchemy import select

from app.core.exceptions import missing
from app.models.order import Order


def order(db, identity, actor, lock=False):
    query = select(Order).where(Order.order_id == identity, Order.customer_id == actor)
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise missing()
    return row


def orders_page(db, actor, limit, cursor):
    query = select(Order).where(Order.customer_id == actor)
    if cursor:
        query = query.where(Order.id > cursor)
    return list(db.scalars(query.order_by(Order.id).limit(limit + 1)))
