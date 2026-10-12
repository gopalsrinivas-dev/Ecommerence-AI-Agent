from sqlalchemy import text


def ready(db):
    return db.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
