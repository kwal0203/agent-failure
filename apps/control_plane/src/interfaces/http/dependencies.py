from functools import lru_cache
from sqlalchemy.orm import Session

# from fastapi import Depends, HTTPException, status
from fastapi import Depends, Request
from dataclasses import dataclass, replace

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
from apps.control_plane.src.infrastructure.policy.admission import StubAdmissionPolicy
from apps.control_plane.src.infrastructure.auth.local_token_verifier import (
    LocalTokenVerifier,
)
from apps.control_plane.src.infrastructure.auth.cognito_jwt_verifier import (
    CognitoJwtVerifier,
)
from apps.control_plane.src.infrastructure.auth.types import AuthVerifierConfig
from apps.control_plane.src.infrastructure.persistence.lab_repository import (
    SQLAlchemyLabRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyCreateSessionRepository,
    SQLAlchemySessionMetadataRepository,
)
from apps.control_plane.src.application.session_query.ports import (
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

# from apps.control_plane.src.application.runtime.ports import RuntimeClientPort
from apps.control_plane.src.infrastructure.runtime.client import RuntimeHttpClient
from apps.control_plane.src.infrastructure.classification.openrouter_email_classifier import (
    OpenRouterEmailClassifier,
)
from apps.control_plane.src.infrastructure.classification.openrouter_authority_bulletin_classifier import (
    OpenRouterAuthorityBulletinClassifier,
)


import os


class AdmissionPolicyStub:
    pass


@dataclass(frozen=True)
class EmailClassifierConfig:
    openrouter_api_key: str
    provider_endpoint: str
    model_name: str
    model_timeout: float


def get_admission_policy() -> AdmissionPolicy:
    return StubAdmissionPolicy()


def get_idempotency_store(
    db: Session = Depends(get_db_session),
) -> IdempotencyStore[CreateSessionResult]:
    return SQLAlchemyCreateSessionIdempotencyStore(db=db)


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


def get_runtime_client_config() -> RuntimeClientConfig:
    timeout_raw = os.getenv("RUNTIME_TIMEOUT_SECONDS", "").strip()
    auth_token = os.getenv("RUNTIME_AUTH_TOKEN", "").strip()

    try:
        timeout_seconds = float(timeout_raw)
    except ValueError:
        timeout_seconds = 10.0

    return RuntimeClientConfig(
        base_url="http://placeholder",
        timeout_seconds=timeout_seconds,
        auth_token=auth_token or None,
    )


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default

    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"Invalid float for {name}: {raw!r}") from exc

    if value <= 0:
        raise RuntimeError(f"{name} must be > 0")

    return value


@lru_cache(maxsize=1)
def get_email_classifier_config() -> EmailClassifierConfig:
    return EmailClassifierConfig(
        openrouter_api_key=_require_env("OPENROUTER_API_KEY"),
        provider_endpoint=_require_env("PROVIDER_ENDPOINT"),
        model_name=_require_env("MODEL_NAME"),
        model_timeout=_get_float_env("MODEL_TIMEOUT", 30.0),
    )


@lru_cache(maxsize=1)
def get_auth_verifier_config() -> AuthVerifierConfig:
    issuer = os.getenv("AUTH_ISSUER", "").strip()
    audience = os.getenv("AUTH_AUDIENCE", "").strip()
    jwks_uri = os.getenv("AUTH_JWKS_URI", "").strip()
    cache_ttl_raw = os.getenv("AUTH_JWKS_CACHE_TTL_SECONDS", "").strip()
    try:
        cache_ttl_seconds = int(cache_ttl_raw) if cache_ttl_raw else 300
    except ValueError:
        cache_ttl_seconds = 300

    return AuthVerifierConfig(
        issuer=issuer,
        audience=audience,
        jwks_uri=jwks_uri,
        jwks_cache_ttl_seconds=cache_ttl_seconds,
    )


@lru_cache(maxsize=1)
def get_token_verifier() -> TokenVerifierPort:
    config = get_auth_verifier_config()
    if config.issuer and config.audience and config.jwks_uri:
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
    except RuntimeError:
        return _NoopAuthorityBulletinClassifier()

    return OpenRouterAuthorityBulletinClassifier(
        base_url=config.provider_endpoint,
        api_key=config.openrouter_api_key,
        model=config.model_name,
        timeout_seconds=config.model_timeout,
    )


# def get_runtime_client(
#     config: RuntimeClientConfig = Depends(get_runtime_client_config),
# ) -> RuntimeClientPort:
#     return RuntimeHttpClient(config=config)
