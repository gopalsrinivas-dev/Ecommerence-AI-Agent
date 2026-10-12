from datetime import timedelta

from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.logging import after_commit, bind_context, event, request_id
from app.models.action import PendingAction
from app.models.audit_event import AuditEvent
from app.models.base import now
from app.models.order import Order
from app.repositories import actions, base, conversations, orders


def order_view(row):
    return {
        "id": str(row.id),
        "order_id": row.order_id,
        "product_name": row.product_name,
        "status": row.status,
        "updated_at": row.updated_at.isoformat(),
        "version": row.version,
    }


def action_view(db, row):
    order = db.get(Order, row.order_id)
    return {
        "id": str(row.id),
        "type": row.type,
        "order_id": order.order_id,
        "product_name": order.product_name,
        "state": "EXPIRED" if row.state == "PENDING" and row.expires_at <= now() else row.state,
        "expires_at": row.expires_at.isoformat(),
        "result": row.result,
    }


def status(db, actor, identity):
    try:
        result = order_view(orders.order(db, identity, actor))
    except DomainError as exc:
        event("order_lookup_rejected", actor_id=actor, order_id=identity, error_code=exc.code)
        raise
    event("order_looked_up", actor_id=actor, order_id=result["order_id"])
    return result


def prepare(db, actor, conversation_id, identity, turn_id=None):
    try:
        conversations.conversation(db, conversation_id, actor)
        order = orders.order(db, identity, actor)
    except DomainError as exc:
        event(
            "cancellation_rejected",
            actor_id=actor,
            conversation_id=conversation_id,
            order_id=identity,
            error_code=exc.code,
        )
        raise
    if turn_id:
        previous = actions.action_for_turn(db, turn_id, order.id)
        if previous:
            event(
                "cancellation_prepared",
                actor_id=actor,
                action_id=previous.id,
                conversation_id=conversation_id,
                order_id=order.order_id,
                replay=True,
            )
            return action_view(db, previous)
    if order.status not in ("PLACED", "PROCESSING"):
        event(
            "cancellation_rejected",
            actor_id=actor,
            order_id=order.order_id,
            error_code="ORDER_NOT_CANCELLABLE",
        )
        raise DomainError(
            "ORDER_NOT_CANCELLABLE", "This order cannot be cancelled at its current stage.", 409
        )
    action = PendingAction(
        customer_id=actor,
        conversation_id=conversation_id,
        order_id=order.id,
        turn_id=turn_id,
        expires_at=now() + timedelta(seconds=settings().action_ttl_seconds),
    )
    db.add(action)
    db.flush()
    after_commit(
        db,
        "cancellation_prepared",
        actor_id=actor,
        action_id=action.id,
        conversation_id=conversation_id,
        order_id=order.order_id,
        replay=False,
    )
    return action_view(db, action)


def audit(db, actor, order, action):
    db.add(
        AuditEvent(
            actor_id=actor,
            order_id=order.id,
            action_id=action.id,
            event_type="cancellation_completed",
            request_id=request_id.get(),
            safe_metadata={},
        )
    )
    db.flush()


def confirm(db, actor, action_id):
    try:
        action = actions.action(db, action_id, actor, True)
    except DomainError as exc:
        event("cancellation_rejected", actor_id=actor, action_id=action_id, error_code=exc.code)
        raise
    bind_context(actor_id=actor, action_id=action.id, conversation_id=action.conversation_id)
    if action.state == "COMPLETED":
        event("cancellation_replayed", actor_id=actor, action_id=action.id, replay=True)
        return action.result
    if action.state == "EXPIRED" or action.expires_at <= now():
        action.state = "EXPIRED"
        db.commit()
        event("cancellation_expired", actor_id=actor, action_id=action.id)
        raise DomainError("ACTION_EXPIRED", "This confirmation expired. Please request a new one.", 410)
    if action.state != "PENDING" or action.type != "cancel_order":
        event("cancellation_rejected", actor_id=actor, action_id=action.id, error_code="ACTION_REJECTED")
        raise DomainError("ACTION_REJECTED", "This confirmation is no longer available.", 409)
    order = base.owned(db, Order, action.order_id, actor, True)
    already = order.status == "CANCELLED"
    if not already and order.status not in ("PLACED", "PROCESSING"):
        action.state = "REJECTED"
        db.commit()
        event(
            "cancellation_rejected",
            actor_id=actor,
            action_id=action.id,
            order_id=order.order_id,
            error_code="ORDER_NOT_CANCELLABLE",
        )
        raise DomainError(
            "ORDER_NOT_CANCELLABLE", "This order cannot be cancelled at its current stage.", 409
        )
    if not already:
        order.status = "CANCELLED"
        order.cancelled_at = order.updated_at = now()
        order.version += 1
        audit(db, actor, order, action)
    result = {
        "action_id": str(action.id),
        "state": "COMPLETED",
        "order_id": order.order_id,
        "order_status": "CANCELLED",
        "already_cancelled": already,
    }
    action.state, action.result, action.completed_at = "COMPLETED", result, now()
    db.commit()
    event(
        "cancellation_committed",
        actor_id=actor,
        action_id=action.id,
        conversation_id=action.conversation_id,
        order_id=order.order_id,
        outcome="already_cancelled" if already else "mutated",
        replay=False,
    )
    return result


def dismiss(db, actor, identity):
    try:
        action = actions.action(db, identity, actor, True)
    except DomainError as exc:
        event("cancellation_rejected", actor_id=actor, action_id=identity, error_code=exc.code)
        raise
    replay = action.state != "PENDING"
    if action.state == "PENDING":
        action.state = "EXPIRED" if action.expires_at <= now() else "REJECTED"
    db.commit()
    event(
        "cancellation_replayed"
        if replay
        else ("cancellation_expired" if action.state == "EXPIRED" else "cancellation_dismissed"),
        actor_id=actor,
        action_id=action.id,
        conversation_id=action.conversation_id,
        replay=replay,
    )
    return action_view(db, action)
