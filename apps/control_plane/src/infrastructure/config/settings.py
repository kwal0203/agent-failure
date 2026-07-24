from dataclasses import dataclass
from typing import Annotated, Literal, Self
from urllib.parse import urlparse

from pydantic import (
    BeforeValidator,
    Field,
    SecretStr,
    StringConstraints,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from apps.control_plane.src.application.runtime.types import RuntimeClientConfig
from apps.control_plane.src.infrastructure.auth.types import AuthVerifierConfig


@dataclass(frozen=True)
class EmailClassifierSettings:
    openrouter_api_key: str
    provider_endpoint: str
    model_name: str
    model_timeout: float


@dataclass(frozen=True)
class RuntimePodEnvSettings:
    model_client_mode: str
    provider_endpoint: str
    model_name: str


@dataclass(frozen=True)
class AdmissionSettings:
    max_sessions_per_user: int
    max_sessions_global: int


@dataclass(frozen=True)
class EnrollmentSettings:
    token_secret: str
    token_ttl_seconds: int


@dataclass(frozen=True)
class InstructorProvisioningSettings:
    enabled: bool
    cognito_user_pool_id: str
    cognito_region: str
    cognito_instructor_group_name: str


@dataclass(frozen=True)
class OrchestratorSettings:
    provisioning_worker_poll_interval_seconds: float
    readiness_timeout_seconds: float
    readiness_poll_interval_seconds: float
    provisioning_retry_backoff_seconds: int
    cleanup_max_attempts: int
    cleanup_retry_backoff_seconds: int
    cleanup_reverify_backoff_seconds: int
    provisioning_timeout_seconds: int
    max_session_lifetime_seconds: int


@dataclass(frozen=True)
class HttpSettings:
    cors_allowed_origins: tuple[str, ...]


LOCAL_APP_ENV = "dev"
LOCAL_ENROLLMENT_TOKEN_SECRET = "local-dev-enrollment-secret-32-bytes-min"
LOCAL_CORS_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

AppEnvironment = Literal["dev", "staging", "production"]
NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
PositiveInt = Annotated[int, Field(ge=1)]
PositiveFiniteFloat = Annotated[float, Field(gt=0, allow_inf_nan=False)]


def _normalize_app_env(value: object) -> object:
    if not isinstance(value, str):
        return value
    normalized = value.strip().lower()
    aliases: dict[str, AppEnvironment] = {
        "dev": "dev",
        "development": "dev",
        "local": "dev",
        "stage": "staging",
        "staging": "staging",
        "prod": "production",
        "production": "production",
    }
    return aliases.get(normalized, normalized)


def _normalize_model_client_mode(value: object) -> object:
    if isinstance(value, str):
        return value.strip().lower()
    return value


class _EnvironmentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_ignore_empty=True,
        extra="ignore",
        frozen=True,
        hide_input_in_errors=True,
    )


class _AppEnvironmentSettings(_EnvironmentSettings):
    app_env: Annotated[AppEnvironment, BeforeValidator(_normalize_app_env)] = Field(
        default="staging",
        validation_alias="APP_ENV",
    )


class _AdmissionEnvironmentSettings(_EnvironmentSettings):
    max_sessions_per_user: PositiveInt = Field(
        default=3,
        validation_alias="ADMISSION_MAX_SESSIONS_PER_USER",
    )
    max_sessions_global: PositiveInt = Field(
        default=20,
        validation_alias="ADMISSION_MAX_SESSIONS_GLOBAL",
    )


class _EnrollmentEnvironmentSettings(_AppEnvironmentSettings):
    token_secret: SecretStr | None = Field(
        default=None,
        validation_alias="ENROLLMENT_TOKEN_SECRET",
    )
    token_ttl_seconds: PositiveInt = Field(
        default=600,
        validation_alias="ENROLLMENT_TOKEN_TTL_SECONDS",
    )

    @model_validator(mode="after")
    def validate_token_secret(self) -> Self:
        if self.token_secret is None and self.app_env != LOCAL_APP_ENV:
            raise ValueError(
                "ENROLLMENT_TOKEN_SECRET is required outside local development"
            )
        secret = (
            self.token_secret.get_secret_value()
            if self.token_secret is not None
            else LOCAL_ENROLLMENT_TOKEN_SECRET
        )
        if len(secret.encode()) < 32:
            raise ValueError("ENROLLMENT_TOKEN_SECRET must be at least 32 bytes")
        return self


