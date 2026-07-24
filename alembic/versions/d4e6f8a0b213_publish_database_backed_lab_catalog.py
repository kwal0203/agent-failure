"""Publish database-backed lab catalog.

Revision ID: d4e6f8a0b213
Revises: c3f5a7b9d102
Create Date: 2026-07-23 23:10:00.000000
"""

from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


revision: str = "d4e6f8a0b213"
down_revision: Union[str, Sequence[str], None] = "c3f5a7b9d102"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "labs",
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("labs", sa.Column("catalog_order", sa.Integer(), nullable=True))
    op.add_column(
        "labs",
        sa.Column(
            "supports_resume",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "labs",
        sa.Column(
            "supports_uploads",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_check_constraint(
        "ck_labs_catalog_order_non_negative",
        "labs",
        "catalog_order IS NULL OR catalog_order >= 0",
    )

    published_labs = (
        (
            "44444444-4444-4444-4444-444444444444",
            0,
            "Indirect Prompt Injection",
            "Attack an agent using indirect prompt injection via a malicious email.",
        ),
        (
            "55555555-5555-5555-5555-555555555555",
            1,
            "Tool Misuse",
            "Induce an LLM agent into unsafe tool operations via deceptive inputs.",
        ),
        (
            "66666666-6666-6666-6666-666666666666",
            2,
            "Memory Poisoning",
            "Poison an LLM agent's memory to reroute invoice payments to an attacker-controlled account.",
        ),
    )
    for lab_id, catalog_order, name, summary in published_labs:
        op.execute(
            sa.text(
                """
                UPDATE labs
                SET is_published = true,
                    catalog_order = :catalog_order,
                    name = :name,
                    summary = :summary
                WHERE id = :lab_id
                """
            ).bindparams(
                lab_id=UUID(lab_id),
                catalog_order=catalog_order,
                name=name,
                summary=summary,
            )
        )

    op.alter_column("labs", "is_published", server_default=None)
    op.alter_column("labs", "supports_resume", server_default=None)
    op.alter_column("labs", "supports_uploads", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_labs_catalog_order_non_negative", "labs", type_="check")
    op.drop_column("labs", "supports_uploads")
    op.drop_column("labs", "supports_resume")
    op.drop_column("labs", "catalog_order")
    op.drop_column("labs", "is_published")
