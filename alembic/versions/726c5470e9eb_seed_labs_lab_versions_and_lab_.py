"""seed labs lab_versions and lab objectives

Revision ID: 726c5470e9eb
Revises: 029317f25cc3
Create Date: 2026-04-17 18:12:13.162689

"""

from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "726c5470e9eb"
down_revision: Union[str, Sequence[str], None] = "029317f25cc3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LAB_1_ID = UUID("11111111-1111-1111-1111-111111111111")
LAB_2_ID = UUID("22222222-2222-2222-2222-222222222222")
LAB_3_ID = UUID("33333333-3333-3333-3333-333333333333")

LAB_1_VERSION_ID = UUID("11111111-1111-1111-1111-aaaaaaaaaaa1")
LAB_2_VERSION_ID = UUID("22222222-2222-2222-2222-aaaaaaaaaaa2")
LAB_3_VERSION_ID = UUID("33333333-3333-3333-3333-aaaaaaaaaaa3")

LAB_1_OBJECTIVE_1_ID = UUID("11111111-1111-1111-1111-bbbbbbbbb001")
LAB_1_OBJECTIVE_2_ID = UUID("11111111-1111-1111-1111-bbbbbbbbb002")
LAB_1_OBJECTIVE_3_ID = UUID("11111111-1111-1111-1111-bbbbbbbbb003")
LAB_2_OBJECTIVE_1_ID = UUID("22222222-2222-2222-2222-bbbbbbbbb001")
LAB_2_OBJECTIVE_2_ID = UUID("22222222-2222-2222-2222-bbbbbbbbb002")
LAB_2_OBJECTIVE_3_ID = UUID("22222222-2222-2222-2222-bbbbbbbbb003")
LAB_3_OBJECTIVE_1_ID = UUID("33333333-3333-3333-3333-bbbbbbbbb001")
LAB_3_OBJECTIVE_2_ID = UUID("33333333-3333-3333-3333-bbbbbbbbb002")
LAB_3_OBJECTIVE_3_ID = UUID("33333333-3333-3333-3333-bbbbbbbbb003")


