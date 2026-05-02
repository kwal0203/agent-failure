import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from apps.control_plane.src.application.common.schemas import LabDifficultyParser
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.learner_explanation.service import (
    inject_learner_explanation,
)
from apps.control_plane.src.application.learner_explanation.types import (
    LearnerExplanationInput,
)
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from apps.control_plane.src.infrastructure.persistence.learner_explanation_repository import (
    LearnerExplanationRepository,
)
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
    SQLAlchemyTraceEventRepository,
)

logger = logging.getLogger(__name__)


class SessionExplanationPolicyError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        retryable: bool,
        status_code: int,
        details: dict[str, object] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status_code = status_code
        self.details = details


@dataclass(frozen=True)
class SubmitLearnerExplanationCommand:
    session_id: UUID
    principal: PrincipalContext
    explanation: str
    idempotency_key: str


@dataclass(frozen=True)
class SubmitLearnerExplanationResult:
    explanation_id: UUID


def submit_learner_explanation(
    *, command: SubmitLearnerExplanationCommand, db: Session
) -> SubmitLearnerExplanationResult | None:
    session_metadata_repo = SQLAlchemySessionMetadataRepository(db=db)
    session_metadata = get_session_metadata(
        session_id=command.session_id,
        principal=command.principal,
        repo=session_metadata_repo,
    )
    if session_metadata is None:
        return None

    if session_metadata.state != "COMPLETED":
        raise SessionExplanationPolicyError(
            code="SESSION_NOT_READY",
            message="Explanations can only be submitted after lab completion.",
            retryable=False,
            status_code=409,
            details={
                "session_id": str(command.session_id),
                "state": session_metadata.state,
                "required_state": "COMPLETED",
            },
        )

    lab_id = session_metadata.lab_id
    lab_version_id = session_metadata.lab_version_id
    if lab_id is None or lab_version_id is None:
        raise SessionExplanationPolicyError(
            code="SESSION_METADATA_INCOMPLETE",
            message="Session is missing lab metadata required for explanation submission.",
            retryable=False,
            status_code=500,
            details={"session_id": str(command.session_id)},
        )

    parsed = LabDifficultyParser.model_validate(
        {"lab_difficulty": session_metadata.lab_difficulty}
    )

    explanation_artifact = LearnerExplanationInput(
        explanation=command.explanation,
        session_id=session_metadata.id,
        lab_id=lab_id,
        lab_version_id=lab_version_id,
        lab_difficulty=parsed.lab_difficulty,
        actor_user_id=command.principal.user_id,
        idempotency_key=command.idempotency_key,
        source="learner",
    )

    learner_explanation_repo = LearnerExplanationRepository(db=db)
    trace_repo = SQLAlchemyTraceEventRepository(db=db)
    outbox = SQLAlchemyOutbox(db=db)
    result = inject_learner_explanation(
        repo=learner_explanation_repo,
        learner_input=explanation_artifact,
        trace_repo=trace_repo,
        outbox=outbox,
    )

    logger.info(
        "learner explanation accepted",
        extra={
            "event": "learner_explanation_submitted",
            "session_id": str(command.session_id),
            "lab_id": str(lab_id),
            "lab_difficulty": parsed.lab_difficulty,
            "user_id": str(command.principal.user_id),
        },
    )

    return SubmitLearnerExplanationResult(explanation_id=result.explanation_id)
