"""Add report section fields to session_report_evidence

Revision ID: b2d4e6f8a901
Revises: 9c4d6f1a2e77
Create Date: 2026-05-24 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2d4e6f8a901"
down_revision: Union[str, Sequence[str], None] = "9c4d6f1a2e77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "session_report_evidence",
        sa.Column(
            "report_section",
            sa.String(length=64),
            nullable=False,
            server_default="unassigned",
        ),
    )
    op.add_column(
        "session_report_evidence",
        sa.Column("section_position", sa.Integer(), nullable=True),
    )
    op.alter_column("session_report_evidence", "report_section", server_default=None)


def downgrade() -> None:
    op.drop_column("session_report_evidence", "section_position")
    op.drop_column("session_report_evidence", "report_section")
