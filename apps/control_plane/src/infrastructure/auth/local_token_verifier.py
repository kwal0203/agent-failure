from apps.control_plane.src.application.auth.errors import AuthTokenInvalidError
from apps.control_plane.src.application.auth.ports import TokenVerifierPort
from apps.control_plane.src.application.auth.types import AuthClaims

from .types import AuthVerifierConfig


class LocalTokenVerifier(TokenVerifierPort):
    """
    Temporary verifier used during auth migration.

    It keeps support for the existing local bearer format while we introduce
    provider-driven verification. Constructor is already config-driven so
    Cognito/JWKS verifier can replace internals without touching call sites.
    """

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
            email = f"{username}@gatech.edu"

        return AuthClaims(
            sub=f"local-user:{username}",
            email=email,
            roles=(role,),
            scopes=(),
            issued_at=None,
            expires_at=None,
        )
