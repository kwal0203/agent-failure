from fastapi import Header, HTTPException, status

import os


def require_internal_auth(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    # TODO(auth-hardening): MVP shortcut. This static shared-token check is only
    # for local/staging bring-up. Replace with service-to-service identity
    # (mTLS or short-lived service JWT via workload identity) before internet
    # exposure, and source credentials from secret manager/cluster identity.
    expected = os.getenv("RUNTIME_SHARED_TOKEN", "").strip()
    if not os.getenv("RUNTIME_SHARED_TOKEN", "").strip():
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
