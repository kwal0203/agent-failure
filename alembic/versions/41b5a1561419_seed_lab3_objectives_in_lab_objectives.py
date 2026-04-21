"""seed lab3 objectives in lab_objectives

Revision ID: 41b5a1561419
Revises: 5b065d788bda
Create Date: 2026-04-21 09:45:32.222503

"""

from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "41b5a1561419"
down_revision: Union[str, Sequence[str], None] = "5b065d788bda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _resolve_active_lab3_version_id(conn: sa.Connection) -> UUID:
    result = conn.execute(
        sa.text(
            """
            SELECT lv.id
            FROM lab_versions lv
            JOIN labs l ON l.id = lv.lab_id
            WHERE l.slug = :lab_slug
              AND l.is_active = true
              AND lv.is_active = true
            ORDER BY lv.created_at DESC
            LIMIT 1
            """
        ),
        {"lab_slug": "invoice-memory-poisoning"},
    ).scalar_one_or_none()

    if result is None:
        raise RuntimeError(
            "Cannot seed lab3 objectives: active lab_version for slug "
            "'invoice-memory-poisoning' not found."
        )
    if not isinstance(result, UUID):
        raise RuntimeError(
            "Cannot seed lab3 objectives: resolved lab_version_id is not a UUID."
        )
    return result


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    _ = _resolve_active_lab3_version_id(conn)


def downgrade() -> None:
    """Downgrade schema."""
    pass
