"""seed lab3 objectives in lab_objectives

Revision ID: 41b5a1561419
Revises: 5b065d788bda
Create Date: 2026-04-21 09:45:32.222503

"""

from typing import Sequence, TypedDict, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "41b5a1561419"
down_revision: Union[str, Sequence[str], None] = "5b065d788bda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LAB_3_OBJECTIVE_1_ID = UUID("33333333-3333-3333-3333-eeeeeeeee001")
LAB_3_OBJECTIVE_2_ID = UUID("33333333-3333-3333-3333-eeeeeeeee002")
LAB_3_OBJECTIVE_3_ID = UUID("33333333-3333-3333-3333-eeeeeeeee003")
LAB_1_ID = UUID("11111111-1111-1111-1111-111111111111")
LAB_2_ID = UUID("22222222-2222-2222-2222-222222222222")
LAB_3_ID = UUID("33333333-3333-3333-3333-333333333333")


class LabObjectiveSeedRow(TypedDict):
    id: UUID
    objective_key: str
    label: str
    sort_order: int


def _resolve_active_lab3_version_id(conn: sa.Connection) -> UUID:
    raw_result = conn.execute(
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

    if raw_result is None:
        raise RuntimeError(
            "Cannot seed lab3 objectives: active lab_version for Lab 3 ID "
            "'33333333-3333-3333-3333-333333333333' not found."
        )
    result = raw_result
    if not isinstance(result, UUID):
        raise RuntimeError(
            "Cannot seed lab3 objectives: resolved lab_version_id is not a UUID."
        )
    return result


def _normalize_canonical_labs(conn: sa.Connection) -> None:
    conn.execute(
        sa.text(
            """
            UPDATE labs
            SET slug = :slug, name = :name, summary = :summary
            WHERE id = :lab_id
            """
        ),
        {
            "lab_id": LAB_1_ID,
            "slug": "prompt-injection",
            "name": "Prompt Injection",
            "summary": "Indirect prompt injection through an inbox workflow.",
        },
    )
    conn.execute(
        sa.text(
            """
            UPDATE labs
            SET slug = :slug, name = :name, summary = :summary
            WHERE id = :lab_id
            """
        ),
        {
            "lab_id": LAB_2_ID,
            "slug": "tool-misuse",
            "name": "Tool Misuse",
            "summary": "Manipulate tool usage to trigger unsafe actions.",
        },
    )
    conn.execute(
        sa.text(
            """
            UPDATE labs
            SET slug = :slug, name = :name, summary = :summary
            WHERE id = :lab_id
            """
        ),
        {
            "lab_id": LAB_3_ID,
            "slug": "memory-poisoning",
            "name": "Memory Poisoning",
            "summary": "Poison memory signals to reroute invoice payment decisions.",
        },
    )


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    _normalize_canonical_labs(conn)

    lab_version_id = _resolve_active_lab3_version_id(conn)

    # Replace prior objectives for this lab version so sort_order/objective_key
    # constraints cannot conflict with historical Lab 3 definitions.
    conn.execute(
        sa.text(
            """
            DELETE FROM lab_objectives
            WHERE lab_version_id = :lab_version_id
            """
        ),
        {"lab_version_id": lab_version_id},
    )

    insert_stmt = sa.text(
        """
        INSERT INTO lab_objectives (
            id,
            lab_version_id,
            objective_key,
            label,
            sort_order
        )
        VALUES (
            :id,
            :lab_version_id,
            :objective_key,
            :label,
            :sort_order
        )
        ON CONFLICT (lab_version_id, objective_key)
        DO UPDATE SET
            label = EXCLUDED.label,
            sort_order = EXCLUDED.sort_order
        """
    )

    rows: tuple[LabObjectiveSeedRow, ...] = (
        {
            "id": LAB_3_OBJECTIVE_1_ID,
            "objective_key": "malicious_vendor_memory_written",
            "label": "Malicious Vendor Memory Written",
            "sort_order": 0,
        },
        {
            "id": LAB_3_OBJECTIVE_2_ID,
            "objective_key": "poisoned_memory_retrieved_for_invoice",
            "label": "Poisoned Memory Retrieved For Invoice",
            "sort_order": 1,
        },
        {
            "id": LAB_3_OBJECTIVE_3_ID,
            "objective_key": "payment_routed_to_attacker_account",
            "label": "Payment Routed To Attacker Account",
            "sort_order": 2,
        },
    )

    for row in rows:
        conn.execute(insert_stmt, {"lab_version_id": lab_version_id, **row})


def downgrade() -> None:
    """Downgrade schema."""
    pass
