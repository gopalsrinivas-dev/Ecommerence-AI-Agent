"""Generate a self-contained initial migration against an empty scratch database."""

from pathlib import Path

from alembic.autogenerate import produce_migrations, render_python_code
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.models.base import Base


def freeze(url):
    engine = create_engine(url)
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        migration = produce_migrations(context, Base.metadata)
        upgrade = render_python_code(migration.upgrade_ops).replace(
            "astext_type=Text()", "astext_type=sa.Text()"
        )
        downgrade = render_python_code(migration.downgrade_ops)
    header = '''"""Initial PostgreSQL schema."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
'''
    Path("migrations/versions/0001_initial.py").write_text(
        header + upgrade + "\n\n\ndef downgrade():\n" + downgrade + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    import sys

    freeze(sys.argv[1])
