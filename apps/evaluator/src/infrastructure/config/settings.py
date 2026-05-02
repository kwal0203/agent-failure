from dataclasses import dataclass
import os


@dataclass(frozen=True)
class EvaluatorRuntimeSettings:
    openrouter_api_key: str
    provider_endpoint: str
    model_name: str
    model_timeout: float


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


def get_evaluator_runtime_settings() -> EvaluatorRuntimeSettings:
    return EvaluatorRuntimeSettings(
        openrouter_api_key=_require_env("OPENROUTER_API_KEY"),
        provider_endpoint=_require_env("PROVIDER_ENDPOINT"),
        model_name=_require_env("MODEL_NAME"),
        model_timeout=_get_float_env("MODEL_TIMEOUT", 30.0),
    )
