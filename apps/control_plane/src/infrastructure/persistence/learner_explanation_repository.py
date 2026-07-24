from apps.control_plane.src.application.learner_explanation.ports import (
    LearnerExplanationPort,
)
from apps.control_plane.src.application.learner_explanation.types import (
    LearnerExplanationInput,
    LearnerExplanationOutput,
)
from apps.control_plane.src.application.common.errors import (
    DuplicateIdempotencyKeyError,
)

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from uuid import UUID

from .models import LearnerExplanationModel


class LearnerExplanationRepository(LearnerExplanationPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_session_and_idempotency_key(
        self, *, session_id: UUID, idempotency_key: str
    ) -> LearnerExplanationOutput | None:
        row = self._db.execute(
            select(LearnerExplanationModel).where(
                LearnerExplanationModel.session_id == session_id,
                LearnerExplanationModel.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none()
        if row is None:
            return None

        return LearnerExplanationOutput(
            session_id=row.session_id,
            explanation_id=row.explanation_id,
            accepted=True,
        )

    def inject_learner_explanation(
        self, input: LearnerExplanationInput
    ) -> LearnerExplanationOutput:
        existing = self.get_by_session_and_idempotency_key(
            session_id=input.session_id,
            idempotency_key=input.idempotency_key,
        )
        if existing is not None:
            return existing

        explanation = LearnerExplanationModel(
            explanation=input.explanation,
            session_id=input.session_id,
            lab_id=input.lab_id,
            lab_version_id=input.lab_version_id,
            source=input.source,
            actor_user_id=input.actor_user_id,
            idempotency_key=input.idempotency_key,
        )

        self._db.add(explanation)

        try:
            self._db.flush()
        except IntegrityError as exc:
            constraint_name = getattr(
                getattr(exc.orig, "diag", None), "constraint_name", None
            )
            if constraint_name == "uq_learner_explanations_idempo":
                raise DuplicateIdempotencyKeyError(
                    code="DUPLICATE_IDEMPOTENCY_KEY",
                    details={
                        "session_id": str(input.session_id),
                        "constraint": constraint_name,
                    },
                ) from exc
            raise

        return LearnerExplanationOutput(
            session_id=input.session_id,
            explanation_id=explanation.explanation_id,
            accepted=True,
        )

    def get_latest_for_session(
        self, session_id: UUID
    ) -> LearnerExplanationOutput | None:
        stmt = (
            select(LearnerExplanationModel)
            .where(LearnerExplanationModel.session_id == session_id)
            .order_by(
                LearnerExplanationModel.created_at.desc(),
                LearnerExplanationModel.explanation_id.desc(),
            )
            .limit(1)
        )
        latest = self._db.execute(stmt).scalar_one_or_none()
        if not latest:
            return None

        return LearnerExplanationOutput(
            session_id=session_id, explanation_id=latest.explanation_id
        )
