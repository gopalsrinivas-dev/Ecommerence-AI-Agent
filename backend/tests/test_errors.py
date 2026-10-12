import json
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.exceptions import DomainError
from app.db.session import managed_session
from app.main import app


@pytest.fixture
def client():
    # Isolated routes exercise the actual centralized handlers and middleware.
    probe = FastAPI()
    probe.exception_handlers.update(app.exception_handlers)
    probe.user_middleware = list(app.user_middleware)

    @probe.get("/failure")
    def fail(kind: int):
        if kind == 1:
            raise HTTPException(401, "secret-detail", headers={"WWW-Authenticate": "Bearer"})
        if kind == 2:
            raise DomainError("ORDER_NOT_CANCELLABLE", "This order cannot be cancelled.", 409)
        if kind == 3:
            raise OperationalError("secret SQL", {"password": "secret-value"}, Exception("secret-value"))
        if kind == 4:
            raise RuntimeError("secret-value")
        raise HTTPException(429, headers={"Retry-After": "7"})

    with TestClient(probe) as result:
        yield result


@pytest.mark.parametrize(
    "query,status,code,retryable",
    [
        ("invalid", 422, "INVALID_INPUT", False),
        ("1", 401, "HTTP_ERROR", False),
        ("2", 409, "ORDER_NOT_CANCELLABLE", False),
        ("3", 503, "DATABASE_UNAVAILABLE", True),
        ("4", 500, "INTERNAL_ERROR", False),
        ("5", 429, "HTTP_ERROR", True),
    ],
)
def test_envelopes(client, query, status, code, retryable):
    response = client.get("/failure", params={"kind": query})
    assert response.status_code == status
    body = response.json()
    assert body["error"]["code"] == code
    assert body["error"]["retryable"] is retryable
    assert body["error"]["message"]
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert response.headers["Cache-Control"] == "no-store"
    assert "secret" not in response.text
    if status == 401:
        assert response.headers["WWW-Authenticate"] == "Bearer"
    if status == 429:
        assert response.headers["Retry-After"] == "7"


@pytest.mark.parametrize(
    "kind,event_name,exception_type",
    [(4, "unexpected_error", "RuntimeError"), (3, "database_failed", "OperationalError")],
)
def test_unexpected_logged_once_with_safe_stack(client, caplog, kind, event_name, exception_type):
    response = client.get(f"/failure?kind={kind}")
    records = [
        json.loads(r.message) for r in caplog.records if json.loads(r.message).get("event") == event_name
    ]
    assert len(records) == 1
    record = records[0]
    assert record["request_id"] == response.json()["request_id"]
    assert record["exception_type"] == exception_type
    assert any(frame["function"] == "fail" for frame in record["stack_trace"])
    assert "secret-value" not in caplog.text


def test_failed_transaction_rolls_back_and_propagates():
    db = MagicMock()
    factory = MagicMock()
    factory.return_value.__enter__.return_value = db
    with pytest.raises(OperationalError):
        with managed_session(factory):
            raise OperationalError("query", {}, Exception("failure"))
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_rollback_failure_preserves_original_error(caplog):
    db = MagicMock()
    factory = MagicMock()
    factory.return_value.__enter__.return_value = db
    db.rollback.side_effect = RuntimeError("secret rollback detail")
    original = OperationalError("query", {}, Exception("original failure"))
    with pytest.raises(OperationalError) as raised:
        with managed_session(factory):
            raise original
    assert raised.value is original
    assert "transaction_rollback_failed" in caplog.text
    assert "secret rollback detail" not in caplog.text


@pytest.mark.parametrize(
    "timeout,code,status", [(True, "PROVIDER_TIMEOUT", 504), (False, "PROVIDER_UNAVAILABLE", 503)]
)
def test_provider_translation(monkeypatch, timeout, code, status):
    from openai import APIConnectionError, APITimeoutError

    from app.integrations import llm_client

    request = httpx.Request("POST", "https://example.test")
    error = APITimeoutError(request=request) if timeout else APIConnectionError(request=request)
    client = MagicMock()
    client.chat.completions.create.side_effect = error
    constructor = MagicMock()
    constructor.return_value.__enter__.return_value = client
    monkeypatch.setattr(llm_client, "OpenAI", constructor)
    with pytest.raises(DomainError) as raised:
        llm_client.OpenAIProvider().complete([], [], 1)
    assert (raised.value.code, raised.value.status, raised.value.retryable) == (code, status, True)


