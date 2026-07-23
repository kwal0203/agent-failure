from dataclasses import dataclass
import math
import os
from urllib.parse import urlparse

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


LOCAL_APP_ENV = "dev"
LOCAL_ENROLLMENT_TOKEN_SECRET = "local-dev-enrollment-secret-32-bytes-min"


def _get_optional_str(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def get_app_env() -> str:
    raw = (_get_optional_str("APP_ENV") or "staging").strip().lower()
    if raw in {"production", "prod"}:
        return "production"
    if raw in {"staging", "stage"}:
        return "staging"
    if raw in {"dev", "development", "local"}:
        return LOCAL_APP_ENV
    raise RuntimeError(
        f"Invalid APP_ENV: {raw!r}. Expected one of: dev, staging, production"
    )


def _require_str(name: str) -> str:
    value = _get_optional_str(name)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_float(name: str, *, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"Invalid float for {name}: {raw!r}") from exc
    if not math.isfinite(value) or value <= 0:
        raise RuntimeError(f"{name} must be a finite number > 0")
    return value


def _get_int(name: str, *, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Invalid integer for {name}: {raw!r}") from exc
    if value < minimum:
        raise RuntimeError(f"{name} must be >= {minimum}")
    return value


def get_admission_settings() -> AdmissionSettings:
    return AdmissionSettings(
        max_sessions_per_user=_get_int("ADMISSION_MAX_SESSIONS_PER_USER", default=3),
        max_sessions_global=_get_int("ADMISSION_MAX_SESSIONS_GLOBAL", default=20),
    )


def get_enrollment_settings() -> EnrollmentSettings:
    app_env = get_app_env()
    configured_secret = _get_optional_str("ENROLLMENT_TOKEN_SECRET")
    if configured_secret is None and app_env != LOCAL_APP_ENV:
        raise RuntimeError(
            "Missing required environment variable outside local development: "
            "ENROLLMENT_TOKEN_SECRET"
        )

    token_secret = configured_secret or LOCAL_ENROLLMENT_TOKEN_SECRET
    if len(token_secret.encode()) < 32:
        raise RuntimeError("ENROLLMENT_TOKEN_SECRET must be at least 32 bytes")

    return EnrollmentSettings(
        token_secret=token_secret,
        token_ttl_seconds=_get_int("ENROLLMENT_TOKEN_TTL_SECONDS", default=600),
    )


def get_database_url() -> str:
    value = _get_optional_str("DATABASE_URL")
    if value is None:
        raise ValueError("DATABASE_URL environment variable not set.")
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    in_k8s = bool(_get_optional_str("KUBERNETES_SERVICE_HOST"))
    if in_k8s and host in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError(
            "Invalid DATABASE_URL for Kubernetes runtime: host resolves to localhost. "
            "Use a reachable service hostname or external DB endpoint."
        )
    return value


def get_runtime_client_config() -> RuntimeClientConfig:
    auth_token = _get_optional_str("RUNTIME_SHARED_TOKEN")
    return RuntimeClientConfig(
        base_url="http://placeholder",
        timeout_seconds=_get_float("RUNTIME_TIMEOUT_SECONDS", default=10.0),
        auth_token=auth_token,
    )


def get_email_classifier_settings() -> EmailClassifierSettings:
    return EmailClassifierSettings(
        openrouter_api_key=_require_str("OPENROUTER_API_KEY"),
        provider_endpoint=_require_str("PROVIDER_ENDPOINT"),
        model_name=_require_str("MODEL_NAME"),
        model_timeout=_get_float("MODEL_TIMEOUT", default=30.0),
    )


def get_auth_verifier_config() -> AuthVerifierConfig:
    app_env = get_app_env()
    values = {
        "AUTH_ISSUER": _get_optional_str("AUTH_ISSUER"),
        "AUTH_AUDIENCE": _get_optional_str("AUTH_AUDIENCE"),
        "AUTH_JWKS_URI": _get_optional_str("AUTH_JWKS_URI"),
    }
    configured = [name for name, value in values.items() if value is not None]
    if configured and len(configured) != len(values):
        missing = ", ".join(name for name, value in values.items() if value is None)
        raise RuntimeError(
            f"Authentication settings must be configured together; missing: {missing}"
        )
    if not configured and app_env != LOCAL_APP_ENV:
        raise RuntimeError(
            f"Cognito authentication settings are required when APP_ENV={app_env}: "
            "AUTH_ISSUER, AUTH_AUDIENCE, AUTH_JWKS_URI"
        )

    return AuthVerifierConfig(
        issuer=values["AUTH_ISSUER"] or "",
        audience=values["AUTH_AUDIENCE"] or "",
        jwks_uri=values["AUTH_JWKS_URI"] or "",
        jwks_cache_ttl_seconds=_get_int("AUTH_JWKS_CACHE_TTL_SECONDS", default=300),
    )


def get_runtime_pod_env_settings() -> RuntimePodEnvSettings:
    model_client_mode = (_get_optional_str("MODEL_CLIENT_MODE") or "gateway").lower()
    if model_client_mode not in {"fake", "gateway"}:
        raise RuntimeError("Invalid MODEL_CLIENT_MODE. Expected one of: fake, gateway")

    return RuntimePodEnvSettings(
        model_client_mode=model_client_mode,
        provider_endpoint=(
            _get_optional_str("PROVIDER_ENDPOINT")
            or "https://openrouter.ai/api/v1/chat/completions"
        ),
        model_name=_get_optional_str("MODEL_NAME") or "deepseek/deepseek-v3.2",
    )


def _get_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(
        f"Invalid boolean for {name}: {raw!r}. "
        "Expected one of: true, false, 1, 0, yes, no, on, off"
    )


def get_instructor_provisioning_settings() -> InstructorProvisioningSettings:
    enabled = _get_bool("INSTRUCTOR_PROVISIONING_ENABLED", default=False)
    cognito_user_pool_id = _get_optional_str("COGNITO_USER_POOL_ID")
    cognito_region = _get_optional_str("COGNITO_REGION")
    if enabled:
        missing = [
            name
            for name, value in {
                "COGNITO_USER_POOL_ID": cognito_user_pool_id,
                "COGNITO_REGION": cognito_region,
            }.items()
            if value is None
        ]
        if missing:
            raise RuntimeError(
                "Instructor provisioning is enabled but required settings are "
                f"missing: {', '.join(missing)}"
            )

    return InstructorProvisioningSettings(
        enabled=enabled,
        cognito_user_pool_id=cognito_user_pool_id or "",
        cognito_region=cognito_region or "",
        cognito_instructor_group_name=(
            _get_optional_str("COGNITO_INSTRUCTOR_GROUP_NAME") or "instructor"
        ),
    )


def validate_control_plane_settings() -> None:
    """Validate security-sensitive HTTP configuration before accepting traffic."""
    get_app_env()
    get_admission_settings()
    get_enrollment_settings()
    get_runtime_client_config()
    get_auth_verifier_config()
    get_instructor_provisioning_settings()
