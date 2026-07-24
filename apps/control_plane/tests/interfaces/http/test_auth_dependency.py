from datetime import datetime, timezone
from uuid import uuid4

import pytest

from apps.control_plane.src.application.auth.errors import (
    AuthTokenExpiredError,
    AuthTokenInvalidError,
)
from apps.control_plane.src.application.auth.types import AuthClaims
from apps.control_plane.src.interfaces.http.auth import (
    UnauthenticatedError,
    get_current_principal,
)


class _FakeVerifier:
    def __init__(
        self,
        *,
        claims: AuthClaims | None = None,
        exc: Exception | None = None,
    ) -> None:
        self._claims = claims
        self._exc = exc
        self.called_with: str | None = None

    def verify_access_token(self, token: str) -> AuthClaims:
        self.called_with = token
        if self._exc is not None:
            raise self._exc
        assert self._claims is not None
        return self._claims


def test_get_current_principal_returns_principal_from_verifier_claims() -> None:
    claims = AuthClaims(
        sub=str(uuid4()),
        email="learner@example.com",
        roles=("admin",),
        scopes=("sessions:read",),
        issued_at=datetime.now(timezone.utc),
        expires_at=None,
    )
    verifier = _FakeVerifier(claims=claims)

    principal = get_current_principal(
        authorization="Bearer token-123",
        verifier=verifier,
    )

    assert verifier.called_with == "token-123"
    assert str(principal.user_id) == claims.sub
    assert principal.role == "admin"


@pytest.mark.parametrize(
    "exc",
    [
        AuthTokenInvalidError(),
        AuthTokenExpiredError(),
    ],
)
def test_get_current_principal_raises_unauthenticated_for_invalid_or_expired_token(
    exc: Exception,
) -> None:
    verifier = _FakeVerifier(exc=exc)
    with pytest.raises(UnauthenticatedError):
        get_current_principal(
            authorization="Bearer token-123",
            verifier=verifier,
        )


def test_get_current_principal_rejects_non_bearer_header_before_verifier() -> None:
    verifier = _FakeVerifier(
        claims=AuthClaims(
            sub=str(uuid4()),
            email=None,
            roles=("learner",),
            scopes=(),
            issued_at=None,
            expires_at=None,
        )
    )

    with pytest.raises(UnauthenticatedError):
        get_current_principal(
            authorization="Token abc",
            verifier=verifier,
        )

    assert verifier.called_with is None


def test_get_current_principal_accepts_external_email_claim() -> None:
    verifier = _FakeVerifier(
        claims=AuthClaims(
            sub=str(uuid4()),
            email="kane@example.com",
            roles=("learner",),
            scopes=(),
            issued_at=None,
            expires_at=None,
        )
    )

    principal = get_current_principal(
        authorization="Bearer token-123",
        verifier=verifier,
    )
    assert principal.role == "learner"


def test_get_current_principal_accepts_local_subject_email() -> None:
    verifier = _FakeVerifier(
        claims=AuthClaims(
            sub="local-user:kane@example.com",
            email=None,
            roles=("learner",),
            scopes=(),
            issued_at=None,
            expires_at=None,
        )
    )

    principal = get_current_principal(
        authorization="Bearer local:kane@example.com:learner",
        verifier=verifier,
    )

    assert principal.role == "learner"
