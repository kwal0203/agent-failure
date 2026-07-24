"""Remove the unfinished lab difficulty dimension.

Revision ID: 4b7c2d9e1a63
Revises: f6b8d0e2a415
Create Date: 2026-07-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "4b7c2d9e1a63"
down_revision: str | Sequence[str] | None = "f6b8d0e2a415"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _normalize_prompt_injection_identifiers() -> None:
    op.execute(
        sa.text(
            """
            UPDATE evaluation_results
            SET code = replace(
                    replace(code, 'pi.global.', 'pi.'),
                    'pi.medium.',
                    'pi.'
                ),
                reason_code = replace(
                    replace(reason_code, 'PI_GLOBAL_', 'PI_'),
                    'PI_MEDIUM_',
                    'PI_'
                ),
                idempotency_key = replace(
                    replace(idempotency_key, 'pi.global.', 'pi.'),
                    'pi.medium.',
                    'pi.'
                )
            WHERE code LIKE 'pi.global.%' OR code LIKE 'pi.medium.%'
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE session_feedback
            SET reason_code = replace(
                    replace(reason_code, 'PI_GLOBAL_', 'PI_'),
                    'PI_MEDIUM_',
                    'PI_'
                ),
                idempotency_key = replace(
                    replace(idempotency_key, 'pi_global_', 'pi_'),
                    'pi_medium_',
                    'pi_'
                )
            WHERE reason_code LIKE 'PI_GLOBAL_%'
               OR reason_code LIKE 'PI_MEDIUM_%'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE sessions
            SET completion_reason_code = replace(
                replace(completion_reason_code, 'PI_GLOBAL_', 'PI_'),
                'PI_MEDIUM_',
                'PI_'
            )
            WHERE completion_reason_code LIKE 'PI_GLOBAL_%'
               OR completion_reason_code LIKE 'PI_MEDIUM_%'
            """
        )
    )


def upgrade() -> None:
    _normalize_prompt_injection_identifiers()
    op.execute(
        sa.text(
            """
            UPDATE outbox_events
            SET payload = payload - 'lab_difficulty'
            WHERE payload ? 'lab_difficulty'
              AND event_type IN (
                  'session.provisioning.v1',
                  'session.evaluate.requested.v1'
              )
            """
        )
    )

    op.drop_constraint("ck_sessions_lab_difficulty", "sessions", type_="check")
    op.drop_column("sessions", "lab_difficulty")

    op.drop_column("trace_events", "lab_difficulty")

    op.drop_constraint(
        "ck_evaluation_results_lab_difficulty",
        "evaluation_results",
        type_="check",
    )
    op.drop_column("evaluation_results", "lab_difficulty")

    op.drop_constraint(
        "ck_learner_explanations_lab_difficulty",
        "learner_explanations",
        type_="check",
    )
    op.drop_column("learner_explanations", "lab_difficulty")


def downgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "lab_difficulty",
            sa.String(length=32),
            nullable=False,
            server_default="medium",
        ),
    )
    op.create_check_constraint(
        "ck_sessions_lab_difficulty",
        "sessions",
        "lab_difficulty IN ('easy', 'medium')",
    )

    op.add_column(
        "trace_events",
        sa.Column("lab_difficulty", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "evaluation_results",
        sa.Column(
            "lab_difficulty",
            sa.String(length=32),
            nullable=False,
            server_default="medium",
        ),
    )
    op.create_check_constraint(
        "ck_evaluation_results_lab_difficulty",
        "evaluation_results",
        "lab_difficulty IN ('easy', 'medium')",
    )

    op.add_column(
        "learner_explanations",
        sa.Column(
            "lab_difficulty",
            sa.String(length=32),
            nullable=False,
            server_default="medium",
        ),
    )
    op.create_check_constraint(
        "ck_learner_explanations_lab_difficulty",
        "learner_explanations",
        "lab_difficulty IN ('easy', 'medium')",
    )

    op.execute(
        sa.text(
            """
            UPDATE outbox_events
            SET payload = payload || '{"lab_difficulty": "medium"}'::jsonb
            WHERE event_type IN (
                'session.provisioning.v1',
                'session.evaluate.requested.v1'
            )
            """
        )
    )
