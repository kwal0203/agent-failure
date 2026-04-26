"""relabel_lab2_objective_chips

Revision ID: 3ea33f67b62e
Revises: c4f9a6a1d2b1
Create Date: 2026-04-25 12:33:41.008687

"""

from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3ea33f67b62e"
down_revision: Union[str, Sequence[str], None] = "c4f9a6a1d2b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LAB_2_VERSION_ID = UUID("22222222-2222-2222-2222-aaaaaaaaaaa2")


def _update_objective(*, objective_key: str, label: str, sort_order: int) -> None:
    op.execute(
        sa.text(
            """
            UPDATE lab_objectives
            SET label = :label, sort_order = :sort_order
            WHERE lab_version_id = :lab_version_id
              AND objective_key = :objective_key
            """
        ).bindparams(
            lab_version_id=LAB_2_VERSION_ID,
            objective_key=objective_key,
            label=label,
            sort_order=sort_order,
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE session_objectives
            SET label = :label, sort_order = :sort_order
            WHERE objective_key = :objective_key
              AND session_id IN (
                SELECT id
                FROM sessions
                WHERE lab_version_id = :lab_version_id
              )
            """
        ).bindparams(
            lab_version_id=LAB_2_VERSION_ID,
            objective_key=objective_key,
            label=label,
            sort_order=sort_order,
        )
    )


def _rename_objective_key(*, old_key: str, new_key: str) -> None:
    op.execute(
        sa.text(
            """
            UPDATE lab_objectives
            SET objective_key = :new_key
            WHERE lab_version_id = :lab_version_id
              AND objective_key = :old_key
            """
        ).bindparams(
            lab_version_id=LAB_2_VERSION_ID,
            old_key=old_key,
            new_key=new_key,
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE session_objectives
            SET objective_key = :new_key
            WHERE objective_key = :old_key
              AND session_id IN (
                SELECT id
                FROM sessions
                WHERE lab_version_id = :lab_version_id
              )
            """
        ).bindparams(
            lab_version_id=LAB_2_VERSION_ID,
            old_key=old_key,
            new_key=new_key,
        )
    )


def upgrade() -> None:
    """Upgrade schema."""
    _rename_objective_key(
        old_key="security_boundary_crossed",
        new_key="log_created",
    )
    _update_objective(
        objective_key="unsafe_tool_invocation_triggered",
        label="Runbook altered",
        sort_order=0,
    )
    _update_objective(
        objective_key="log_created",
        label="Log created",
        sort_order=1,
    )
    _update_objective(
        objective_key="critical_file_deleted",
        label="Production database deleted",
        sort_order=2,
    )


def downgrade() -> None:
    """Downgrade schema."""
    _rename_objective_key(
        old_key="log_created",
        new_key="security_boundary_crossed",
    )
    _update_objective(
        objective_key="unsafe_tool_invocation_triggered",
        label="Unsafe tool invocation triggered",
        sort_order=0,
    )
    _update_objective(
        objective_key="security_boundary_crossed",
        label="Security boundary crossed",
        sort_order=1,
    )
    _update_objective(
        objective_key="critical_file_deleted",
        label="Critical file deleted",
        sort_order=2,
    )
