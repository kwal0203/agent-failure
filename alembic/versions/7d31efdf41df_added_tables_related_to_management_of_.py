"""Added tables related to management of hint system state

Revision ID: 7d31efdf41df
Revises: 726c5470e9eb
Create Date: 2026-04-19 11:49:47.371405

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7d31efdf41df"
down_revision: Union[str, Sequence[str], None] = "726c5470e9eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # NOTE: keep this migration focused on hint tables only.
    # Any lab_objectives/sort_order operations were autogenerate drift noise.
    op.create_table(
        "session_hints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("hint_key", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("unlock_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "hint_key <> ''", name="ck_session_hints_hint_key_not_empty"
        ),
        sa.CheckConstraint(
            "status in ('pending', 'unlocked')", name="ck_session_hints_status"
        ),
        sa.CheckConstraint("text <> ''", name="ck_session_hints_text_not_empty"),
        sa.CheckConstraint("sort_order >= 0", name="ck_session_hints_sort_nonnegative"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "hint_key", name="uq_session_hints_session_key"
        ),
    )
    op.create_index(
        op.f("ix_session_hints_session_id"),
        "session_hints",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_session_hints_updated_at"),
        "session_hints",
        ["updated_at"],
        unique=False,
    )
    op.create_table(
        "lab_hint_templates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lab_version_id", sa.UUID(), nullable=False),
        sa.Column("hint_key", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("offset_seconds", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
            "hint_key <> ''", name="ck_lab_hint_templates_hint_key_not_empty"
        ),
        sa.CheckConstraint("text <> ''", name="ck_lab_hint_templates_text_not_empty"),
        sa.CheckConstraint(
            "offset_seconds >= 0", name="ck_lab_hint_templates_offset_nonnegative"
        ),
        sa.CheckConstraint(
            "sort_order >= 0", name="ck_lab_hint_templates_sort_nonnegative"
        ),
        sa.ForeignKeyConstraint(
            ["lab_version_id"], ["lab_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "lab_version_id", "hint_key", name="uq_lab_hint_templates_version_key"
        ),
        sa.UniqueConstraint(
            "lab_version_id", "sort_order", name="uq_lab_hint_templates_version_sort"
        ),
    )
    op.create_index(
        op.f("ix_lab_hint_templates_lab_version_id"),
        "lab_hint_templates",
        ["lab_version_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_lab_hint_templates_lab_version_id"), table_name="lab_hint_templates"
    )
    op.drop_table("lab_hint_templates")
    op.drop_index(op.f("ix_session_hints_updated_at"), table_name="session_hints")
    op.drop_index(op.f("ix_session_hints_session_id"), table_name="session_hints")
    op.drop_table("session_hints")
