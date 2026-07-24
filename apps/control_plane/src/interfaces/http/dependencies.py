from functools import lru_cache
from sqlalchemy.orm import Session
from pydantic import ValidationError

# from fastapi import Depends, HTTPException, status
from fastapi import Depends, Request
from dataclasses import replace

from apps.control_plane.src.application.session_create.ports import (
    AdmissionPolicy,
    LabRepository,
    CreateSessionRepository,
    CreateSessionUnitOfWork,
)
from apps.control_plane.src.application.session_create.schemas import (
    CreateSessionResult,
)
from apps.control_plane.src.application.common.ports import IdempotencyStore
from apps.control_plane.src.application.runtime.types import RuntimeClientConfig
from apps.control_plane.src.application.auth.ports import TokenVerifierPort
from apps.control_plane.src.application.email_classification.ports import (
    EmailMaliciousnessClassifierPort,
)
from apps.control_plane.src.application.prompt_classification.ports import (
    AuthorityBulletinClassifierPort,
)
from apps.control_plane.src.application.prompt_classification.types import (
    AuthorityBulletinClassificationInput,
    AuthorityBulletinClassificationResult,
)
from apps.control_plane.src.application.session_stream.ports import (
    SessionStreamManagerPort,
)
from apps.control_plane.src.infrastructure.policy.admission_policy import (
    ConcreteAdmissionPolicy,
)
from apps.control_plane.src.infrastructure.config.settings import (
    get_admission_settings,
)
from apps.control_plane.src.infrastructure.auth.cognito_jwt_verifier import (
    CognitoJwtVerifier,
)
from apps.control_plane.src.infrastructure.auth.local_token_verifier import (
    LocalTokenVerifier,
)
from apps.control_plane.src.infrastructure.auth.types import AuthVerifierConfig
from apps.control_plane.src.infrastructure.persistence.lab_repository import (
    SQLAlchemyLabRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyCreateSessionRepository,
    SQLAlchemyEvaluatorRepository,
    SQLAlchemySessionMetadataRepository,
    SQLAlchemySessionRuntimeBindingRepository,
    SQLAlchemyTraceEventRepository,
)
from apps.control_plane.src.application.session_query.ports import (
    SessionLatestByLabRepository,
    SessionListByLabRepository,
    SessionMetadataRepository,
)
from apps.control_plane.src.infrastructure.persistence.db import (
    get_db_session,
    SessionFactory,
)
from apps.control_plane.src.infrastructure.persistence.idempotency_store import (
    SQLAlchemyCreateSessionIdempotencyStore,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work_create_session import (
    SQLAlchemyCreateSessionUnitOfWork,
)
from apps.control_plane.src.infrastructure.persistence.session_feedback_repository import (
    SQLAlchemySessionFeedbackRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_report_evidence_repository import (
    SQLAlchemySessionReportEvidenceRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_report_draft_repository import (
    SQLAlchemySessionReportDraftRepository,
)
from apps.control_plane.src.infrastructure.persistence.enrollment_repository import (
    SQLAlchemyEnrollmentRepository,
)
from apps.control_plane.src.application.enrollment.ports import EnrollmentRepositoryPort
from apps.control_plane.src.application.pilot_requests.ports import (
    PilotRequestRepositoryPort,
)
from apps.control_plane.src.application.pilot_provisioning.ports import (
    PilotProvisioningRepositoryPort,
)
from apps.control_plane.src.application.instructor_provisioning.ports import (
    InstructorIdentityProviderPort,
    InstructorProvisioningRepositoryPort,
)
from apps.control_plane.src.infrastructure.persistence.pilot_request_repository import (
    SQLAlchemyPilotRequestRepository,
)
from apps.control_plane.src.infrastructure.persistence.pilot_provisioning_repository import (
    SQLAlchemyPilotProvisioningRepository,
)
from apps.control_plane.src.infrastructure.persistence.instructor_provisioning_repository import (
    SQLAlchemyInstructorProvisioningRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_hints_repository import (
    SQLAlchemySessionHintSeenRepository,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from apps.control_plane.src.infrastructure.session_email.deps import (
    SessionEmailDeps,
    build_session_email_deps,
)
from apps.control_plane.src.infrastructure.session_explanation_submission.deps import (
    SessionExplanationDeps,
    build_session_explanation_deps,
)

# from apps.control_plane.src.application.runtime.ports import RuntimeClientPort
from apps.control_plane.src.infrastructure.runtime.client import RuntimeHttpClient
from apps.control_plane.src.infrastructure.classification.openrouter_email_classifier import (
    OpenRouterEmailClassifier,
)
from apps.control_plane.src.infrastructure.classification.openrouter_authority_bulletin_classifier import (
    OpenRouterAuthorityBulletinClassifier,
)
from apps.control_plane.src.interfaces.http.ws_manager_registry import ws_manager
from apps.control_plane.src.infrastructure.config.settings import (
    EmailClassifierSettings,
    InstructorProvisioningSettings,
    get_auth_verifier_config as load_auth_verifier_config,
    get_email_classifier_settings,
    get_instructor_provisioning_settings as load_instructor_provisioning_settings,
    get_runtime_client_config as load_runtime_client_config,
)
from apps.control_plane.src.infrastructure.auth.cognito_instructor_identity_provider import (
    CognitoInstructorIdentityProvider,
    CognitoInstructorIdentitySettings,
    NoopInstructorIdentityProvider,
)


def get_ws_session_manager() -> SessionStreamManagerPort:
    return ws_manager


def get_admission_policy(
    db: Session = Depends(get_db_session),
) -> AdmissionPolicy:
    settings = get_admission_settings()
    return ConcreteAdmissionPolicy(db=db, settings=settings)


def get_idempotency_store(
    db: Session = Depends(get_db_session),
) -> IdempotencyStore[CreateSessionResult]:
    return SQLAlchemyCreateSessionIdempotencyStore(db=db)


def get_request_db_session(db: Session = Depends(get_db_session)) -> Session:
    return db


def get_lab_repository(db: Session = Depends(get_db_session)) -> LabRepository:
    return SQLAlchemyLabRepository(db=db)


def get_session_repository(
    db: Session = Depends(get_db_session),
) -> CreateSessionRepository:
    return SQLAlchemyCreateSessionRepository(db=db)


def get_create_session_uow() -> CreateSessionUnitOfWork:
    return SQLAlchemyCreateSessionUnitOfWork(session_factory=SessionFactory)


def get_session_metadata_repository(
    db: Session = Depends(get_db_session),
) -> SessionMetadataRepository:
    return SQLAlchemySessionMetadataRepository(db=db)


def get_session_latest_by_lab_repository(
    db: Session = Depends(get_db_session),
) -> SessionLatestByLabRepository:
    return SQLAlchemySessionMetadataRepository(db=db)


def get_session_list_by_lab_repository(
    db: Session = Depends(get_db_session),
) -> SessionListByLabRepository:
    return SQLAlchemySessionMetadataRepository(db=db)


def get_evaluator_repository(
    db: Session = Depends(get_db_session),
) -> SQLAlchemyEvaluatorRepository:
    return SQLAlchemyEvaluatorRepository(db=db)


def get_trace_event_repository(
    db: Session = Depends(get_db_session),
) -> SQLAlchemyTraceEventRepository:
    return SQLAlchemyTraceEventRepository(db=db)


def get_runtime_binding_repository(
    db: Session = Depends(get_db_session),
) -> SQLAlchemySessionRuntimeBindingRepository:
    return SQLAlchemySessionRuntimeBindingRepository(db=db)


def get_session_feedback_repository(
    db: Session = Depends(get_db_session),
) -> SQLAlchemySessionFeedbackRepository:
    return SQLAlchemySessionFeedbackRepository(db=db)


def get_session_report_evidence_repository(
    db: Session = Depends(get_db_session),
) -> SQLAlchemySessionReportEvidenceRepository:
    return SQLAlchemySessionReportEvidenceRepository(db=db)


def get_session_report_draft_repository(
    db: Session = Depends(get_db_session),
) -> SQLAlchemySessionReportDraftRepository:
    return SQLAlchemySessionReportDraftRepository(db=db)


def get_session_hint_seen_repository(
    db: Session = Depends(get_db_session),
) -> SQLAlchemySessionHintSeenRepository:
    return SQLAlchemySessionHintSeenRepository(db=db)


def get_enrollment_repository(
    db: Session = Depends(get_db_session),
) -> EnrollmentRepositoryPort:
    return SQLAlchemyEnrollmentRepository(db=db)


def get_pilot_request_repository(
    db: Session = Depends(get_db_session),
) -> PilotRequestRepositoryPort:
    return SQLAlchemyPilotRequestRepository(db=db)


def get_pilot_provisioning_repository(
    db: Session = Depends(get_db_session),
) -> PilotProvisioningRepositoryPort:
    return SQLAlchemyPilotProvisioningRepository(db=db)


def get_instructor_provisioning_repository(
    db: Session = Depends(get_db_session),
) -> InstructorProvisioningRepositoryPort:
    return SQLAlchemyInstructorProvisioningRepository(db=db)


def get_session_lifecycle_uow() -> SQLAlchemyUnitOfWork:
    return SQLAlchemyUnitOfWork(session_factory=SessionFactory)


def get_session_email_deps(
    db: Session = Depends(get_db_session),
) -> SessionEmailDeps:
    return build_session_email_deps(db=db)


def get_session_explanation_deps(
    db: Session = Depends(get_db_session),
) -> SessionExplanationDeps:
    return build_session_explanation_deps(db=db)


def get_runtime_client_config() -> RuntimeClientConfig:
    return load_runtime_client_config()


@lru_cache(maxsize=1)
def get_email_classifier_config() -> EmailClassifierSettings:
    return get_email_classifier_settings()


@lru_cache(maxsize=1)
def get_auth_verifier_config() -> AuthVerifierConfig:
    return load_auth_verifier_config()


@lru_cache(maxsize=1)
def get_instructor_provisioning_settings() -> InstructorProvisioningSettings:
    return load_instructor_provisioning_settings()


@lru_cache(maxsize=1)
def get_instructor_identity_provider() -> InstructorIdentityProviderPort:
    settings = get_instructor_provisioning_settings()
    if (
        not settings.enabled
        or not settings.cognito_user_pool_id
        or not settings.cognito_region
    ):
        return NoopInstructorIdentityProvider()
    return CognitoInstructorIdentityProvider(
        CognitoInstructorIdentitySettings(
            enabled=settings.enabled,
            user_pool_id=settings.cognito_user_pool_id,
            region=settings.cognito_region,
            instructor_group_name=settings.cognito_instructor_group_name,
        )
    )


@lru_cache(maxsize=1)
def get_token_verifier() -> TokenVerifierPort:
    config = get_auth_verifier_config()
    if config.issuer:
        return CognitoJwtVerifier(config=config)
    return LocalTokenVerifier(config=config)


def get_token_verifier_from_request(request: Request) -> TokenVerifierPort:
    verifier = getattr(request.app.state, "token_verifier", None)
    if verifier is not None:
        return verifier
    return get_token_verifier()


class RuntimeClientFactory:
    def __init__(self, config: RuntimeClientConfig) -> None:
        self._config = config

    def create(self, *, base_url: str) -> RuntimeHttpClient:
        cfg = replace(self._config, base_url=base_url)
        return RuntimeHttpClient(config=cfg)


def get_runtime_client_factory() -> RuntimeClientFactory:
    config = get_runtime_client_config()
    base_cfg = RuntimeClientConfig(
        base_url=config.base_url,
        timeout_seconds=config.timeout_seconds,
        auth_token=config.auth_token,
    )

    return RuntimeClientFactory(config=base_cfg)


def get_email_maliciousness_classifier() -> EmailMaliciousnessClassifierPort:
    config = get_email_classifier_config()
    return OpenRouterEmailClassifier(
        base_url=config.provider_endpoint,
        api_key=config.openrouter_api_key,
        model=config.model_name,
        timeout_seconds=config.model_timeout,
    )


class _NoopAuthorityBulletinClassifier(AuthorityBulletinClassifierPort):
    async def classify_prompt(
        self, *, input: AuthorityBulletinClassificationInput
    ) -> AuthorityBulletinClassificationResult:
        return AuthorityBulletinClassificationResult(
            is_authority_bulletin=False,
            signer_name=None,
            confidence=0.0,
            reason="classifier_not_configured",
            provider="noop",
            model="noop",
        )


def get_authority_bulletin_classifier() -> AuthorityBulletinClassifierPort:
    try:
        config = get_email_classifier_config()
    except (RuntimeError, ValidationError):
        return _NoopAuthorityBulletinClassifier()

    return OpenRouterAuthorityBulletinClassifier(
        base_url=config.provider_endpoint,
        api_key=config.openrouter_api_key,
        model=config.model_name,
        timeout_seconds=config.model_timeout,
    )
