"""Add session_report_evidence table

Revision ID: 7f3c2a1d9b50
Revises: 6e8f1a2b3c40
Create Date: 2026-05-17 14:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "7f3c2a1d9b50"
down_revision: Union[str, Sequence[str], None] = "6e8f1a2b3c40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_report_evidence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column(
            "objective_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("why_it_matters", sa.Text(), nullable=True),
        sa.Column("default_priority", sa.String(length=16), nullable=False),
        sa.Column("student_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "evidence_type IN ('exploit_step', 'exploit_outcome', 'system_context', 'coaching_feedback', 'noise')",
            name="ck_session_report_evidence_type",
        ),
        sa.CheckConstraint(
            "default_priority IN ('high', 'medium', 'low')",
            name="ck_session_report_evidence_default_priority",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "event_id",
            name="uq_session_report_evidence_session_id_event_id",
        ),
    )
    op.create_index(
        "ix_session_report_evidence_session_id",
        "session_report_evidence",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_session_report_evidence_event_id",
        "session_report_evidence",
        ["event_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_session_report_evidence_event_id", table_name="session_report_evidence"
    )
    op.drop_index(
        "ix_session_report_evidence_session_id", table_name="session_report_evidence"
    )
    op.drop_table("session_report_evidence")
