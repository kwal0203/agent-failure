"""Add pilot requests table

Revision ID: 2d6b4c8a9e10
Revises: 1f4e7a9c2b10
Create Date: 2026-05-16 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2d6b4c8a9e10"
down_revision: Union[str, Sequence[str], None] = "1f4e7a9c2b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "pilot_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("work_email", sa.String(length=254), nullable=False),
        sa.Column("university", sa.String(length=160), nullable=False),
        sa.Column("role", sa.String(length=120), nullable=True),
        sa.Column("course_name", sa.String(length=120), nullable=True),
        sa.Column("cohort_size", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_ip", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="new", nullable=False),
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
            "full_name <> ''", name="ck_pilot_requests_full_name_not_empty"
        ),
        sa.CheckConstraint(
            "work_email <> ''", name="ck_pilot_requests_work_email_not_empty"
        ),
        sa.CheckConstraint(
            "university <> ''", name="ck_pilot_requests_university_not_empty"
        ),
        sa.CheckConstraint("status <> ''", name="ck_pilot_requests_status_not_empty"),
        sa.CheckConstraint(
            "status IN ('new', 'contacted', 'approved', 'rejected')",
            name="ck_pilot_requests_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pilot_requests_work_email", "pilot_requests", ["work_email"], unique=False
    )
    op.create_index(
        "ix_pilot_requests_university", "pilot_requests", ["university"], unique=False
    )
    op.create_index(
        "ix_pilot_requests_source_ip", "pilot_requests", ["source_ip"], unique=False
    )
    op.create_index(
        "ix_pilot_requests_created_at", "pilot_requests", ["created_at"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_pilot_requests_created_at", table_name="pilot_requests")
    op.drop_index("ix_pilot_requests_source_ip", table_name="pilot_requests")
    op.drop_index("ix_pilot_requests_university", table_name="pilot_requests")
    op.drop_index("ix_pilot_requests_work_email", table_name="pilot_requests")
    op.drop_table("pilot_requests")