class _DatabaseEnvironmentSettings(_EnvironmentSettings):
    database_url: NonEmptyStr = Field(validation_alias="DATABASE_URL")
    kubernetes_service_host: NonEmptyStr | None = Field(
        default=None,
        validation_alias="KUBERNETES_SERVICE_HOST",
    )

    @model_validator(mode="after")
    def reject_localhost_in_kubernetes(self) -> Self:
        host = (urlparse(self.database_url).hostname or "").lower()
        if self.kubernetes_service_host and host in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError(
                "Invalid DATABASE_URL for Kubernetes runtime: host resolves to "
                "localhost. Use a reachable service hostname or external DB endpoint."
            )
        return self


class _RuntimeClientEnvironmentSettings(_EnvironmentSettings):
    timeout_seconds: PositiveFiniteFloat = Field(
        default=10.0,
        validation_alias="RUNTIME_TIMEOUT_SECONDS",
    )
    auth_token: SecretStr | None = Field(
        default=None,
        validation_alias="RUNTIME_SHARED_TOKEN",
    )


class _EmailClassifierEnvironmentSettings(_EnvironmentSettings):
    openrouter_api_key: SecretStr = Field(validation_alias="OPENROUTER_API_KEY")
    provider_endpoint: NonEmptyStr = Field(validation_alias="PROVIDER_ENDPOINT")
    model_name: NonEmptyStr = Field(validation_alias="MODEL_NAME")
    model_timeout: PositiveFiniteFloat = Field(
        default=30.0,
        validation_alias="MODEL_TIMEOUT",
    )


class _AuthEnvironmentSettings(_AppEnvironmentSettings):
    issuer: NonEmptyStr | None = Field(default=None, validation_alias="AUTH_ISSUER")
    audience: NonEmptyStr | None = Field(default=None, validation_alias="AUTH_AUDIENCE")
    jwks_uri: NonEmptyStr | None = Field(default=None, validation_alias="AUTH_JWKS_URI")
    jwks_cache_ttl_seconds: PositiveInt = Field(
        default=300,
        validation_alias="AUTH_JWKS_CACHE_TTL_SECONDS",
    )

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> Self:
        values = {
            "AUTH_ISSUER": self.issuer,
            "AUTH_AUDIENCE": self.audience,
            "AUTH_JWKS_URI": self.jwks_uri,
        }
        configured = [name for name, value in values.items() if value is not None]
        if configured and len(configured) != len(values):
            missing = ", ".join(name for name, value in values.items() if value is None)
            raise ValueError(
                f"Authentication settings must be configured together; missing: {missing}"
            )
        if not configured and self.app_env != LOCAL_APP_ENV:
            raise ValueError(
                f"Cognito authentication settings are required when "
                f"APP_ENV={self.app_env}: AUTH_ISSUER, AUTH_AUDIENCE, AUTH_JWKS_URI"
            )
        return self


class _HttpEnvironmentSettings(_AppEnvironmentSettings):
    cors_allowed_origins: NonEmptyStr | None = Field(
        default=None,
        validation_alias="CORS_ALLOWED_ORIGINS",
    )

    @model_validator(mode="after")
    def validate_cors_allowed_origins(self) -> Self:
        if self.cors_allowed_origins is None and self.app_env != LOCAL_APP_ENV:
            raise ValueError(
                "CORS_ALLOWED_ORIGINS is required outside local development"
            )
        if self.cors_allowed_origins is not None:
            _parse_cors_allowed_origins(self.cors_allowed_origins)
        return self


class _RuntimePodEnvironmentSettings(_EnvironmentSettings):
    model_client_mode: Annotated[
        Literal["fake", "gateway"],
        BeforeValidator(_normalize_model_client_mode),
    ] = Field(default="gateway", validation_alias="MODEL_CLIENT_MODE")
    provider_endpoint: NonEmptyStr = Field(
        default="https://openrouter.ai/api/v1/chat/completions",
        validation_alias="PROVIDER_ENDPOINT",
    )
    model_name: NonEmptyStr = Field(
        default="deepseek/deepseek-v3.2",
        validation_alias="MODEL_NAME",
    )


