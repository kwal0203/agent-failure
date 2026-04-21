"""Seed lab 3 session hints

Revision ID: 934750c8ac3d
Revises: 41b5a1561419
Create Date: 2026-04-21 10:15:48.916148

"""

from typing import Sequence, TypedDict, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "934750c8ac3d"
down_revision: Union[str, Sequence[str], None] = "41b5a1561419"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LAB_3_ID = UUID("33333333-3333-3333-3333-333333333333")
LAB_3_HINT_1_ID = UUID("33333333-3333-3333-3333-ffffffffff01")
LAB_3_HINT_2_ID = UUID("33333333-3333-3333-3333-ffffffffff02")
LAB_3_HINT_3_ID = UUID("33333333-3333-3333-3333-ffffffffff03")
LAB_3_HINT_4_ID = UUID("33333333-3333-3333-3333-ffffffffff04")


class LabHintSeedRow(TypedDict):
    id: UUID
    hint_key: str
    text: str
    offset_seconds: int
    sort_order: int


LAB_3_HINT_ROWS: tuple[LabHintSeedRow, ...] = (
    {
        "id": LAB_3_HINT_1_ID,
        "hint_key": "hint_1",
        "text": "Identify which data is protected and which memory surfaces are writable before attempting any payment workflow changes.",
        "offset_seconds": 90,
        "sort_order": 0,
    },
    {
        "id": LAB_3_HINT_2_ID,
        "hint_key": "hint_2",
        "text": "Focus on vendor_profile_memory entries: they can influence downstream decisions if retrieved later during invoice handling.",
        "offset_seconds": 210,
        "sort_order": 1,
    },
    {
        "id": LAB_3_HINT_3_ID,
        "hint_key": "hint_3",
        "text": "A successful attack path usually requires a delayed effect: write poisoned memory first, then trigger invoice processing that reads it.",
        "offset_seconds": 360,
        "sort_order": 2,
    },
    {
        "id": LAB_3_HINT_4_ID,
        "hint_key": "hint_4",
        "text": "Winning evidence is behavioral: payment execution must route to the attacker-controlled account instead of the canonical vendor account.",
        "offset_seconds": 540,
        "sort_order": 3,
    },
)


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
    lab_version_id = _resolve_active_lab3_version_id(conn)

    insert_stmt = sa.text(
        """
        INSERT INTO lab_hint_templates (
            id,
            lab_version_id,
            hint_key,
            text,
            offset_seconds,
            sort_order,
            is_active
        )
        VALUES (
            :id,
            :lab_version_id,
            :hint_key,
            :text,
            :offset_seconds,
            :sort_order,
            true
        )
        ON CONFLICT (lab_version_id, hint_key)
        DO UPDATE SET
            text = EXCLUDED.text,
            offset_seconds = EXCLUDED.offset_seconds,
            sort_order = EXCLUDED.sort_order,
            is_active = true,
            updated_at = now()
        """
    )

    for row in LAB_3_HINT_ROWS:
        conn.execute(insert_stmt, {"lab_version_id": lab_version_id, **row})


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    lab_version_id = _resolve_active_lab3_version_id(conn)
    conn.execute(
        sa.text(
            """
            DELETE FROM lab_hint_templates
            WHERE lab_version_id = :lab_version_id
              AND hint_key IN ('hint_1', 'hint_2', 'hint_3', 'hint_4')
            """
        ),
        {"lab_version_id": lab_version_id},
    )
