from apps.control_plane.src.application.auth.errors import AuthTokenInvalidError
from apps.control_plane.src.application.auth.ports import TokenVerifierPort
from apps.control_plane.src.application.auth.types import AuthClaims

from .types import AuthVerifierConfig


class LocalTokenVerifier(TokenVerifierPort):
    """Development-only verifier for ``local:<username>[:role]`` bearer tokens."""

    def __init__(self, config: AuthVerifierConfig) -> None:
        self._config = config

    def verify_access_token(self, token: str) -> AuthClaims:
        _ = self._config

        normalized = token.strip()
        if not normalized:
            raise AuthTokenInvalidError()

        parts = normalized.split(":")
        if len(parts) not in (2, 3) or parts[0] != "local":
            raise AuthTokenInvalidError()

        username = parts[1].strip()
        if not username:
            raise AuthTokenInvalidError()

        role = "learner"
        if len(parts) == 3:
            role = parts[2].strip() or "learner"

        if "@" in username:
            email = username
        else:
            email = f"{username}@example.test"

        return AuthClaims(
            sub=f"local-user:{username}",
            email=email,
            roles=(role,),
            scopes=(),
            issued_at=None,
            expires_at=None,
        )
