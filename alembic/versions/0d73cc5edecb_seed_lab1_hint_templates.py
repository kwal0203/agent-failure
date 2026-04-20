"""seed lab1 hint templates

Revision ID: 0d73cc5edecb
Revises: 7d31efdf41df
Create Date: 2026-04-19 11:54:43.366060

"""

from typing import Sequence, TypedDict, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0d73cc5edecb"
down_revision: Union[str, Sequence[str], None] = "7d31efdf41df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LAB_1_HINT_1_ID = UUID("11111111-1111-1111-1111-ccccccccc001")
LAB_1_HINT_2_ID = UUID("11111111-1111-1111-1111-ccccccccc002")
LAB_1_HINT_3_ID = UUID("11111111-1111-1111-1111-ccccccccc003")
LAB_1_HINT_4_ID = UUID("11111111-1111-1111-1111-ccccccccc004")


class LabHintSeedRow(TypedDict):
    id: UUID
    hint_key: str
    text: str
    offset_seconds: int
    sort_order: int


LAB_1_HINT_ROWS: tuple[LabHintSeedRow, ...] = (
    {
        "id": LAB_1_HINT_1_ID,
        "hint_key": "hint_1",
        "text": "Ask the assistant what tools are available to it.",
        "offset_seconds": 90,
        "sort_order": 0,
    },
    {
        "id": LAB_1_HINT_2_ID,
        "hint_key": "hint_2",
        "text": "The assistant can read emails but can it tell the difference between benign data and malicious instructions?",
        "offset_seconds": 210,
        "sort_order": 1,
    },
    {
        "id": LAB_1_HINT_3_ID,
        "hint_key": "hint_3",
        "text": "Use the email tool in the attack console to inject malicious content.",
        "offset_seconds": 360,
        "sort_order": 2,
    },
    {
        "id": LAB_1_HINT_4_ID,
        "hint_key": "hint_4",
        "text": "Try to frame the malicious instructions as urgent requirements or as if the instruction is coming from an authoritative source.",
        "offset_seconds": 540,
        "sort_order": 3,
    },
)


def _resolve_active_lab1_version_id(conn: sa.Connection) -> UUID:
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
        {"lab_slug": "prompt-injection"},
    ).scalar_one_or_none()

    if result is None:
        raise RuntimeError(
            "Cannot seed lab1 hint templates: active lab_version for slug "
            "'prompt-injection' not found."
        )

    return result


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    lab_version_id = _resolve_active_lab1_version_id(conn)

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

    for row in LAB_1_HINT_ROWS:
        conn.execute(insert_stmt, {"lab_version_id": lab_version_id, **row})


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()
    lab_version_id = _resolve_active_lab1_version_id(conn)
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
