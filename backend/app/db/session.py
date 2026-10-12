from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import event, failure
from app.core.postgres import configure_libpq

configure_libpq(settings().postgres_bin)

engine = create_engine(
    settings().database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=10,
    connect_args={"connect_timeout": 5},
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


@sqlalchemy_event.listens_for(Session, "after_commit")
def log_committed(db):
    for name, fields in db.info.pop("log_events", []):
        event(name, **fields)


@sqlalchemy_event.listens_for(Session, "after_rollback")
@sqlalchemy_event.listens_for(Session, "after_soft_rollback")
def clear_log_events(db, *args):
    db.info.pop("log_events", None)


@contextmanager
def managed_session(factory):
    """Rollback failed units of work; services retain explicit commit points."""
    with factory() as db:
        try:
            yield db
        except BaseException:
            try:
                db.rollback()
            except Exception as rollback_error:
                failure("transaction_rollback_failed", rollback_error, "ROLLBACK_FAILED")
            raise
