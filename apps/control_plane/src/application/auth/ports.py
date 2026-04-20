from typing import Protocol

from .types import AuthClaims


class TokenVerifierPort(Protocol):
    def verify_access_token(self, token: str) -> AuthClaims: ...
