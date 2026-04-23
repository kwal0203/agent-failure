"""Add session feedback table

Revision ID: b1c6f0d7e2a9
Revises: aa4b2f6c1d9e
Create Date: 2026-04-23 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1c6f0d7e2a9"
down_revision: Union[str, Sequence[str], None] = "aa4b2f6c1d9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "session_feedback",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("feedback_key", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("trigger_event_index", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "feedback_key <> ''",
            name="ck_session_feedback_feedback_key_not_empty",
        ),
        sa.CheckConstraint(
            "reason_code <> ''",
            name="ck_session_feedback_reason_code_not_empty",
        ),
        sa.CheckConstraint(
            "message <> ''",
            name="ck_session_feedback_message_not_empty",
        ),
        sa.CheckConstraint(
            "severity in ('info', 'warning', 'error')",
            name="ck_session_feedback_severity",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_session_feedback_idempotency_key"
        ),
    )
    op.create_index(
        "ix_session_feedback_session_id",
        "session_feedback",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_session_feedback_idempotency_key",
        "session_feedback",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        "ix_session_feedback_session_id_created_at",
        "session_feedback",
        ["session_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_session_feedback_session_id_seen_at",
        "session_feedback",
        ["session_id", "seen_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_session_feedback_session_id_seen_at", table_name="session_feedback"
    )
    op.drop_index(
        "ix_session_feedback_session_id_created_at", table_name="session_feedback"
    )
    op.drop_index("ix_session_feedback_idempotency_key", table_name="session_feedback")
    op.drop_index("ix_session_feedback_session_id", table_name="session_feedback")
    op.drop_table("session_feedback")
