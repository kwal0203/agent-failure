from __future__ import annotations

import logging
from datetime import UTC, datetime

import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwt import InvalidTokenError, PyJWKClient
from jwt.exceptions import (
    PyJWKClientConnectionError,
    PyJWKClientError,
    PyJWKError,
    PyJWKSetError,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from apps.control_plane.src.application.auth.errors import (
    AuthTokenExpiredError,
    AuthTokenInvalidError,
)
from apps.control_plane.src.application.auth.ports import TokenVerifierPort
from apps.control_plane.src.application.auth.types import AuthClaims

from .types import AuthVerifierConfig

logger = logging.getLogger(__name__)


class TokenHeader(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kid: str


class CognitoAccessClaims(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    sub: str
    exp: int
    iat: int
    iss: str
    aud: str | list[str] | None = None
    client_id: str | None = None
    email: str | None = None
    token_use: str | None = None
    scope: str | None = None
    cognito_groups: list[str] = Field(default_factory=list, alias="cognito:groups")


class CognitoJwtVerifier(TokenVerifierPort):
    """
    Cognito JWT verifier using JWKS-based signature validation.
    """

    def __init__(self, config: AuthVerifierConfig) -> None:
        self._config = config
        self._jwks_client = (
            PyJWKClient(
                config.jwks_uri,
                cache_jwk_set=True,
                cache_keys=False,
                lifespan=config.jwks_cache_ttl_seconds,
                timeout=5,
            )
            if config.jwks_uri
            else None
        )

    def verify_access_token(self, token: str) -> AuthClaims:
        normalized = token.strip()
        if not normalized:
            raise AuthTokenInvalidError(code="AUTH_TOKEN_MISSING")

        signing_key = self._resolve_signing_key(normalized)

        try:
            payload_raw = jwt.decode(
                normalized,
                signing_key,
                algorithms=["RS256"],
                issuer=self._config.issuer,
                options={
                    "require": ["sub", "exp", "iat", "iss"],
                    "verify_aud": False,
                },
            )
            claims = CognitoAccessClaims.model_validate(payload_raw)
        except ValidationError as exc:
            raise AuthTokenInvalidError(code="AUTH_TOKEN_INVALID_PAYLOAD") from exc
        except jwt.ExpiredSignatureError as exc:
            raise AuthTokenExpiredError() from exc
        except InvalidTokenError as exc:
            raise AuthTokenInvalidError(
                code="AUTH_TOKEN_INVALID_SIGNATURE_OR_CLAIMS"
            ) from exc

        token_use = (claims.token_use or "").strip().lower()
        if token_use and token_use != "access":
            raise AuthTokenInvalidError(code="AUTH_TOKEN_WRONG_USE")
        _validate_client_binding(claims=claims, expected=self._config.audience)

        iat = _to_datetime_or_none(claims.iat)
        exp = _to_datetime_or_none(claims.exp)
        _validate_expiry(expires_at=exp, now=datetime.now(UTC))

        roles = _extract_roles(claims)
        scopes = _extract_scopes(claims)

        return AuthClaims(
            sub=claims.sub.strip(),
            email=(claims.email or "").strip() or None,
            roles=roles,
            scopes=scopes,
            issued_at=iat,
            expires_at=exp,
        )

    def _resolve_signing_key(self, token: str) -> RSAPublicKey:
        try:
            header_raw = jwt.get_unverified_header(token)
            header = TokenHeader.model_validate(header_raw)
        except ValidationError as exc:
            raise AuthTokenInvalidError(code="AUTH_TOKEN_MISSING_KID") from exc
        except InvalidTokenError as exc:
            raise AuthTokenInvalidError(code="AUTH_TOKEN_INVALID_HEADER") from exc

        kid = header.kid.strip()
        if not kid:
            raise AuthTokenInvalidError(code="AUTH_TOKEN_MISSING_KID")

        if self._jwks_client is None:
            raise AuthTokenInvalidError(code="AUTH_JWKS_URI_MISSING")

        try:
            signing_key = self._jwks_client.get_signing_key(kid)
        except PyJWKClientConnectionError as exc:
            logger.warning("jwks_fetch_failed")
            raise AuthTokenInvalidError(code="AUTH_JWKS_FETCH_FAILED") from exc
        except PyJWKClientError as exc:
            code = (
                "AUTH_TOKEN_UNKNOWN_KID"
                if str(exc).startswith("Unable to find a signing key that matches:")
                else "AUTH_JWKS_INVALID_FORMAT"
            )
            raise AuthTokenInvalidError(code=code) from exc
        except (PyJWKError, PyJWKSetError, TypeError, ValueError) as exc:
            raise AuthTokenInvalidError(code="AUTH_JWKS_INVALID_FORMAT") from exc

        if not isinstance(signing_key.key, RSAPublicKey):
            raise AuthTokenInvalidError(code="AUTH_JWKS_INVALID_FORMAT")
        return signing_key.key


def _to_datetime_or_none(value: int | float | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=UTC)


def _validate_expiry(expires_at: datetime | None, now: datetime) -> None:
    if expires_at is not None and expires_at <= now:
        raise AuthTokenExpiredError()


def _extract_roles(claims: CognitoAccessClaims) -> tuple[str, ...]:
    groups: list[str] = []
    for item in claims.cognito_groups:
        normalized = item.strip().lower()
        if normalized:
            groups.append(normalized)
    return tuple(groups)


def _extract_scopes(claims: CognitoAccessClaims) -> tuple[str, ...]:
    scope_raw = claims.scope
    if scope_raw is None or not scope_raw.strip():
        return ()
    return tuple(part.strip() for part in scope_raw.split(" ") if part.strip())


def _validate_client_binding(claims: CognitoAccessClaims, expected: str) -> None:
    expected_normalized = expected.strip()
    if not expected_normalized:
        return

    if isinstance(claims.aud, str) and claims.aud.strip() == expected_normalized:
        return
    if isinstance(claims.aud, list):
        for item in claims.aud:
            if isinstance(item, str) and item.strip() == expected_normalized:
                return

    if (
        isinstance(claims.client_id, str)
        and claims.client_id.strip() == expected_normalized
    ):
        return

    raise AuthTokenInvalidError(code="AUTH_TOKEN_INVALID_AUDIENCE")
