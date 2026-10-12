import asyncio
import json
import uuid
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.exc import OperationalError

from app.core import logging as logs
from app.core.exceptions import DomainError
from app.db.session import managed_session
from app.main import app
from app.services import order_service


def records(caplog, name=None):
    rows = [json.loads(r.getMessage()) for r in caplog.records if r.name == "support"]
    return [r for r in rows if name is None or r["event"] == name]


def test_actual_included_api_route_fields(caplog):
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.get("/api/v1/health/live?token=secret")
    assert response.status_code == 200
    row = records(caplog, "request_completed")[-1]
    assert row["route_template"] == row["path"] == "/api/v1/health/live"
    assert row["action"] == "live"
    assert "secret" not in json.dumps(records(caplog))


def test_concurrent_context_and_redaction(caplog):
    probe = FastAPI()
    probe.user_middleware = list(app.user_middleware)
    probe.exception_handlers.update(app.exception_handlers)

    @probe.get("/probe/{value}", name="order_lookup")
    async def endpoint(value: str):
        identity = logs.request_id.get()
        await asyncio.sleep(0.01)
        logs.event("provider_completed", password=value, message=value, order_id=value)
        return {"id": identity}

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=probe), base_url="http://test") as c:
            return await asyncio.gather(*(c.get(f"/probe/secret-{i}?token=secret") for i in range(8)))

    responses = asyncio.run(run())
    identities = {r.json()["id"] for r in responses}
    assert len(identities) == 8
    for r in responses:
        assert r.headers["x-request-id"] == r.json()["id"]
    for identity in identities:
        rows = [r for r in records(caplog) if r["request_id"] == identity]
        assert {r["event"] for r in rows} == {"request_started", "provider_completed", "request_completed"}
        for row in rows:
            assert row["method"] == "GET"
            assert row["path"] == row["route_template"] == "/probe/{value}"
            assert row["action"] == "order_lookup"
        completed = next(r for r in rows if r["event"] == "request_completed")
        assert type(completed["status_code"]) is int
        assert type(completed["duration_ms"]) is int
    assert "secret" not in json.dumps(records(caplog))
    assert logs.request_id.get() == "system"
    assert logs.request_context.get() == {}


def test_worker_context_reaches_errors(caplog):
    from fastapi.testclient import TestClient

    probe = FastAPI()
    probe.user_middleware = list(app.user_middleware)
    probe.exception_handlers.update(app.exception_handlers)
    actor, conversation = uuid.uuid4(), uuid.uuid4()

    @probe.get("/worker", name="chat")
    def worker():
        logs.bind_context(actor_id=actor, conversation_id=conversation)
        logs.event("provider_completed")
        raise RuntimeError("secret-provider-message")

    with TestClient(probe) as client:
        response = client.get("/worker")
    assert response.status_code == 500
    rows = records(caplog, "unexpected_error")
    assert len(rows) == 1
    row = rows[0]
    assert row["request_id"] == response.headers["x-request-id"]
    assert row["actor_id"] == str(actor) and row["conversation_id"] == str(conversation)
    assert row["action"] == "chat"
    assert "secret-provider-message" not in json.dumps(records(caplog))


def test_formats_and_logging_failure(monkeypatch, caplog):
    logs.event("probe", duration_ms=4, cookie="secret", actor_id="secret")
    row = records(caplog)[-1]
    assert "secret" not in json.dumps(row)
    record = next(r for r in reversed(caplog.records) if r.name == "support")
    text = logs.ConsoleFormatter().format(record)
    assert 'event="probe"' in text and "\n" not in text
    logs.configure_logging(SimpleNamespace(log_format="auto", app_env="production"))
    assert json.loads(logs.logger.handlers[0].format(record))["duration_ms"] == 4
    logs.configure_logging(SimpleNamespace(log_format="auto", app_env="development"))
    monkeypatch.setattr(logs.logger, "log", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("secret")))
    logs.event("probe")
    logs.failure("probe_failed", RuntimeError("secret"), "INTERNAL_ERROR")


@pytest.mark.parametrize("boundary", ["commit", "audit"])
def test_cancel_rollback_has_no_success(store, monkeypatch, caplog, boundary):
    factory, data = store
    with factory() as db:
        action = order_service.prepare(db, data["a"], data["ca"], "ORD1004")
        assert not records(caplog, "cancellation_prepared")
        db.rollback()
        db.commit()
        assert not records(caplog, "cancellation_prepared")
        action = order_service.prepare(db, data["a"], data["ca"], "ORD1004")
        db.commit()
        assert len(records(caplog, "cancellation_prepared")) == 1
    caplog.clear()

    def fail(*args):
        raise OperationalError("secret", {}, Exception("secret"))

    with pytest.raises(OperationalError), managed_session(factory) as db:
        if boundary == "commit":
            monkeypatch.setattr(db, "commit", fail)
        else:
            monkeypatch.setattr(order_service, "audit", fail)
        order_service.confirm(db, data["a"], uuid.UUID(action["id"]))
    assert not records(caplog, "cancellation_committed")


def test_cancel_commit_and_replay(store, caplog):
    factory, data = store
    with factory() as db:
        action = order_service.prepare(db, data["a"], data["ca"], "ORD1004")
        db.commit()
        order_service.confirm(db, data["a"], uuid.UUID(action["id"]))
        row = records(caplog, "cancellation_committed")[0]
        assert row["outcome"] == "mutated" and row["replay"] is False
        order_service.confirm(db, data["a"], uuid.UUID(action["id"]))
        assert len(records(caplog, "cancellation_committed")) == 1
        assert records(caplog, "cancellation_replayed")[0]["replay"] is True


def test_cancellation_dismissal_expiry_and_rejection(store, caplog):
    from datetime import timedelta

    from app.models.action import PendingAction
    from app.models.base import now

    factory, data = store
    with factory() as db:
        action = order_service.prepare(db, data["a"], data["ca"], "ORD1004")
        db.commit()
        identity = uuid.UUID(action["id"])
        order_service.dismiss(db, data["a"], identity)
        assert len(records(caplog, "cancellation_dismissed")) == 1
        with pytest.raises(DomainError):
            order_service.confirm(db, data["a"], identity)
        assert len(records(caplog, "cancellation_rejected")) == 1
        action = order_service.prepare(db, data["a"], data["ca"], "ORD1004")
        identity = uuid.UUID(action["id"])
        db.get(PendingAction, identity).expires_at = now() - timedelta(seconds=1)
        db.commit()
        with pytest.raises(DomainError):
            order_service.confirm(db, data["a"], identity)
        assert len(records(caplog, "cancellation_expired")) == 1
        assert not records(caplog, "cancellation_committed")
