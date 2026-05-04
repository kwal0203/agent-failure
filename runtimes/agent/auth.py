import logging

from fastapi import Header, HTTPException, status

from runtimes.agent.config.settings import get_runtime_shared_token

logger = logging.getLogger(__name__)


def require_internal_auth(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    expected = get_runtime_shared_token()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="runtime auth not configured",
        )

    logger.warning(
        "AUTH DEBUG authorization=%r expected_len=%d", authorization, len(expected)
    )

    if not authorization or not authorization.startswith("Bearer "):
        logger.warning("AUTH DEBUG missing or bad prefix")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )

    token = authorization.removeprefix("Bearer ").strip()
    logger.warning(
        "AUTH DEBUG token_len=%d expected_len=%d match=%s",
        len(token),
        len(expected),
        token == expected,
    )
    if token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )
