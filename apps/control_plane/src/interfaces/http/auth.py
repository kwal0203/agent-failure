from uuid import uuid5, NAMESPACE_URL
from fastapi import Header, WebSocket
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

    user_id = uuid5(namespace=NAMESPACE_URL, name=f"local-user:{username}")
    return PrincipalContext(user_id=user_id, role=role)


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
