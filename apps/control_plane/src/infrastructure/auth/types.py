from dataclasses import dataclass


@dataclass(frozen=True)
class AuthVerifierConfig:
    issuer: str
    audience: str
    jwks_uri: str
