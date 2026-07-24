from collections.abc import Callable, Generator
import asyncio

from pydantic import ValidationError
import pytest

from apps.control_plane.src.infrastructure.auth.cognito_jwt_verifier import (
    CognitoJwtVerifier,
)
from apps.control_plane.src.infrastructure.auth.local_token_verifier import (
    LocalTokenVerifier,
)
from apps.control_plane.src.infrastructure.config.settings import (
    LOCAL_ENROLLMENT_TOKEN_SECRET,
    get_admission_settings,
    get_app_env,
    get_auth_verifier_config,
    get_enrollment_settings,
    get_instructor_provisioning_settings,
    get_orchestrator_settings,
    get_runtime_client_config,
    get_runtime_pod_env_settings,
)
from apps.control_plane.src.interfaces.http import dependencies
import apps.control_plane.src.interfaces.http.main as main_module


AUTH_ENV_NAMES = ("AUTH_ISSUER", "AUTH_AUDIENCE", "AUTH_JWKS_URI")


def _clear_auth_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in AUTH_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def _set_auth_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_ISSUER", "https://issuer.example.test/pool")
    monkeypatch.setenv("AUTH_AUDIENCE", "client-id")
    monkeypatch.setenv("AUTH_JWKS_URI", "https://issuer.example.test/pool/jwks.json")


@pytest.fixture(autouse=True)
def _clear_auth_dependency_caches() -> Generator[None, None, None]:
    dependencies.get_auth_verifier_config.cache_clear()
    dependencies.get_token_verifier.cache_clear()
    yield
    dependencies.get_auth_verifier_config.cache_clear()
    dependencies.get_token_verifier.cache_clear()


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("dev", "dev"),
        ("development", "dev"),
        ("local", "dev"),
        ("stage", "staging"),
        ("staging", "staging"),
        ("prod", "production"),
        ("production", "production"),
    ],
)
def test_get_app_env_accepts_only_known_values(
    monkeypatch: pytest.MonkeyPatch,
    configured: str,
    expected: str,
) -> None:
    monkeypatch.setenv("APP_ENV", configured)
    assert get_app_env() == expected


def test_get_app_env_defaults_to_fail_closed_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    assert get_app_env() == "staging"


def test_get_app_env_rejects_unknown_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "preview")
    with pytest.raises(ValidationError, match="APP_ENV"):
        get_app_env()


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_auth_is_required_outside_local_development(
    monkeypatch: pytest.MonkeyPatch,
    app_env: str,
) -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    _clear_auth_settings(monkeypatch)

    with pytest.raises(ValidationError, match="Cognito authentication settings"):
        get_auth_verifier_config()


def test_partial_auth_configuration_is_always_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    _clear_auth_settings(monkeypatch)
    monkeypatch.setenv("AUTH_ISSUER", "https://issuer.example.test/pool")

    with pytest.raises(
        ValidationError,
        match="AUTH_AUDIENCE, AUTH_JWKS_URI",
    ):
        get_auth_verifier_config()


def test_local_token_verifier_is_available_only_in_dev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    _clear_auth_settings(monkeypatch)

    assert isinstance(dependencies.get_token_verifier(), LocalTokenVerifier)

    dependencies.get_auth_verifier_config.cache_clear()
    dependencies.get_token_verifier.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    _set_auth_settings(monkeypatch)

    assert isinstance(dependencies.get_token_verifier(), CognitoJwtVerifier)


def test_enrollment_secret_is_required_outside_dev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("ENROLLMENT_TOKEN_SECRET", raising=False)

    with pytest.raises(ValidationError, match="ENROLLMENT_TOKEN_SECRET"):
        get_enrollment_settings()


def test_dev_uses_local_enrollment_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("ENROLLMENT_TOKEN_SECRET", raising=False)

    assert get_enrollment_settings().token_secret == LOCAL_ENROLLMENT_TOKEN_SECRET


def test_enrollment_secret_must_be_at_least_32_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    configured_secret = "visibly-too-short-secret"
    monkeypatch.setenv("ENROLLMENT_TOKEN_SECRET", configured_secret)

    with pytest.raises(ValidationError, match="at least 32 bytes") as exc_info:
        get_enrollment_settings()
    assert configured_secret not in str(exc_info.value)


@pytest.mark.parametrize(
    ("name", "value", "getter"),
    [
        (
            "ADMISSION_MAX_SESSIONS_PER_USER",
            "many",
            get_admission_settings,
        ),
        (
            "ADMISSION_MAX_SESSIONS_GLOBAL",
            "0",
            get_admission_settings,
        ),
        (
            "AUTH_JWKS_CACHE_TTL_SECONDS",
            "-1",
            get_auth_verifier_config,
        ),
        (
            "ENROLLMENT_TOKEN_TTL_SECONDS",
            "soon",
            get_enrollment_settings,
        ),
        (
            "RUNTIME_TIMEOUT_SECONDS",
            "nan",
            get_runtime_client_config,
        ),
        (
            "ORCHESTRATOR_CLEANUP_MAX_ATTEMPTS",
            "0",
            get_orchestrator_settings,
        ),
        (
            "ORCHESTRATOR_READINESS_TIMEOUT_SECONDS",
            "forever",
            get_orchestrator_settings,
        ),
    ],
)
def test_invalid_numeric_settings_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    value: str,
    getter: Callable[[], object],
) -> None:
    monkeypatch.setenv("APP_ENV", "dev")
    _clear_auth_settings(monkeypatch)
    monkeypatch.delenv("ENROLLMENT_TOKEN_SECRET", raising=False)
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        getter()


def test_invalid_boolean_setting_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INSTRUCTOR_PROVISIONING_ENABLED", "sometimes")

    with pytest.raises(ValidationError, match="INSTRUCTOR_PROVISIONING_ENABLED"):
        get_instructor_provisioning_settings()


def test_invalid_model_client_mode_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MODEL_CLIENT_MODE", "gateawy")

    with pytest.raises(ValidationError, match="MODEL_CLIENT_MODE"):
        get_runtime_pod_env_settings()


def test_orchestrator_accepts_subsecond_provisioning_intervals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ORCHESTRATOR_PROVISIONING_WORKER_POLL_INTERVAL_SECONDS",
        "0.1",
    )
    monkeypatch.setenv(
        "ORCHESTRATOR_READINESS_POLL_INTERVAL_SECONDS",
        "0.1",
    )

    settings = get_orchestrator_settings()

    assert settings.provisioning_worker_poll_interval_seconds == 0.1
    assert settings.readiness_poll_interval_seconds == 0.1


def test_enabled_instructor_provisioning_requires_cognito_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INSTRUCTOR_PROVISIONING_ENABLED", "true")
    monkeypatch.delenv("COGNITO_USER_POOL_ID", raising=False)
    monkeypatch.delenv("COGNITO_REGION", raising=False)

    with pytest.raises(ValidationError, match="COGNITO_USER_POOL_ID, COGNITO_REGION"):
        get_instructor_provisioning_settings()


def test_http_lifespan_rejects_insecure_production_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENROLLMENT_TOKEN_SECRET", "x" * 32)
    _clear_auth_settings(monkeypatch)

    async def _start_app() -> None:
        async with main_module.app.router.lifespan_context(main_module.app):
            pytest.fail("Application started with insecure production configuration")

    with pytest.raises(ValidationError, match="Cognito authentication settings"):
        asyncio.run(_start_app())
