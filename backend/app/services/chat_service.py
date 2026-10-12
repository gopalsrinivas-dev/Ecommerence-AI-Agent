import uuid
from datetime import timedelta

from app.agents.orchestrator import execute_tool, run
from app.core.config import settings
from app.core.exceptions import DomainError
from app.core.logging import bind_context, event, failure
from app.core.security import digest
from app.db.session import SessionLocal, managed_session
from app.integrations.llm_client import provider
from app.models.action import PendingAction
from app.models.base import now
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.turn import Turn
from app.repositories import conversations
from app.services.order_service import action_view


def create(db, actor):
    row = Conversation(customer_id=actor)
    db.add(row)
    db.commit()
    return {"conversation_id": str(row.id)}


def history(db, actor, identity, limit, cursor):
    conversations.conversation(db, identity, actor)
    rows = conversations.messages_page(db, identity, limit, cursor)
    # Pagination uses stable UUID ordering; UI sorts messages by creation time.
    result = []
    for row in rows[:limit]:
        action = db.get(PendingAction, row.action_id) if row.action_id else None
        result.append(
            {
                "id": str(row.id),
                "role": row.role,
                "content": row.content,
                "created_at": row.created_at.isoformat(),
                "client_message_id": str(row.client_message_id) if row.client_message_id else None,
                "action": action_view(db, action) if action else None,
            }
        )
    return {"items": result, "next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None}


def send(actor, payload):
    bind_context(actor_id=actor, conversation_id=payload.conversation_id)
    config = settings()
    lease = uuid.uuid4()
    with managed_session(SessionLocal) as db:
        conversation = conversations.conversation(db, payload.conversation_id, actor, True)
        turn = conversations.turn_for_message(db, conversation.id, payload.client_message_id)
        if turn and turn.content_hash != digest(payload.message):
            raise DomainError("MESSAGE_ID_REUSED", "Retry the original message or send a new one.", 409)
        if turn and turn.state == "COMPLETED":
            event("agent_turn_replayed", actor_id=actor, conversation_id=payload.conversation_id, replay=True)
            return turn.result
        if conversation.lease_until and conversation.lease_until > now():
            raise DomainError(
                "TURN_EXECUTING", "A message is still being processed. Retry shortly.", 409, True
            )
        conversation.lease_id = lease
        conversation.lease_until = now() + timedelta(seconds=config.chat_timeout_seconds + 5)
        if not turn:
            turn = Turn(
                conversation_id=conversation.id,
                client_message_id=payload.client_message_id,
                content_hash=digest(payload.message),
                state="EXECUTING",
                lease_id=lease,
            )
            db.add(turn)
            db.add(
                Message(
                    conversation_id=conversation.id,
                    client_message_id=payload.client_message_id,
                    role="user",
                    content=payload.message,
                )
            )
        else:
            turn.state, turn.lease_id = "EXECUTING", lease
        db.commit()
        turn_id = turn.id
        rows = conversations.recent_messages(db, conversation.id)
        context = [
            {"role": row.role, "content": row.content[:2000]}
            for row in reversed(rows)
            if row.client_message_id != payload.client_message_id
        ]
        context.append({"role": "user", "content": payload.message})
    event("agent_turn_started", actor_id=actor, conversation_id=payload.conversation_id)

    def tool(name, arguments):
        # Fence each tool against a recovered lease, with no locks held during provider calls.
        with managed_session(SessionLocal) as db:
            conversation = conversations.conversation(db, payload.conversation_id, actor, True)
            if conversation.lease_id != lease or conversation.lease_until <= now():
                raise DomainError("TURN_EXPIRED", "Please retry this message.", 409, True)
            result = execute_tool(db, actor, conversation.id, turn_id, name, arguments)
            db.commit()
            return result

    try:
        text, action = run(provider(), context, tool)
        with managed_session(SessionLocal) as db:
            conversation = conversations.conversation(db, payload.conversation_id, actor, True)
            if conversation.lease_id != lease:
                raise DomainError("TURN_EXPIRED", "Please retry this message.", 409, True)
            message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=text,
                action_id=uuid.UUID(action["id"]) if action else None,
            )
            db.add(message)
            db.flush()
            result = {
                "message": {
                    "id": str(message.id),
                    "role": "assistant",
                    "content": text,
                    "created_at": message.created_at.isoformat(),
                },
                "action": action,
            }
            turn = db.get(Turn, turn_id)
            assert turn is not None
            turn.state, turn.result = "COMPLETED", result
            conversation.lease_id = conversation.lease_until = None
            conversation.updated_at = now()
            db.commit()
            event("agent_turn_completed", actor_id=actor, conversation_id=payload.conversation_id)
            return result
    except Exception:
        # Cleanup is a separate transaction. Preserve the original operation error
        # if the database also fails while releasing this turn's lease.
        try:
            with managed_session(SessionLocal) as db:
                conversation = conversations.conversation(db, payload.conversation_id, actor, True)
                if conversation.lease_id == lease:
                    conversation.lease_id = conversation.lease_until = None
                    abandoned = db.get(Turn, turn_id)
                    assert abandoned is not None
                    abandoned.state = "FAILED"
                    db.commit()
        except Exception as cleanup_error:
            failure("turn_cleanup_failed", cleanup_error, "TURN_CLEANUP_FAILED")
        raise
