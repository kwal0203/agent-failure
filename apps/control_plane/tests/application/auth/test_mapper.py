from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest

from apps.control_plane.src.application.auth.errors import AuthTokenInvalidError
from apps.control_plane.src.application.auth.mapper import auth_claims_to_principal
from apps.control_plane.src.application.auth.types import AuthClaims


def _claims(*, sub: str, roles: tuple[str, ...]) -> AuthClaims:
    return AuthClaims(
        sub=sub,
        email=None,
        roles=roles,
        scopes=(),
        issued_at=datetime.now(timezone.utc),
        expires_at=None,
    )


def test_auth_claims_to_principal_prefers_admin_role() -> None:
    principal = auth_claims_to_principal(
        _claims(sub=str(uuid4()), roles=("learner", "admin"))
    )
    assert principal.role == "admin"


def test_auth_claims_to_principal_falls_back_to_learner_role() -> None:
    principal = auth_claims_to_principal(_claims(sub=str(uuid4()), roles=("viewer",)))
    assert principal.role == "learner"


def test_auth_claims_to_principal_uses_uuid_subject_when_available() -> None:
    sub = str(uuid4())
    principal = auth_claims_to_principal(_claims(sub=sub, roles=("learner",)))
    assert str(principal.user_id) == sub


def test_auth_claims_to_principal_uses_deterministic_uuid_for_non_uuid_subject() -> (
    None
):
    sub = "external-subject-123"
    principal = auth_claims_to_principal(_claims(sub=sub, roles=("learner",)))
    assert principal.user_id == uuid5(NAMESPACE_URL, sub)


def test_auth_claims_to_principal_raises_for_missing_subject() -> None:
    with pytest.raises(AuthTokenInvalidError):
        auth_claims_to_principal(_claims(sub="  ", roles=("learner",)))
