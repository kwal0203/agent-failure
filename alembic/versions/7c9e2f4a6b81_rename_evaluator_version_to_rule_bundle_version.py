"""Rename evaluator version provenance to rule bundle version.

Revision ID: 7c9e2f4a6b81
Revises: 4b7c2d9e1a63
Create Date: 2026-07-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "7c9e2f4a6b81"
down_revision: str | Sequence[str] | None = "4b7c2d9e1a63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "evaluation_results",
        "evaluator_version",
        new_column_name="rule_bundle_version",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )

    op.execute(
        sa.text(
            """
            UPDATE outbox_events
            SET payload = payload - 'evaluator_version' - 'rule_bundle_version'
            WHERE event_type = 'session.evaluate.requested.v1'
              AND (
                  payload ? 'evaluator_version'
                  OR payload ? 'rule_bundle_version'
              )
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE outbox_events
            SET payload = jsonb_set(
                payload - 'evaluator_version',
                '{rule_bundle_version}',
                payload -> 'evaluator_version',
                true
            )
            WHERE event_type = 'session.objective.completed.v1'
              AND payload ? 'evaluator_version'
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE outbox_events
            SET payload = payload || '{"evaluator_version": 1}'::jsonb
            WHERE event_type = 'session.evaluate.requested.v1'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE outbox_events
            SET payload = jsonb_set(
                payload - 'rule_bundle_version',
                '{evaluator_version}',
                payload -> 'rule_bundle_version',
                true
            )
            WHERE event_type = 'session.objective.completed.v1'
              AND payload ? 'rule_bundle_version'
            """
        )
    )

    op.alter_column(
        "evaluation_results",
        "rule_bundle_version",
        new_column_name="evaluator_version",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
