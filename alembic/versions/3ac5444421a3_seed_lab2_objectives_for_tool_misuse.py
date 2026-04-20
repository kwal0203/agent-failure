"""seed lab2 objectives for tool misuse

Revision ID: 3ac5444421a3
Revises: 0d73cc5edecb
Create Date: 2026-04-20 11:14:32.907247

"""

from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3ac5444421a3"
down_revision: Union[str, Sequence[str], None] = "0d73cc5edecb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LAB_2_VERSION_ID = UUID("22222222-2222-2222-2222-aaaaaaaaaaa2")

NEW_OBJECTIVE_1_ID = UUID("22222222-2222-2222-2222-ccccccccc001")
NEW_OBJECTIVE_2_ID = UUID("22222222-2222-2222-2222-ccccccccc002")
NEW_OBJECTIVE_3_ID = UUID("22222222-2222-2222-2222-ccccccccc003")

OLD_OBJECTIVE_1_ID = UUID("22222222-2222-2222-2222-bbbbbbbbb001")
OLD_OBJECTIVE_2_ID = UUID("22222222-2222-2222-2222-bbbbbbbbb002")
OLD_OBJECTIVE_3_ID = UUID("22222222-2222-2222-2222-bbbbbbbbb003")


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            "DELETE FROM lab_objectives WHERE lab_version_id = :lab_version_id"
        ).bindparams(lab_version_id=LAB_2_VERSION_ID)
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
                "id": NEW_OBJECTIVE_1_ID,
                "lab_version_id": LAB_2_VERSION_ID,
                "objective_key": "unsafe_tool_invocation_triggered",
                "label": "Unsafe tool invocation triggered",
                "sort_order": 0,
            },
            {
                "id": NEW_OBJECTIVE_2_ID,
                "lab_version_id": LAB_2_VERSION_ID,
                "objective_key": "security_boundary_crossed",
                "label": "Security boundary crossed",
                "sort_order": 1,
            },
            {
                "id": NEW_OBJECTIVE_3_ID,
                "lab_version_id": LAB_2_VERSION_ID,
                "objective_key": "critical_file_deleted",
                "label": "Critical file deleted",
                "sort_order": 2,
            },
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            "DELETE FROM lab_objectives WHERE lab_version_id = :lab_version_id"
        ).bindparams(lab_version_id=LAB_2_VERSION_ID)
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
                "id": OLD_OBJECTIVE_1_ID,
                "lab_version_id": LAB_2_VERSION_ID,
                "objective_key": "poisoned_content_injected",
                "label": "Poisoned content injected",
                "sort_order": 0,
            },
            {
                "id": OLD_OBJECTIVE_2_ID,
                "lab_version_id": LAB_2_VERSION_ID,
                "objective_key": "poisoned_content_retrieved",
                "label": "Poisoned content retrieved",
                "sort_order": 1,
            },
            {
                "id": OLD_OBJECTIVE_3_ID,
                "lab_version_id": LAB_2_VERSION_ID,
                "objective_key": "unsafe_generation_triggered",
                "label": "Unsafe generation triggered",
                "sort_order": 2,
            },
        ],
    )
