import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hasher
from app.models.base import Base
from app.models.conversation import Conversation
from app.models.order import Order
from app.models.user import User


@pytest.fixture
def store(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated PostgreSQL test database")
    if "test" not in url.rsplit("/", 1)[-1]:
        pytest.fail("Refusing schema reset: test database name must contain 'test'")
    engine = create_engine(url, pool_size=12)
    assert engine.dialect.name == "postgresql"
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    from app.api import dependencies
    from app.services import chat_service

    monkeypatch.setattr(chat_service, "SessionLocal", factory)
    monkeypatch.setattr(dependencies, "SessionLocal", factory)
    monkeypatch.setattr(settings(), "chat_rate_limit", 1000)
    monkeypatch.setattr(settings(), "auth_rate_limit", 1000)
    with factory() as db:
        a = User(email="a@example.test", password_hash=hasher.hash("password-a"))
        b = User(email="b@example.test", password_hash=hasher.hash("password-b"))
        db.add_all([a, b])
        db.flush()
        ca, cb = Conversation(customer_id=a.id), Conversation(customer_id=b.id)
        db.add_all([ca, cb])
        db.flush()
        for identity, owner, state in [
            ("ORD1004", a.id, "PROCESSING"),
            ("ORD1001", a.id, "SHIPPED"),
            ("ORD1002", b.id, "DELIVERED"),
            ("ORD1005", a.id, "PLACED"),
        ]:
            db.add(Order(order_id=identity, customer_id=owner, product_name="Test product", status=state))
        db.commit()
        data = {"a": a.id, "b": b.id, "ca": ca.id, "cb": cb.id}
    yield factory, data
    engine.dispose()