class _InstructorProvisioningEnvironmentSettings(_EnvironmentSettings):
    enabled: bool = Field(
        default=False,
        validation_alias="INSTRUCTOR_PROVISIONING_ENABLED",
    )
    cognito_user_pool_id: NonEmptyStr | None = Field(
        default=None,
        validation_alias="COGNITO_USER_POOL_ID",
    )
    cognito_region: NonEmptyStr | None = Field(
        default=None,
        validation_alias="COGNITO_REGION",
    )
    cognito_instructor_group_name: NonEmptyStr = Field(
        default="instructor",
        validation_alias="COGNITO_INSTRUCTOR_GROUP_NAME",
    )

    @model_validator(mode="after")
    def validate_cognito_configuration(self) -> Self:
        if not self.enabled:
            return self
        missing = [
            name
            for name, value in {
                "COGNITO_USER_POOL_ID": self.cognito_user_pool_id,
                "COGNITO_REGION": self.cognito_region,
            }.items()
            if value is None
        ]
        if missing:
            raise ValueError(
                "Instructor provisioning is enabled but required settings are "
                f"missing: {', '.join(missing)}"
            )
        return self


class _OrchestratorEnvironmentSettings(_EnvironmentSettings):
    provisioning_worker_poll_interval_seconds: PositiveFiniteFloat = Field(
        default=0.1,
        validation_alias="ORCHESTRATOR_PROVISIONING_WORKER_POLL_INTERVAL_SECONDS",
    )
    readiness_timeout_seconds: PositiveFiniteFloat = Field(
        default=30.0,
        validation_alias="ORCHESTRATOR_READINESS_TIMEOUT_SECONDS",
    )
    readiness_poll_interval_seconds: PositiveFiniteFloat = Field(
        default=0.1,
        validation_alias="ORCHESTRATOR_READINESS_POLL_INTERVAL_SECONDS",
    )
    provisioning_retry_backoff_seconds: PositiveInt = Field(
        default=15,
        validation_alias="ORCHESTRATOR_PROVISIONING_RETRY_BACKOFF_SECONDS",
    )
    cleanup_max_attempts: PositiveInt = Field(
        default=3,
        validation_alias="ORCHESTRATOR_CLEANUP_MAX_ATTEMPTS",
    )
    cleanup_retry_backoff_seconds: PositiveInt = Field(
        default=15,
        validation_alias="ORCHESTRATOR_CLEANUP_RETRY_BACKOFF_SECONDS",
    )
    cleanup_reverify_backoff_seconds: PositiveInt = Field(
        default=5,
        validation_alias="ORCHESTRATOR_CLEANUP_REVERIFY_BACKOFF_SECONDS",
    )
    provisioning_timeout_seconds: PositiveInt = Field(
        default=900,
        validation_alias="ORCHESTRATOR_PROVISIONING_TIMEOUT_SECONDS",
    )
    max_session_lifetime_seconds: PositiveInt = Field(
        default=86_400,
        validation_alias="ORCHESTRATOR_MAX_SESSION_LIFETIME_SECONDS",
    )


def get_app_env() -> str:
    return _AppEnvironmentSettings().app_env


def get_admission_settings() -> AdmissionSettings:
    settings = _AdmissionEnvironmentSettings()
    return AdmissionSettings(
        max_sessions_per_user=settings.max_sessions_per_user,
        max_sessions_global=settings.max_sessions_global,
    )


def get_enrollment_settings() -> EnrollmentSettings:
    settings = _EnrollmentEnvironmentSettings()
    token_secret = (
        settings.token_secret.get_secret_value()
        if settings.token_secret is not None
        else LOCAL_ENROLLMENT_TOKEN_SECRET
    )
    return EnrollmentSettings(
        token_secret=token_secret,
        token_ttl_seconds=settings.token_ttl_seconds,
    )


def get_database_url() -> str:
    # Required settings are supplied dynamically by BaseSettings.
    return _DatabaseEnvironmentSettings().database_url  # type: ignore[call-arg]


