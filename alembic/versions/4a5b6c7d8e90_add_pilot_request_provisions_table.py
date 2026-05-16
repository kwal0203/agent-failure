"""Add pilot request provisions table

Revision ID: 4a5b6c7d8e90
Revises: 2d6b4c8a9e10
Create Date: 2026-05-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "4a5b6c7d8e90"
down_revision: str | None = "2d6b4c8a9e10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pilot_request_provisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pilot_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", sa.String(length=128), nullable=False),
        sa.Column("course_name", sa.String(length=256), nullable=False),
        sa.Column("class_code", sa.String(length=128), nullable=False),
        sa.Column("instructor_email", sa.String(length=320), nullable=False),
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
            "course_id <> ''", name="ck_pilot_request_provisions_course_id_not_empty"
        ),
        sa.CheckConstraint(
            "course_name <> ''",
            name="ck_pilot_request_provisions_course_name_not_empty",
        ),
        sa.CheckConstraint(
            "class_code <> ''",
            name="ck_pilot_request_provisions_class_code_not_empty",
        ),
        sa.CheckConstraint(
            "instructor_email <> ''",
            name="ck_pilot_request_provisions_instructor_email_not_empty",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "pilot_request_id", name="uq_pilot_request_provisions_request_id"
        ),
    )
    op.create_index(
        "ix_pilot_request_provisions_pilot_request_id",
        "pilot_request_provisions",
        ["pilot_request_id"],
        unique=False,
    )
    op.create_index(
        "ix_pilot_request_provisions_class_code",
        "pilot_request_provisions",
        ["class_code"],
        unique=False,
    )
    op.create_index(
        "ix_pilot_request_provisions_instructor_email",
        "pilot_request_provisions",
        ["instructor_email"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pilot_request_provisions_instructor_email",
        table_name="pilot_request_provisions",
    )
    op.drop_index(
        "ix_pilot_request_provisions_class_code", table_name="pilot_request_provisions"
    )
    op.drop_index(
        "ix_pilot_request_provisions_pilot_request_id",
        table_name="pilot_request_provisions",
    )
    op.drop_table("pilot_request_provisions")
