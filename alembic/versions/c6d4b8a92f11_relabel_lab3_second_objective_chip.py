"""relabel_lab3_second_objective_chip

Revision ID: c6d4b8a92f11
Revises: 7a2b8c1f4d90
Create Date: 2026-04-26 15:05:00.000000

"""

from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c6d4b8a92f11"
down_revision: Union[str, Sequence[str], None] = "7a2b8c1f4d90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LAB_3_VERSION_ID = UUID("33333333-3333-3333-3333-aaaaaaaaaaa3")
LAB_3_OBJECTIVE_KEY = "poisoned_memory_retrieved_for_invoice"
NEW_LABEL = "Malicious instruction retrieved"
OLD_LABEL = "Poisoned Memory Retrieved For Invoice"


def _update_label(*, label: str) -> None:
    op.execute(
        sa.text(
            """
            UPDATE lab_objectives
            SET label = :label
            WHERE lab_version_id = :lab_version_id
              AND objective_key = :objective_key
            """
        ).bindparams(
            lab_version_id=LAB_3_VERSION_ID,
            objective_key=LAB_3_OBJECTIVE_KEY,
            label=label,
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE session_objectives
            SET label = :label
            WHERE objective_key = :objective_key
              AND session_id IN (
                SELECT id
                FROM sessions
                WHERE lab_version_id = :lab_version_id
              )
            """
        ).bindparams(
            lab_version_id=LAB_3_VERSION_ID,
            objective_key=LAB_3_OBJECTIVE_KEY,
            label=label,
        )
    )


def upgrade() -> None:
    """Upgrade schema."""
    _update_label(label=NEW_LABEL)


def downgrade() -> None:
    """Downgrade schema."""
    _update_label(label=OLD_LABEL)
