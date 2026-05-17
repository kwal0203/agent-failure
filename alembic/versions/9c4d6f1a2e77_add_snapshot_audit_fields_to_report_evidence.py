"""Add snapshot audit fields to session_report_evidence

Revision ID: 9c4d6f1a2e77
Revises: feca540e06df
Create Date: 2026-05-17 17:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9c4d6f1a2e77"
down_revision: Union[str, Sequence[str], None] = "feca540e06df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_report_evidence",
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "session_report_evidence",
        sa.Column("trace_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "session_report_evidence",
        sa.Column("event_index", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("session_report_evidence", "trace_version", server_default=None)
    op.alter_column("session_report_evidence", "event_index", server_default=None)


def downgrade() -> None:
    op.drop_column("session_report_evidence", "event_index")
    op.drop_column("session_report_evidence", "trace_version")
    op.drop_column("session_report_evidence", "details")