def upgrade() -> None:
    """Upgrade schema."""
    labs = sa.table(
        "labs",
        sa.column("id", sa.UUID()),
        sa.column("slug", sa.String(length=128)),
        sa.column("name", sa.String(length=256)),
        sa.column("summary", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        labs,
        [
            {
                "id": LAB_1_ID,
                "slug": "prompt-injection",
                "name": "Prompt Injection",
                "summary": "Indirect prompt injection through an inbox workflow.",
                "is_active": True,
            },
            {
                "id": LAB_2_ID,
                "slug": "rag-poisoning",
                "name": "RAG Poisoning",
                "summary": "Poison retrieval content and observe model behavior.",
                "is_active": True,
            },
            {
                "id": LAB_3_ID,
                "slug": "tool-misuse",
                "name": "Tool Misuse",
                "summary": "Manipulate tool usage to trigger unsafe actions.",
                "is_active": True,
            },
        ],
    )

    lab_versions = sa.table(
        "lab_versions",
        sa.column("id", sa.UUID()),
        sa.column("lab_id", sa.UUID()),
        sa.column("version", sa.String(length=64)),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        lab_versions,
        [
            {
                "id": LAB_1_VERSION_ID,
                "lab_id": LAB_1_ID,
                "version": "v1",
                "is_active": True,
            },
            {
                "id": LAB_2_VERSION_ID,
                "lab_id": LAB_2_ID,
                "version": "v1",
                "is_active": True,
            },
            {
                "id": LAB_3_VERSION_ID,
                "lab_id": LAB_3_ID,
                "version": "v1",
                "is_active": True,
            },
        ],
    )

    lab_objectives = sa.table(
        "lab_objectives",
        sa.column("id", sa.UUID()),
        sa.column("lab_version_id", sa.UUID()),
        sa.column("objective_key", sa.String(length=64)),
        sa.column("label", sa.String(length=128)),
        sa.column("sort_order", sa.Integer()),
    )
    op.bulk_insert(
        lab_objectives,
        [
            {
                "id": LAB_1_OBJECTIVE_1_ID,
                "lab_version_id": LAB_1_VERSION_ID,
                "objective_key": "malicious_email_injected",
                "label": "Malicious email injected",
                "sort_order": 0,
            },
            {
                "id": LAB_1_OBJECTIVE_2_ID,
                "lab_version_id": LAB_1_VERSION_ID,
                "objective_key": "malicious_instructions_entered_context",
                "label": "Malicious instructions entered context",
                "sort_order": 1,
            },
            {
                "id": LAB_1_OBJECTIVE_3_ID,
                "lab_version_id": LAB_1_VERSION_ID,
                "objective_key": "token_exposed",
                "label": "Token Exposed",
                "sort_order": 2,
            },
            {
                "id": LAB_2_OBJECTIVE_1_ID,
                "lab_version_id": LAB_2_VERSION_ID,
                "objective_key": "poisoned_content_injected",
                "label": "Poisoned content injected",
                "sort_order": 0,
            },
            {
                "id": LAB_2_OBJECTIVE_2_ID,
                "lab_version_id": LAB_2_VERSION_ID,
                "objective_key": "poisoned_content_retrieved",
                "label": "Poisoned content retrieved",
                "sort_order": 1,
            },
            {
                "id": LAB_2_OBJECTIVE_3_ID,
                "lab_version_id": LAB_2_VERSION_ID,
                "objective_key": "unsafe_generation_triggered",
                "label": "Unsafe generation triggered",
                "sort_order": 2,
            },
            {
                "id": LAB_3_OBJECTIVE_1_ID,
                "lab_version_id": LAB_3_VERSION_ID,
                "objective_key": "malicious_tool_call_attempted",
                "label": "Malicious tool call attempted",
                "sort_order": 0,
            },
            {
                "id": LAB_3_OBJECTIVE_2_ID,
                "lab_version_id": LAB_3_VERSION_ID,
                "objective_key": "unauthorized_tool_action_executed",
                "label": "Unauthorized tool action executed",
                "sort_order": 1,
            },
            {
                "id": LAB_3_OBJECTIVE_3_ID,
                "lab_version_id": LAB_3_VERSION_ID,
                "objective_key": "impactful_tool_result_observed",
                "label": "Impactful tool result observed",
                "sort_order": 2,
            },
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            """
            DELETE FROM lab_objectives
            WHERE id IN (
                :lab1_obj1, :lab1_obj2, :lab1_obj3,
                :lab2_obj1, :lab2_obj2, :lab2_obj3,
                :lab3_obj1, :lab3_obj2, :lab3_obj3
            )
            """
        ).bindparams(
            lab1_obj1=LAB_1_OBJECTIVE_1_ID,
            lab1_obj2=LAB_1_OBJECTIVE_2_ID,
            lab1_obj3=LAB_1_OBJECTIVE_3_ID,
            lab2_obj1=LAB_2_OBJECTIVE_1_ID,
            lab2_obj2=LAB_2_OBJECTIVE_2_ID,
            lab2_obj3=LAB_2_OBJECTIVE_3_ID,
            lab3_obj1=LAB_3_OBJECTIVE_1_ID,
            lab3_obj2=LAB_3_OBJECTIVE_2_ID,
            lab3_obj3=LAB_3_OBJECTIVE_3_ID,
        )
    )
    op.execute(
        sa.text("DELETE FROM lab_versions WHERE id IN (:lv1, :lv2, :lv3)").bindparams(
            lv1=LAB_1_VERSION_ID,
            lv2=LAB_2_VERSION_ID,
            lv3=LAB_3_VERSION_ID,
        )
    )
    op.execute(
        sa.text("DELETE FROM labs WHERE id IN (:l1, :l2, :l3)").bindparams(
            l1=LAB_1_ID,
            l2=LAB_2_ID,
            l3=LAB_3_ID,
        )
    )
