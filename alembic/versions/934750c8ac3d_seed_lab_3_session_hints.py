"""Seed lab 3 session hints

Revision ID: 934750c8ac3d
Revises: 41b5a1561419
Create Date: 2026-04-21 10:15:48.916148

"""

from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "934750c8ac3d"
down_revision: Union[str, Sequence[str], None] = "41b5a1561419"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LAB_3_ID = UUID("33333333-3333-3333-3333-333333333333")


def _resolve_active_lab3_version_id(conn: sa.Connection) -> UUID:
    result = conn.execute(
        sa.text(
            """
            SELECT lv.id
            FROM lab_versions lv
            JOIN labs l ON l.id = lv.lab_id
            WHERE lv.lab_id = :lab_id
              AND l.is_active = true
              AND lv.is_active = true
            ORDER BY lv.created_at DESC
            LIMIT 1
            """
        ),
        {"lab_id": LAB_3_ID},
    ).scalar_one_or_none()

    if result is None:
        raise RuntimeError(
            "Cannot seed lab3 hint templates: active lab_version for Lab 3 not found."
        )
    if not isinstance(result, UUID):
        raise RuntimeError(
            "Cannot seed lab3 hint templates: resolved lab_version_id is not UUID."
        )
    return result


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    _ = _resolve_active_lab3_version_id(conn)


def downgrade() -> None:
    """Downgrade schema."""
    pass
