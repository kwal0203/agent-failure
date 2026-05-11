"""Add enrollment tables

Revision ID: 1f4e7a9c2b10
Revises: 9f2b6a1c4d77
Create Date: 2026-05-10 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1f4e7a9c2b10"
down_revision: Union[str, Sequence[str], None] = "9f2b6a1c4d77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "class_codes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("course_id", sa.String(length=128), nullable=False),
        sa.Column("course_name", sa.String(length=256), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("uses", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "status", sa.String(length=32), server_default="active", nullable=False
        ),
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
        sa.CheckConstraint("code <> ''", name="ck_class_codes_code_not_empty"),
        sa.CheckConstraint(
            "course_id <> ''", name="ck_class_codes_course_id_not_empty"
        ),
        sa.CheckConstraint(
            "course_name <> ''", name="ck_class_codes_course_name_not_empty"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_class_codes_code"),
    )
    op.create_index("ix_class_codes_code", "class_codes", ["code"], unique=False)
    op.create_index(
        "ix_class_codes_course_id", "class_codes", ["course_id"], unique=False
    )

    op.create_table(
        "enrollment_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("nonce", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("course_id", sa.String(length=128), nullable=False),
        sa.Column("course_name", sa.String(length=256), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nonce", name="uq_enrollment_tokens_nonce"),
    )
    op.create_index(
        "ix_enrollment_tokens_nonce", "enrollment_tokens", ["nonce"], unique=False
    )
    op.create_index(
        "ix_enrollment_tokens_email", "enrollment_tokens", ["email"], unique=False
    )
    op.create_index(
        "ix_enrollment_tokens_course_id",
        "enrollment_tokens",
        ["course_id"],
        unique=False,
    )

    op.create_table(
        "enrollments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_sub", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("course_id", sa.String(length=128), nullable=False),
        sa.Column("course_name", sa.String(length=256), nullable=False),
        sa.Column(
            "source", sa.String(length=32), server_default="class_code", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_sub", "course_id", name="uq_enrollments_user_course"),
    )
    op.create_index(
        "ix_enrollments_user_sub", "enrollments", ["user_sub"], unique=False
    )
    op.create_index("ix_enrollments_user_id", "enrollments", ["user_id"], unique=False)
    op.create_index("ix_enrollments_email", "enrollments", ["email"], unique=False)
    op.create_index(
        "ix_enrollments_course_id", "enrollments", ["course_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_enrollments_course_id", table_name="enrollments")
    op.drop_index("ix_enrollments_email", table_name="enrollments")
    op.drop_index("ix_enrollments_user_id", table_name="enrollments")
    op.drop_index("ix_enrollments_user_sub", table_name="enrollments")
    op.drop_table("enrollments")

    op.drop_index("ix_enrollment_tokens_course_id", table_name="enrollment_tokens")
    op.drop_index("ix_enrollment_tokens_email", table_name="enrollment_tokens")
    op.drop_index("ix_enrollment_tokens_nonce", table_name="enrollment_tokens")
    op.drop_table("enrollment_tokens")

    op.drop_index("ix_class_codes_course_id", table_name="class_codes")
    op.drop_index("ix_class_codes_code", table_name="class_codes")
    op.drop_table("class_codes")
