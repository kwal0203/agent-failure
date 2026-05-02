from dataclasses import dataclass

from apps.evaluator.src.infrastructure.config.settings import (
    get_evaluator_runtime_settings,
)


@dataclass(frozen=True)
class EvaluatorRuntimeConfig:
    openrouter_api_key: str
    provider_endpoint: str
    model_name: str
    model_timeout: float


def load_evaluator_runtime_config() -> EvaluatorRuntimeConfig:
    settings = get_evaluator_runtime_settings()
    return EvaluatorRuntimeConfig(
        openrouter_api_key=settings.openrouter_api_key,
        provider_endpoint=settings.provider_endpoint,
        model_name=settings.model_name,
        model_timeout=settings.model_timeout,
    )
