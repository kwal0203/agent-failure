"""Add approved_provisioning_failed pilot request status

Revision ID: 6e8f1a2b3c40
Revises: 5b7c9d1e2f30
Create Date: 2026-05-16 12:30:00.000000
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "6e8f1a2b3c40"
down_revision = "5b7c9d1e2f30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_pilot_requests_status", "pilot_requests", type_="check")
    op.create_check_constraint(
        "ck_pilot_requests_status",
        "pilot_requests",
        "status IN ('new', 'contacted', 'approved', 'approved_provisioning_failed', 'rejected')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_pilot_requests_status", "pilot_requests", type_="check")
    op.create_check_constraint(
        "ck_pilot_requests_status",
        "pilot_requests",
        "status IN ('new', 'contacted', 'approved', 'rejected')",
    )
