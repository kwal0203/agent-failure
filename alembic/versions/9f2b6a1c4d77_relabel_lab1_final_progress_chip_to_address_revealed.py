"""Relabel lab1 final progress chip to Address revealed

Revision ID: 9f2b6a1c4d77
Revises: c1a7f0d9e4b2
Create Date: 2026-05-03 10:58:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f2b6a1c4d77"
down_revision: Union[str, Sequence[str], None] = "c1a7f0d9e4b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_LABEL = "Private information revealed"
_NEW_LABEL = "Address revealed"
_OBJECTIVE_KEY = "token_exposed"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            """
            UPDATE lab_objectives
            SET label = :new_label
            WHERE objective_key = :objective_key
            """
        ).bindparams(new_label=_NEW_LABEL, objective_key=_OBJECTIVE_KEY)
    )
    op.execute(
        sa.text(
            """
            UPDATE session_objectives
            SET label = :new_label
            WHERE objective_key = :objective_key
            """
        ).bindparams(new_label=_NEW_LABEL, objective_key=_OBJECTIVE_KEY)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            """
            UPDATE lab_objectives
            SET label = :old_label
            WHERE objective_key = :objective_key
            """
        ).bindparams(old_label=_OLD_LABEL, objective_key=_OBJECTIVE_KEY)
    )
    op.execute(
        sa.text(
            """
            UPDATE session_objectives
            SET label = :old_label
            WHERE objective_key = :objective_key
            """
        ).bindparams(old_label=_OLD_LABEL, objective_key=_OBJECTIVE_KEY)
    )
