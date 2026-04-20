from fastapi import Header, WebSocket
from apps.control_plane.src.application.auth.mapper import auth_claims_to_principal
from apps.control_plane.src.application.auth.types import AuthClaims
from apps.control_plane.src.application.common.types import PrincipalContext


class UnauthenticatedError(Exception):
    pass


def _principal_from_token(token: str) -> PrincipalContext:
    token = token.strip()
    if not token:
        raise UnauthenticatedError()

    parts = token.split(":")
    if len(parts) not in (2, 3) or parts[0] != "local":
        raise UnauthenticatedError()

    username = parts[1].strip()
    if not username:
        raise UnauthenticatedError()

    role = "learner"
    if len(parts) == 3:
        role = parts[2].strip() or "learner"

    claims = AuthClaims(
        sub=f"local-user:{username}",
        email=None,
        roles=(role,),
        scopes=(),
        issued_at=None,
        expires_at=None,
    )
    return auth_claims_to_principal(claims)


def get_current_principal(
    authorization: str = Header(..., alias="Authorization"),
) -> PrincipalContext:
    if not authorization.startswith("Bearer "):
        raise UnauthenticatedError()

    token = authorization.removeprefix("Bearer ")
    return _principal_from_token(token=token)


def get_current_principal_ws(websocket: WebSocket) -> PrincipalContext:
    token_qs = websocket.query_params.get("access_token")
    if token_qs:
        return _principal_from_token(token=token_qs)

    header = websocket.headers.get("authorization")
    if not header or not header.startswith("Bearer "):
        raise UnauthenticatedError()

    token = header.removeprefix("Bearer ")
    return _principal_from_token(token=token)
