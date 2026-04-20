from fastapi import Depends, Header, WebSocket
from apps.control_plane.src.application.auth.errors import (
    AuthTokenExpiredError,
    AuthTokenInvalidError,
)
from apps.control_plane.src.application.auth.mapper import auth_claims_to_principal
from apps.control_plane.src.application.auth.ports import TokenVerifierPort
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.interfaces.http.dependencies import get_token_verifier


class UnauthenticatedError(Exception):
    pass


def _extract_bearer_token(authorization: str) -> str:
    header_value = authorization.strip()
    if not header_value.startswith("Bearer "):
        raise UnauthenticatedError()

    token = header_value.removeprefix("Bearer ").strip()
    if not token:
        raise UnauthenticatedError()

    return token


def _principal_from_token(token: str, verifier: TokenVerifierPort) -> PrincipalContext:
    token = token.strip()
    if not token:
        raise UnauthenticatedError()

    try:
        claims = verifier.verify_access_token(token=token)
        return auth_claims_to_principal(claims)
    except (AuthTokenInvalidError, AuthTokenExpiredError):
        raise UnauthenticatedError()


def get_current_principal(
    authorization: str = Header(..., alias="Authorization"),
    verifier: TokenVerifierPort = Depends(get_token_verifier),
) -> PrincipalContext:
    token = _extract_bearer_token(authorization)
    return _principal_from_token(token=token, verifier=verifier)


def get_current_principal_ws(websocket: WebSocket) -> PrincipalContext:
    verifier = get_token_verifier()

    token_qs = websocket.query_params.get("access_token")
    if token_qs:
        return _principal_from_token(token=token_qs, verifier=verifier)

    header = websocket.headers.get("authorization")
    if not header:
        raise UnauthenticatedError()

    token = _extract_bearer_token(header)
    return _principal_from_token(token=token, verifier=verifier)
