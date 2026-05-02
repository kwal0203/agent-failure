import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.orchestrator.types import SessionRuntimeBinding
from apps.control_plane.src.application.prompt_classification.ports import (
    AuthorityBulletinClassifierPort,
)
from apps.control_plane.src.application.prompt_classification.types import (
    AuthorityBulletinClassificationInput,
)
from apps.control_plane.src.application.session_stream.messages import (
    ServerMessageEnvelope,
)
from apps.control_plane.src.application.session_query.types import SessionMetadataDTO
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
    SQLAlchemySessionRuntimeBindingRepository,
)
from apps.control_plane.src.application.session_stream.messages import (
    build_policy_denial_message,
)

from .constants import LAB2_AUTHORITY_SIGNER, LAB2_IDS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthorityBulletinDecision:
    passed: bool
    runbook_action_type: str | None
    destructive_db_delete: bool | None


async def classify_authority_bulletin(
    *,
    lab_id: UUID | None,
    prompt_content: str,
    bulletin_classifier: AuthorityBulletinClassifierPort,
) -> AuthorityBulletinDecision:
    if lab_id not in LAB2_IDS:
        return AuthorityBulletinDecision(
            passed=False, runbook_action_type=None, destructive_db_delete=None
        )

    try:
        classify = await bulletin_classifier.classify_prompt(
            input=AuthorityBulletinClassificationInput(
                prompt_content=prompt_content,
                expected_signer=LAB2_AUTHORITY_SIGNER,
            )
        )
        passed = (
            classify.is_authority_bulletin
            and isinstance(classify.signer_name, str)
            and classify.signer_name.strip().lower() == LAB2_AUTHORITY_SIGNER.lower()
        )
        return AuthorityBulletinDecision(
            passed=passed,
            runbook_action_type=classify.runbook_action_type,
            destructive_db_delete=classify.destructive_db_delete,
        )
    except RuntimeError:
        return AuthorityBulletinDecision(
            passed=False, runbook_action_type=None, destructive_db_delete=None
        )


def get_session_metadata_or_none(
    *, db: Session, session_id: UUID, principal: PrincipalContext
) -> SessionMetadataDTO | None:
    repo = SQLAlchemySessionMetadataRepository(db=db)
    return get_session_metadata(session_id=session_id, principal=principal, repo=repo)


def get_runtime_binding_or_none(
    *, db: Session, session_id: UUID
) -> SessionRuntimeBinding | None:
    runtime_binding_repo = SQLAlchemySessionRuntimeBindingRepository(db=db)
    return runtime_binding_repo.get_by_session_id(session_id=session_id)


def runtime_not_ready_message(
    *,
    session_id: UUID,
    runtime_binding: SessionRuntimeBinding | None,
    lab_difficulty: str | None,
) -> ServerMessageEnvelope:
    current_status = (
        runtime_binding.status if runtime_binding is not None else "missing"
    )
    logger.warning(
        "runtime binding not ready",
        extra={
            "event": "runtime_binding_not_ready",
            "session_id": str(session_id),
            "status": current_status,
            "base_url": runtime_binding.base_url
            if runtime_binding is not None
            else None,
            "lab_difficulty": lab_difficulty,
        },
    )
    return build_policy_denial_message(
        session_id=session_id,
        reason_code="RUNTIME_BINDING_NOT_READY",
        message=f"Runtime is not ready: (status={current_status})",
    )
