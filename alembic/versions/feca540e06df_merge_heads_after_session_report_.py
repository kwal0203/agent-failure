"""merge heads after session_report_evidence

Revision ID: feca540e06df
Revises: 7c9d2e4f5a60, 7f3c2a1d9b50
Create Date: 2026-05-17 13:29:47.046444

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "feca540e06df"
down_revision: Union[str, Sequence[str], None] = ("7c9d2e4f5a60", "7f3c2a1d9b50")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
