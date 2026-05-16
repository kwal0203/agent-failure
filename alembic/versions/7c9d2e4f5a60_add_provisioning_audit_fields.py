"""Add provisioning audit fields

Revision ID: 7c9d2e4f5a60
Revises: 6e8f1a2b3c40
Create Date: 2026-05-16 13:05:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "7c9d2e4f5a60"
down_revision = "6e8f1a2b3c40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pilot_request_provisions",
        sa.Column("class_code_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "pilot_request_provisions",
        sa.Column("provisioned_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "pilot_request_provisions",
        sa.Column("provisioning_correlation_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f("ix_pilot_request_provisions_class_code_id"),
        "pilot_request_provisions",
        ["class_code_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pilot_request_provisions_provisioned_by"),
        "pilot_request_provisions",
        ["provisioned_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_pilot_request_provisions_provisioning_correlation_id"),
        "pilot_request_provisions",
        ["provisioning_correlation_id"],
        unique=False,
    )

    op.execute(
        """
        UPDATE pilot_request_provisions prp
        SET class_code_id = cc.id
        FROM class_codes cc
        WHERE cc.code = prp.class_code
        """
    )
    op.alter_column("pilot_request_provisions", "class_code_id", nullable=False)

    op.add_column(
        "instructor_course_memberships",
        sa.Column("instructor_user_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "instructor_course_memberships",
        sa.Column("provisioned_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "instructor_course_memberships",
        sa.Column("provisioning_correlation_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f("ix_instructor_course_memberships_instructor_user_id"),
        "instructor_course_memberships",
        ["instructor_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_instructor_course_memberships_provisioned_by"),
        "instructor_course_memberships",
        ["provisioned_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_instructor_course_memberships_provisioning_correlation_id"),
        "instructor_course_memberships",
        ["provisioning_correlation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_instructor_course_memberships_provisioning_correlation_id"),
        table_name="instructor_course_memberships",
    )
    op.drop_index(
        op.f("ix_instructor_course_memberships_provisioned_by"),
        table_name="instructor_course_memberships",
    )
    op.drop_index(
        op.f("ix_instructor_course_memberships_instructor_user_id"),
        table_name="instructor_course_memberships",
    )
    op.drop_column("instructor_course_memberships", "provisioning_correlation_id")
    op.drop_column("instructor_course_memberships", "provisioned_by")
    op.drop_column("instructor_course_memberships", "instructor_user_id")

    op.drop_index(
        op.f("ix_pilot_request_provisions_provisioning_correlation_id"),
        table_name="pilot_request_provisions",
    )
    op.drop_index(
        op.f("ix_pilot_request_provisions_provisioned_by"),
        table_name="pilot_request_provisions",
    )
    op.drop_index(
        op.f("ix_pilot_request_provisions_class_code_id"),
        table_name="pilot_request_provisions",
    )
    op.drop_column("pilot_request_provisions", "provisioning_correlation_id")
    op.drop_column("pilot_request_provisions", "provisioned_by")
    op.drop_column("pilot_request_provisions", "class_code_id")
