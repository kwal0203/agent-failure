"""Add session completion fields

Revision ID: aa4b2f6c1d9e
Revises: 934750c8ac3d
Create Date: 2026-04-22 13:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aa4b2f6c1d9e"
down_revision: Union[str, Sequence[str], None] = "934750c8ac3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COMPLETION_STATUS_IN_PROGRESS = "in_progress"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "sessions",
        sa.Column(
            "completion_status",
            sa.String(length=32),
            nullable=True,
            server_default=COMPLETION_STATUS_IN_PROGRESS,
        ),
    )
    op.add_column(
        "sessions",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("completion_reason_code", sa.String(length=128), nullable=True),
    )

    op.execute(
        "UPDATE sessions SET completion_status = 'in_progress' "
        "WHERE completion_status IS NULL"
    )
    op.alter_column("sessions", "completion_status", nullable=False)
    op.create_check_constraint(
        "ck_sessions_completion_status",
        "sessions",
        "completion_status IN ('in_progress','completed_success','completed_failure')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_sessions_completion_status", "sessions", type_="check")
    op.drop_column("sessions", "completion_reason_code")
    op.drop_column("sessions", "completed_at")
    op.drop_column("sessions", "completion_status")
