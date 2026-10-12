import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.exceptions import DomainError
from app.core.security import digest
from app.models.action import PendingAction
from app.models.base import now
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.turn import Turn
from app.schemas.chat import ChatInput
from app.services import chat_service, order_service


def test_abandoned_same_turn_recovers_prepared_action(store, monkeypatch):
    factory, data = store
    message_id = uuid.uuid4()
    content = "Cancel ORD1004"
    with factory() as db:
        lease = uuid.uuid4()
        conversation = db.get(Conversation, data["ca"])
        conversation.lease_id = lease
        conversation.lease_until = now() - timedelta(seconds=1)
        turn = Turn(
            conversation_id=data["ca"],
            client_message_id=message_id,
            content_hash=digest(content),
            state="EXECUTING",
            lease_id=lease,
        )
        db.add(turn)
        db.flush()
        db.add(
            Message(conversation_id=data["ca"], client_message_id=message_id, role="user", content=content)
        )
        action = order_service.prepare(db, data["a"], data["ca"], "ORD1004", turn.id)
        db.commit()
    payload = ChatInput(conversation_id=data["ca"], client_message_id=message_id, message=content)
    result = chat_service.send(data["a"], payload)
    assert result["action"]["id"] == action["id"]
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(PendingAction)) == 1
        assert db.scalar(select(func.count()).select_from(Message)) == 2


def test_failed_turn_retry_keeps_client_id(store, monkeypatch):
    factory, data = store
    payload = ChatInput(
        conversation_id=data["ca"], client_message_id=uuid.uuid4(), message="Where is ORD1001?"
    )

    class Broken:
        def complete(self, *args):
            raise DomainError("PROVIDER_UNAVAILABLE", "Retry.", 503, True)

    from app.integrations.llm_client import MockProvider

    monkeypatch.setattr(chat_service, "provider", lambda: Broken())
    with pytest.raises(DomainError):
        chat_service.send(data["a"], payload)
    monkeypatch.setattr(chat_service, "provider", lambda: MockProvider())
    assert "SHIPPED" in chat_service.send(data["a"], payload)["message"]["content"]
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Message).where(Message.role == "user")) == 1


def test_committed_confirmation_never_calls_provider(store, monkeypatch):
    factory, data = store
    with factory() as db:
        action = order_service.prepare(db, data["a"], data["ca"], "ORD1004")
        db.commit()
    monkeypatch.setattr(
        chat_service, "provider", lambda: pytest.fail("No provider is allowed during confirmation")
    )
    with factory() as db:
        first = order_service.confirm(db, data["a"], uuid.UUID(action["id"]))
    with factory() as db:
        assert order_service.confirm(db, data["a"], uuid.UUID(action["id"])) == first


def test_recovered_action_completed_result_is_factual(store):
    factory, data = store
    from app.agents.orchestrator import execute_tool, factual

    with factory() as db:
        turn = Turn(
            conversation_id=data["ca"],
            client_message_id=uuid.uuid4(),
            content_hash=digest("Cancel"),
            state="FAILED",
            lease_id=uuid.uuid4(),
        )
        db.add(turn)
        db.flush()
        action = order_service.prepare(db, data["a"], data["ca"], "ORD1004", turn.id)
        db.commit()
        order_service.confirm(db, data["a"], uuid.UUID(action["id"]))
        result = execute_tool(db, data["a"], data["ca"], turn.id, "cancel_order", '{"order_id":"ORD1004"}')
        assert result.status == "CANCELLED" and not result.confirmation_required
        assert "CANCELLED" in factual(result) and "not been changed" not in factual(result)
