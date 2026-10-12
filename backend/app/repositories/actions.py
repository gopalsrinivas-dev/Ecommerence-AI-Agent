from sqlalchemy import select

from app.models.action import PendingAction
from app.repositories.base import owned


def action(db, identity, actor, lock=False):
    return owned(db, PendingAction, identity, actor, lock)


def action_for_turn(db, turn_id, order_id):
    return db.scalar(
        select(PendingAction).where(PendingAction.turn_id == turn_id, PendingAction.order_id == order_id)
    )
