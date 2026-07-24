"""Drop the database-backed worker heartbeat table.

Revision ID: f6b8d0e2a415
Revises: e5a7c9d1f304
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "f6b8d0e2a415"
down_revision: str | Sequence[str] | None = "e5a7c9d1f304"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("worker_heartbeats")


def downgrade() -> None:
    op.create_table(
        "worker_heartbeats",
        sa.Column("worker_name", sa.String(length=64), nullable=False),
        sa.Column(
            "last_tick_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("worker_name"),
    )
