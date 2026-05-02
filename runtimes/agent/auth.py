from fastapi import Header, HTTPException, status

from runtimes.agent.config.settings import get_runtime_shared_token


def require_internal_auth(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    expected = get_runtime_shared_token()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="runtime auth not configured",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )

    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )
