from dataclasses import dataclass


@dataclass(frozen=True)
class GatewayConfig:
    endpoint: str
    api_key: str
    model: str
    timeout_seconds: float
