"""Rename token_exposed objective label for lab 1

Revision ID: c4f9a6a1d2b1
Revises: b1c6f0d7e2a9
Create Date: 2026-04-24 18:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4f9a6a1d2b1"
down_revision: Union[str, Sequence[str], None] = "b1c6f0d7e2a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_LABEL = "Token Exposed"
_NEW_LABEL = "Private information revealed"
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
