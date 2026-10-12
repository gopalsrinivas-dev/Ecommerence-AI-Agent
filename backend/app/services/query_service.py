import uuid

from app.core.exceptions import DomainError
from app.core.logging import event
from app.repositories import health
from app.repositories import orders as orders_repo
from app.services.order_service import order_view


def orders(db, actor, limit, cursor):
    rows = orders_repo.orders_page(db, actor, limit, uuid.UUID(cursor) if cursor else None)
    event("orders_looked_up", actor_id=actor, count=min(len(rows), limit))
    return {
        "items": [order_view(row) for row in rows[:limit]],
        "next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None,
    }


def readiness(db):
    if not health.ready(db):
        raise DomainError(
            "DATABASE_NOT_READY", "Service is temporarily unavailable. Please retry.", 503, True
        )
    return {"status": "ready"}