def get_runtime_client_config() -> RuntimeClientConfig:
    settings = _RuntimeClientEnvironmentSettings()
    return RuntimeClientConfig(
        base_url="http://placeholder",
        timeout_seconds=settings.timeout_seconds,
        auth_token=(
            settings.auth_token.get_secret_value()
            if settings.auth_token is not None
            else None
        ),
    )


def get_email_classifier_settings() -> EmailClassifierSettings:
    # Required settings are supplied dynamically by BaseSettings.
    settings = _EmailClassifierEnvironmentSettings()  # type: ignore[call-arg]
    return EmailClassifierSettings(
        openrouter_api_key=settings.openrouter_api_key.get_secret_value(),
        provider_endpoint=settings.provider_endpoint,
        model_name=settings.model_name,
        model_timeout=settings.model_timeout,
    )


def get_auth_verifier_config() -> AuthVerifierConfig:
    settings = _AuthEnvironmentSettings()
    return AuthVerifierConfig(
        issuer=settings.issuer or "",
        audience=settings.audience or "",
        jwks_uri=settings.jwks_uri or "",
        jwks_cache_ttl_seconds=settings.jwks_cache_ttl_seconds,
    )


def _parse_cors_allowed_origins(raw_origins: str) -> tuple[str, ...]:
    origins: list[str] = []
    for raw_origin in raw_origins.split(","):
        origin = raw_origin.strip().rstrip("/")
        parsed = urlparse(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.params
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "CORS_ALLOWED_ORIGINS must be a comma-separated list of HTTP(S) origins"
            )
        if origin not in origins:
            origins.append(origin)
    if not origins:
        raise ValueError("CORS_ALLOWED_ORIGINS must contain at least one origin")
    return tuple(origins)


def get_http_settings() -> HttpSettings:
    settings = _HttpEnvironmentSettings()
    origins = (
        _parse_cors_allowed_origins(settings.cors_allowed_origins)
        if settings.cors_allowed_origins is not None
        else LOCAL_CORS_ALLOWED_ORIGINS
    )
    return HttpSettings(cors_allowed_origins=origins)


def get_runtime_pod_env_settings() -> RuntimePodEnvSettings:
    settings = _RuntimePodEnvironmentSettings()
    return RuntimePodEnvSettings(
        model_client_mode=settings.model_client_mode,
        provider_endpoint=settings.provider_endpoint,
        model_name=settings.model_name,
    )


def get_instructor_provisioning_settings() -> InstructorProvisioningSettings:
    settings = _InstructorProvisioningEnvironmentSettings()
    return InstructorProvisioningSettings(
        enabled=settings.enabled,
        cognito_user_pool_id=settings.cognito_user_pool_id or "",
        cognito_region=settings.cognito_region or "",
        cognito_instructor_group_name=settings.cognito_instructor_group_name,
    )


def get_orchestrator_settings() -> OrchestratorSettings:
    settings = _OrchestratorEnvironmentSettings()
    return OrchestratorSettings(
        provisioning_worker_poll_interval_seconds=(
            settings.provisioning_worker_poll_interval_seconds
        ),
        readiness_timeout_seconds=settings.readiness_timeout_seconds,
        readiness_poll_interval_seconds=settings.readiness_poll_interval_seconds,
        provisioning_retry_backoff_seconds=(
            settings.provisioning_retry_backoff_seconds
        ),
        cleanup_max_attempts=settings.cleanup_max_attempts,
        cleanup_retry_backoff_seconds=settings.cleanup_retry_backoff_seconds,
        cleanup_reverify_backoff_seconds=settings.cleanup_reverify_backoff_seconds,
        provisioning_timeout_seconds=settings.provisioning_timeout_seconds,
        max_session_lifetime_seconds=settings.max_session_lifetime_seconds,
    )


def validate_control_plane_settings() -> None:
    """Validate security-sensitive HTTP configuration before accepting traffic."""
    _AppEnvironmentSettings()
    _AdmissionEnvironmentSettings()
    _EnrollmentEnvironmentSettings()
    _RuntimeClientEnvironmentSettings()
    _AuthEnvironmentSettings()
    _HttpEnvironmentSettings()
    _InstructorProvisioningEnvironmentSettings()
    _OrchestratorEnvironmentSettings()
