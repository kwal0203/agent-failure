"""update agent lab2 hint offsets to match lab1

Revision ID: 9c4e1d2f7a88
Revises: f2a7c9d4b1e0
Create Date: 2026-04-28 15:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c4e1d2f7a88"
down_revision: Union[str, Sequence[str], None] = "f2a7c9d4b1e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE lab_hint_templates lht
            SET
                offset_seconds = CASE lht.hint_key
                    WHEN 'hint_1' THEN 90
                    WHEN 'hint_2' THEN 210
                    WHEN 'hint_3' THEN 360
                    WHEN 'hint_4' THEN 540
                    ELSE lht.offset_seconds
                END,
                updated_at = now()
            FROM lab_versions lv
            JOIN labs l ON l.id = lv.lab_id
            WHERE lht.lab_version_id = lv.id
              AND l.slug = 'agent-tool-misuse'
              AND lv.is_active = true
              AND lht.hint_key IN ('hint_1', 'hint_2', 'hint_3', 'hint_4')
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE lab_hint_templates lht
            SET
                offset_seconds = CASE lht.hint_key
                    WHEN 'hint_1' THEN 10
                    WHEN 'hint_2' THEN 20
                    WHEN 'hint_3' THEN 30
                    WHEN 'hint_4' THEN 40
                    ELSE lht.offset_seconds
                END,
                updated_at = now()
            FROM lab_versions lv
            JOIN labs l ON l.id = lv.lab_id
            WHERE lht.lab_version_id = lv.id
              AND l.slug = 'agent-tool-misuse'
              AND lv.is_active = true
              AND lht.hint_key IN ('hint_1', 'hint_2', 'hint_3', 'hint_4')
            """
        )
    )
