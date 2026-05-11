from dataclasses import dataclass
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
    runtime_shared_token: str
    model_client_mode: str
    provider_endpoint: str
    model_name: str
    openrouter_api_key: str


@dataclass(frozen=True)
class AdmissionSettings:
    max_sessions_per_user: int
    max_sessions_global: int


@dataclass(frozen=True)
class EnrollmentSettings:
    token_secret: str
    token_ttl_seconds: int


def _get_optional_str(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


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
    if value <= 0:
        raise RuntimeError(f"{name} must be > 0")
    return value


def _get_int(name: str, *, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_admission_settings() -> AdmissionSettings:
    return AdmissionSettings(
        max_sessions_per_user=_get_int("ADMISSION_MAX_SESSIONS_PER_USER", default=3),
        max_sessions_global=_get_int("ADMISSION_MAX_SESSIONS_GLOBAL", default=20),
    )


def get_enrollment_settings() -> EnrollmentSettings:
    return EnrollmentSettings(
        token_secret=_get_optional_str("ENROLLMENT_TOKEN_SECRET")
        or "local-dev-enrollment-secret",
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
    timeout_raw = os.getenv("RUNTIME_TIMEOUT_SECONDS", "").strip()
    auth_token = _get_optional_str("RUNTIME_SHARED_TOKEN")
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError:
        timeout_seconds = 10.0
    return RuntimeClientConfig(
        base_url="http://placeholder",
        timeout_seconds=timeout_seconds,
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
    return AuthVerifierConfig(
        issuer=_get_optional_str("AUTH_ISSUER") or "",
        audience=_get_optional_str("AUTH_AUDIENCE") or "",
        jwks_uri=_get_optional_str("AUTH_JWKS_URI") or "",
        jwks_cache_ttl_seconds=_get_int("AUTH_JWKS_CACHE_TTL_SECONDS", default=300),
    )


def get_runtime_pod_env_settings() -> RuntimePodEnvSettings:
    model_client_mode = (_get_optional_str("MODEL_CLIENT_MODE") or "gateway").lower()
    runtime_shared_token = _get_optional_str("RUNTIME_SHARED_TOKEN")

    return RuntimePodEnvSettings(
        runtime_shared_token=runtime_shared_token or "",
        model_client_mode=model_client_mode,
        provider_endpoint=(
            _get_optional_str("PROVIDER_ENDPOINT")
            or "https://openrouter.ai/api/v1/chat/completions"
        ),
        model_name=_get_optional_str("MODEL_NAME") or "deepseek/deepseek-v3.2",
        openrouter_api_key=_get_optional_str("OPENROUTER_API_KEY") or "",
    )
