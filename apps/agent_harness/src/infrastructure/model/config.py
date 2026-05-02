from .types import GatewayConfig
from apps.agent_harness.src.infrastructure.config.settings import (
    get_gateway_settings,
)


def load_gateway_config() -> GatewayConfig:
    settings = get_gateway_settings()
    return GatewayConfig(
        endpoint=settings.endpoint,
        api_key=settings.api_key,
        model=settings.model,
        timeout_seconds=settings.timeout_seconds,
    )
