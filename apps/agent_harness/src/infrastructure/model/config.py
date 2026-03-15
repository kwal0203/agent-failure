from .types import GatewayConfig

import os


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required env variable: {name}")
    return value


def load_gateway_config() -> GatewayConfig:
    endpoint = _required_env("PROVIDER_ENDPOINT")
    api_key = _required_env("OPENROUTER_API_KEY")
    model = _required_env("MODEL_NAME")

    raw_timeout = os.getenv("MODEL_TIMEOUT", "30").strip()
    try:
        timeout = float(raw_timeout)
    except ValueError as exc:
        raise ValueError(
            f"Invalid MODEL_TIMEOUT value '{raw_timeout}'. Must be a number."
        ) from exc

    if timeout <= 0:
        raise ValueError("MODEL_TIMEOUT must be > 0")

    return GatewayConfig(
        endpoint=endpoint, api_key=api_key, model=model, timeout_seconds=timeout
    )
