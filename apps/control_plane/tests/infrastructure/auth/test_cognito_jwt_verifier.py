import io
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from urllib.error import URLError

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from apps.control_plane.src.application.auth.errors import AuthTokenInvalidError
from apps.control_plane.src.infrastructure.auth.cognito_jwt_verifier import (
    CognitoJwtVerifier,
)
from apps.control_plane.src.infrastructure.auth.types import AuthVerifierConfig

ISSUER = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_example"
AUDIENCE = "client-id"
JWKS_URI = f"{ISSUER}/.well-known/jwks.json"


def _config(*, jwks_uri: str = JWKS_URI) -> AuthVerifierConfig:
    return AuthVerifierConfig(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_uri=jwks_uri,
        jwks_cache_ttl_seconds=300,
    )


def _key_pair(kid: str) -> tuple[rsa.RSAPrivateKey, dict[str, object]]:
    private_key = rsa.generate_private_key(public_exponent=65_537, key_size=2_048)
    jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    return private_key, {**jwk, "kid": kid, "alg": "RS256", "use": "sig"}


def _token(private_key: rsa.RSAPrivateKey, kid: str) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": "user-123",
            "email": "learner@example.com",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "iss": ISSUER,
            "client_id": AUDIENCE,
            "token_use": "access",
            "scope": "sessions:read sessions:write",
            "cognito:groups": ["Learner"],
        },
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )


def _stub_jwks_responses(
    monkeypatch: pytest.MonkeyPatch,
    documents: list[object],
) -> Callable[[], int]:
    call_count = 0

    def fake_urlopen(*args: object, **kwargs: object) -> io.BytesIO:
        del args, kwargs
        nonlocal call_count
        index = min(call_count, len(documents) - 1)
        call_count += 1
        return io.BytesIO(json.dumps(documents[index]).encode())

    monkeypatch.setattr("jwt.jwks_client.urllib.request.urlopen", fake_urlopen)
    return lambda: call_count


def test_verifier_uses_cached_jwks_for_repeated_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key, jwk = _key_pair("key-1")
    request_count = _stub_jwks_responses(monkeypatch, [{"keys": [jwk]}])
    verifier = CognitoJwtVerifier(_config())
    token = _token(private_key, "key-1")

    first = verifier.verify_access_token(token)
    second = verifier.verify_access_token(token)

    assert first == second
    assert first.sub == "user-123"
    assert first.roles == ("learner",)
    assert first.scopes == ("sessions:read", "sessions:write")
    assert request_count() == 1


def test_verifier_refreshes_jwks_when_cognito_rotates_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_private_key, old_jwk = _key_pair("old-key")
    new_private_key, new_jwk = _key_pair("new-key")
    request_count = _stub_jwks_responses(
        monkeypatch,
        [
            {"keys": [old_jwk]},
            {"keys": [old_jwk, new_jwk]},
        ],
    )
    verifier = CognitoJwtVerifier(_config())

    verifier.verify_access_token(_token(old_private_key, "old-key"))
    claims = verifier.verify_access_token(_token(new_private_key, "new-key"))

    assert claims.sub == "user-123"
    assert request_count() == 2


def test_verifier_maps_jwks_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key, _ = _key_pair("key-1")

    def fail_urlopen(*args: object, **kwargs: object) -> io.BytesIO:
        del args, kwargs
        raise URLError("unavailable")

    monkeypatch.setattr("jwt.jwks_client.urllib.request.urlopen", fail_urlopen)
    verifier = CognitoJwtVerifier(_config())

    with pytest.raises(AuthTokenInvalidError) as exc_info:
        verifier.verify_access_token(_token(private_key, "key-1"))

    assert exc_info.value.code == "AUTH_JWKS_FETCH_FAILED"


def test_verifier_rejects_unknown_signing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    known_private_key, known_jwk = _key_pair("known-key")
    unknown_private_key, _ = _key_pair("unknown-key")
    del known_private_key
    request_count = _stub_jwks_responses(monkeypatch, [{"keys": [known_jwk]}])
    verifier = CognitoJwtVerifier(_config())

    with pytest.raises(AuthTokenInvalidError) as exc_info:
        verifier.verify_access_token(_token(unknown_private_key, "unknown-key"))

    assert exc_info.value.code == "AUTH_TOKEN_UNKNOWN_KID"
    assert request_count() == 2


def test_verifier_rejects_invalid_jwks_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key, _ = _key_pair("key-1")
    _stub_jwks_responses(monkeypatch, [{"keys": []}])
    verifier = CognitoJwtVerifier(_config())

    with pytest.raises(AuthTokenInvalidError) as exc_info:
        verifier.verify_access_token(_token(private_key, "key-1"))

    assert exc_info.value.code == "AUTH_JWKS_INVALID_FORMAT"


def test_verifier_rejects_non_object_jwks_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key, _ = _key_pair("key-1")
    _stub_jwks_responses(monkeypatch, [["not", "an", "object"]])
    verifier = CognitoJwtVerifier(_config())

    with pytest.raises(AuthTokenInvalidError) as exc_info:
        verifier.verify_access_token(_token(private_key, "key-1"))

    assert exc_info.value.code == "AUTH_JWKS_INVALID_FORMAT"


def test_verifier_reports_missing_jwks_uri() -> None:
    private_key, _ = _key_pair("key-1")
    verifier = CognitoJwtVerifier(_config(jwks_uri=""))

    with pytest.raises(AuthTokenInvalidError) as exc_info:
        verifier.verify_access_token(_token(private_key, "key-1"))

    assert exc_info.value.code == "AUTH_JWKS_URI_MISSING"