@pytest.mark.parametrize("boundary", ["audit", "commit"])
def test_failed_cancellation_is_rolled_back(store, monkeypatch, boundary):
    import uuid

    from sqlalchemy import select

    from app.models.action import PendingAction
    from app.models.audit_event import AuditEvent
    from app.services import order_service

    factory, data = store
    with factory() as db:
        action = order_service.prepare(db, data["a"], data["ca"], "ORD1004")
        db.commit()
    identity = uuid.UUID(action["id"])
    with pytest.raises(OperationalError):
        with managed_session(factory) as db:

            def broken(*args):
                raise OperationalError("secret SQL", {}, Exception("secret-value"))

            if boundary == "commit":
                monkeypatch.setattr(db, "commit", broken)
            else:
                original = order_service.audit

                def broken_audit(*args):
                    original(*args)
                    broken()

                monkeypatch.setattr(order_service, "audit", broken_audit)
            order_service.confirm(db, data["a"], identity)
    with factory() as db:
        assert order_service.status(db, data["a"], "ORD1004")["status"] == "PROCESSING"
        assert db.get(PendingAction, identity).state == "PENDING"
        assert db.scalar(select(AuditEvent)) is None


def test_cleanup_failure_preserves_original_provider_error(store, monkeypatch, caplog):
    import uuid

    from sqlalchemy import select

    from app.models.conversation import Conversation
    from app.models.turn import Turn
    from app.schemas.chat import ChatInput
    from app.services import chat_service

    factory, data = store

    def unavailable():
        raise OperationalError("secret SQL", {}, Exception("secret-value"))

    class BrokenProvider:
        def complete(self, *args):
            monkeypatch.setattr(chat_service, "SessionLocal", unavailable)
            raise DomainError("PROVIDER_UNAVAILABLE", "Please retry.", 503, True)

    monkeypatch.setattr(chat_service, "provider", lambda: BrokenProvider())
    with pytest.raises(DomainError, match="PROVIDER_UNAVAILABLE"):
        chat_service.send(
            data["a"],
            ChatInput(
                conversation_id=data["ca"],
                client_message_id=uuid.uuid4(),
                message="Where is ORD1001?",
            ),
        )
    assert "turn_cleanup_failed" in caplog.text
    assert "secret-value" not in caplog.text
    with factory() as db:
        # A failed cleanup leaves an expiring lease, never a false completed turn.
        assert db.get(Conversation, data["ca"]).lease_until is not None
        assert db.scalar(select(Turn)).state == "EXECUTING"


def test_committed_cancellation_survives_later_provider_failure(store, monkeypatch):
    import uuid

    from app.schemas.chat import ChatInput
    from app.services import chat_service, order_service

    factory, data = store
    with managed_session(factory) as db:
        action = order_service.prepare(db, data["a"], data["ca"], "ORD1004")
        db.commit()
        committed = order_service.confirm(db, data["a"], uuid.UUID(action["id"]))

    class Broken:
        def complete(self, *args):
            raise DomainError("PROVIDER_UNAVAILABLE", "Please retry.", 503, True)

    monkeypatch.setattr(chat_service, "provider", lambda: Broken())
    with pytest.raises(DomainError, match="PROVIDER_UNAVAILABLE"):
        chat_service.send(
            data["a"],
            ChatInput(
                conversation_id=data["ca"],
                client_message_id=uuid.uuid4(),
                message="Where is ORD1004?",
            ),
        )
    with factory() as db:
        assert order_service.status(db, data["a"], "ORD1004")["status"] == "CANCELLED"
        assert order_service.confirm(db, data["a"], uuid.UUID(action["id"])) == committed
