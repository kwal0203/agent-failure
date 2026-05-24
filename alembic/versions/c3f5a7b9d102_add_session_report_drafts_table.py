"""Add session_report_drafts table

Revision ID: c3f5a7b9d102
Revises: b2d4e6f8a901
Create Date: 2026-05-24 13:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c3f5a7b9d102"
down_revision: Union[str, Sequence[str], None] = "b2d4e6f8a901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "session_report_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("threat_model", sa.Text(), nullable=False, server_default=""),
        sa.Column("methodology", sa.Text(), nullable=False, server_default=""),
        sa.Column("evidence_and_results", sa.Text(), nullable=False, server_default=""),
        sa.Column("mitigations", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_session_report_drafts_session_id"),
    )
    op.create_index(
        "ix_session_report_drafts_session_id",
        "session_report_drafts",
        ["session_id"],
        unique=False,
    )
    op.alter_column("session_report_drafts", "executive_summary", server_default=None)
    op.alter_column("session_report_drafts", "threat_model", server_default=None)
    op.alter_column("session_report_drafts", "methodology", server_default=None)
    op.alter_column(
        "session_report_drafts", "evidence_and_results", server_default=None
    )
    op.alter_column("session_report_drafts", "mitigations", server_default=None)


def downgrade() -> None:
    op.drop_index(
        "ix_session_report_drafts_session_id", table_name="session_report_drafts"
    )
    op.drop_table("session_report_drafts")
