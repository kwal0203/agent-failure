"""Allow pending runtime bindings without a base URL.

Revision ID: e5a7c9d1f304
Revises: d4e6f8a0b213
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "e5a7c9d1f304"
down_revision: str | Sequence[str] | None = "d4e6f8a0b213"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "session_runtime_bindings",
        "base_url",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.execute(
        sa.text(
            "UPDATE session_runtime_bindings "
            "SET base_url = NULL "
            "WHERE base_url = '' AND status IN ('provisioning', 'failed')"
        )
    )
    op.create_check_constraint(
        "ck_session_runtime_binding_ready_base_url",
        "session_runtime_bindings",
        "status != 'ready' OR (base_url IS NOT NULL AND length(trim(base_url)) > 0)",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TABLE session_runtime_bindings "
            "DROP CONSTRAINT IF EXISTS ck_session_runtime_binding_ready_base_url"
        )
    )
    op.execute(
        sa.text(
            "UPDATE session_runtime_bindings SET base_url = '' WHERE base_url IS NULL"
        )
    )
    op.alter_column(
        "session_runtime_bindings",
        "base_url",
        existing_type=sa.Text(),
        nullable=False,
    )
