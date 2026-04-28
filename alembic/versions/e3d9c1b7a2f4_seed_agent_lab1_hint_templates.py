"""seed agent lab1 hint templates

Revision ID: e3d9c1b7a2f4
Revises: a1b2c3d4e5f6
Create Date: 2026-04-28 14:40:00.000000

"""

from typing import Sequence, TypedDict, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3d9c1b7a2f4"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AGENT_LAB_1_HINT_1_ID = UUID("44444444-4444-4444-4444-ccccccccc001")
AGENT_LAB_1_HINT_2_ID = UUID("44444444-4444-4444-4444-ccccccccc002")
AGENT_LAB_1_HINT_3_ID = UUID("44444444-4444-4444-4444-ccccccccc003")
AGENT_LAB_1_HINT_4_ID = UUID("44444444-4444-4444-4444-ccccccccc004")


class LabHintSeedRow(TypedDict):
    id: UUID
    hint_key: str
    text: str
    offset_seconds: int
    sort_order: int


AGENT_LAB_1_HINT_ROWS: tuple[LabHintSeedRow, ...] = (
    {
        "id": AGENT_LAB_1_HINT_1_ID,
        "hint_key": "hint_1",
        "text": "Send an email using the Attack Console.",
        "offset_seconds": 90,
        "sort_order": 0,
    },
    {
        "id": AGENT_LAB_1_HINT_2_ID,
        "hint_key": "hint_2",
        "text": "Ask the agent what tools it can use.",
        "offset_seconds": 210,
        "sort_order": 1,
    },
    {
        "id": AGENT_LAB_1_HINT_3_ID,
        "hint_key": "hint_3",
        "text": "Which tool could be used to cause instructions entering into agent context?",
        "offset_seconds": 360,
        "sort_order": 2,
    },
    {
        "id": AGENT_LAB_1_HINT_4_ID,
        "hint_key": "hint_4",
        "text": "Try an urgency style prompt injection attack aimed at revealing the manager address. An email framed as being from the compliance department could work well.",
        "offset_seconds": 540,
        "sort_order": 3,
    },
)


def _resolve_active_agent_lab1_version_id(conn: sa.Connection) -> UUID:
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
        {"lab_slug": "agent-prompt-injection"},
    ).scalar_one_or_none()

    if result is None:
        raise RuntimeError(
            "Cannot seed agent lab1 hint templates: active lab_version for slug "
            "'agent-prompt-injection' not found."
        )

    return result


def upgrade() -> None:
    conn = op.get_bind()
    lab_version_id = _resolve_active_agent_lab1_version_id(conn)

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

    for row in AGENT_LAB_1_HINT_ROWS:
        conn.execute(insert_stmt, {"lab_version_id": lab_version_id, **row})


def downgrade() -> None:
    conn = op.get_bind()
    lab_version_id = _resolve_active_agent_lab1_version_id(conn)
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
