from dataclasses import dataclass


@dataclass(frozen=True)
class AuthVerifierConfig:
    issuer: str
    audience: str
    jwks_uri: str
    jwks_cache_ttl_seconds: int = 300
