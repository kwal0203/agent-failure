from uuid import NAMESPACE_URL, UUID, uuid5

from apps.control_plane.src.application.common.types import PrincipalContext

from .errors import AuthTokenInvalidError
from .types import AuthClaims


def _resolve_user_id_from_subject(sub: str) -> UUID:
    subject = sub.strip()
    if not subject:
        raise AuthTokenInvalidError(
            code="AUTH_TOKEN_SUBJECT_MISSING",
            message="Authentication token subject is missing.",
        )

    try:
        return UUID(subject)
    except ValueError:
        # Deterministic fallback for external subjects that are not UUIDs.
        return uuid5(namespace=NAMESPACE_URL, name=subject)


def _resolve_role(roles: tuple[str, ...]) -> str:
    normalized_roles = {item.strip().lower() for item in roles if item.strip()}

    if "admin" in normalized_roles:
        return "admin"
    if "learner" in normalized_roles:
        return "learner"

    return "learner"


def auth_claims_to_principal(claims: AuthClaims) -> PrincipalContext:
    normalized_email = (claims.email or "").strip().lower() or None
    return PrincipalContext(
        user_id=_resolve_user_id_from_subject(claims.sub),
        role=_resolve_role(claims.roles),
        email=normalized_email,
    )
