"""Add instructor course memberships table

Revision ID: 5b7c9d1e2f30
Revises: 4a5b6c7d8e90
Create Date: 2026-05-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "5b7c9d1e2f30"
down_revision: str | None = "4a5b6c7d8e90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "instructor_course_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pilot_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instructor_email", sa.String(length=320), nullable=False),
        sa.Column("course_id", sa.String(length=128), nullable=False),
        sa.Column("course_name", sa.String(length=256), nullable=False),
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
            "instructor_email <> ''",
            name="ck_instructor_course_memberships_email_not_empty",
        ),
        sa.CheckConstraint(
            "course_id <> ''",
            name="ck_instructor_course_memberships_course_id_not_empty",
        ),
        sa.CheckConstraint(
            "course_name <> ''",
            name="ck_instructor_course_memberships_course_name_not_empty",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "instructor_email",
            "course_id",
            name="uq_instructor_course_memberships_email_course",
        ),
    )
    op.create_index(
        "ix_instructor_course_memberships_pilot_request_id",
        "instructor_course_memberships",
        ["pilot_request_id"],
        unique=False,
    )
    op.create_index(
        "ix_instructor_course_memberships_instructor_email",
        "instructor_course_memberships",
        ["instructor_email"],
        unique=False,
    )
    op.create_index(
        "ix_instructor_course_memberships_course_id",
        "instructor_course_memberships",
        ["course_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_instructor_course_memberships_course_id",
        table_name="instructor_course_memberships",
    )
    op.drop_index(
        "ix_instructor_course_memberships_instructor_email",
        table_name="instructor_course_memberships",
    )
    op.drop_index(
        "ix_instructor_course_memberships_pilot_request_id",
        table_name="instructor_course_memberships",
    )
    op.drop_table("instructor_course_memberships")
