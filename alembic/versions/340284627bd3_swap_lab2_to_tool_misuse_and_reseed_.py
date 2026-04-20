"""swap lab2 to tool misuse and reseed lab3 objectives

Revision ID: 340284627bd3
Revises: 3ac5444421a3
Create Date: 2026-04-20 11:16:45.159719

"""

from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "340284627bd3"
down_revision: Union[str, Sequence[str], None] = "3ac5444421a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LAB_2_ID = UUID("22222222-2222-2222-2222-222222222222")
LAB_3_ID = UUID("33333333-3333-3333-3333-333333333333")
LAB_3_VERSION_ID = UUID("33333333-3333-3333-3333-aaaaaaaaaaa3")

LAB_3_RAG_OBJECTIVE_1_ID = UUID("33333333-3333-3333-3333-ddddddddd001")
LAB_3_RAG_OBJECTIVE_2_ID = UUID("33333333-3333-3333-3333-ddddddddd002")
LAB_3_RAG_OBJECTIVE_3_ID = UUID("33333333-3333-3333-3333-ddddddddd003")

LAB_3_TOOL_OBJECTIVE_1_ID = UUID("33333333-3333-3333-3333-bbbbbbbbb001")
LAB_3_TOOL_OBJECTIVE_2_ID = UUID("33333333-3333-3333-3333-bbbbbbbbb002")
LAB_3_TOOL_OBJECTIVE_3_ID = UUID("33333333-3333-3333-3333-bbbbbbbbb003")


def upgrade() -> None:
    """Upgrade schema."""
    # Swap metadata so Lab 2 is Tool Misuse and Lab 3 is RAG Poisoning.
    op.execute(
        sa.text(
            """
            UPDATE labs
            SET slug = :temp_slug
            WHERE id = :lab2_id
            """
        ).bindparams(temp_slug="rag-poisoning-temp", lab2_id=LAB_2_ID)
    )
    op.execute(
        sa.text(
            """
            UPDATE labs
            SET
              slug = :slug,
              name = :name,
              summary = :summary
            WHERE id = :lab3_id
            """
        ).bindparams(
            slug="rag-poisoning",
            name="RAG Poisoning",
            summary="Poison retrieval content and observe model behavior.",
            lab3_id=LAB_3_ID,
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE labs
            SET
              slug = :slug,
              name = :name,
              summary = :summary
            WHERE id = :lab2_id
            """
        ).bindparams(
            slug="tool-misuse",
            name="Tool Misuse",
            summary="Manipulate tool usage to trigger unsafe actions.",
            lab2_id=LAB_2_ID,
        )
    )

    # Reseed Lab 3 objectives to match new RAG Poisoning assignment.
    op.execute(
        sa.text(
            "DELETE FROM lab_objectives WHERE lab_version_id = :lab_version_id"
        ).bindparams(lab_version_id=LAB_3_VERSION_ID)
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
                "id": LAB_3_RAG_OBJECTIVE_1_ID,
                "lab_version_id": LAB_3_VERSION_ID,
                "objective_key": "poisoned_content_injected",
                "label": "Poisoned content injected",
                "sort_order": 0,
            },
            {
                "id": LAB_3_RAG_OBJECTIVE_2_ID,
                "lab_version_id": LAB_3_VERSION_ID,
                "objective_key": "poisoned_content_retrieved",
                "label": "Poisoned content retrieved",
                "sort_order": 1,
            },
            {
                "id": LAB_3_RAG_OBJECTIVE_3_ID,
                "lab_version_id": LAB_3_VERSION_ID,
                "objective_key": "unsafe_generation_triggered",
                "label": "Unsafe generation triggered",
                "sort_order": 2,
            },
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            """
            UPDATE labs
            SET slug = :temp_slug
            WHERE id = :lab2_id
            """
        ).bindparams(temp_slug="tool-misuse-temp", lab2_id=LAB_2_ID)
    )
    op.execute(
        sa.text(
            """
            UPDATE labs
            SET
              slug = :slug,
              name = :name,
              summary = :summary
            WHERE id = :lab3_id
            """
        ).bindparams(
            slug="tool-misuse",
            name="Tool Misuse",
            summary="Manipulate tool usage to trigger unsafe actions.",
            lab3_id=LAB_3_ID,
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE labs
            SET
              slug = :slug,
              name = :name,
              summary = :summary
            WHERE id = :lab2_id
            """
        ).bindparams(
            slug="rag-poisoning",
            name="RAG Poisoning",
            summary="Poison retrieval content and observe model behavior.",
            lab2_id=LAB_2_ID,
        )
    )

    op.execute(
        sa.text(
            "DELETE FROM lab_objectives WHERE lab_version_id = :lab_version_id"
        ).bindparams(lab_version_id=LAB_3_VERSION_ID)
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
                "id": LAB_3_TOOL_OBJECTIVE_1_ID,
                "lab_version_id": LAB_3_VERSION_ID,
                "objective_key": "malicious_tool_call_attempted",
                "label": "Malicious tool call attempted",
                "sort_order": 0,
            },
            {
                "id": LAB_3_TOOL_OBJECTIVE_2_ID,
                "lab_version_id": LAB_3_VERSION_ID,
                "objective_key": "unauthorized_tool_action_executed",
                "label": "Unauthorized tool action executed",
                "sort_order": 1,
            },
            {
                "id": LAB_3_TOOL_OBJECTIVE_3_ID,
                "lab_version_id": LAB_3_VERSION_ID,
                "objective_key": "impactful_tool_result_observed",
                "label": "Impactful tool result observed",
                "sort_order": 2,
            },
        ],
    )
