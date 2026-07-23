from collections.abc import Generator
from urllib.parse import urlparse
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from apps.control_plane.src.infrastructure.persistence.models import Base
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionRepository,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)

import os
import pytest

from dotenv import load_dotenv
from apps.control_plane.src.application.auth.errors import AuthTokenInvalidError
from apps.control_plane.src.application.auth.types import AuthClaims

load_dotenv()
os.environ.setdefault("APP_ENV", "dev")


def _get_test_database_url() -> str:
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "TEST_DATABASE_URL must be set for tests. "
            "Refusing to use DATABASE_URL to avoid wiping dev DB."
        )

    parsed = urlparse(db_url)
    db_name = parsed.path.lstrip("/").lower()
    if "test" not in db_name:
        raise RuntimeError(
            f"Refusing to run tests against non-test database '{db_name}'. "
            "Set TEST_DATABASE_URL to a dedicated test DB."
        )

    return db_url


if os.getenv("TEST_DATABASE_URL"):
    # Some integration-test modules build session factories during collection,
    # before fixtures run. Force those factories onto the validated test
    # database and never allow the developer DATABASE_URL as a fallback.
    os.environ["DATABASE_URL"] = _get_test_database_url()
else:
    # Keep later load_dotenv() calls from restoring a developer/production URL.
    # Unit tests must not connect; this intentionally unreachable test URL
    # makes an accidental connection fail locally and immediately.
    os.environ["DATABASE_URL"] = (
        "postgresql+psycopg://invalid:invalid@127.0.0.1:1/agent_failure_test"
    )


class _LocalTestTokenVerifier:
    """Test-only verifier that preserves legacy local:<username>[:role] tokens."""

    def verify_access_token(self, token: str) -> AuthClaims:
        if not token.startswith("local:"):
            raise AuthTokenInvalidError()

        payload = token.removeprefix("local:").strip()
        if not payload:
            raise AuthTokenInvalidError()

        parts = [part.strip() for part in payload.split(":") if part.strip()]
        if not parts:
            raise AuthTokenInvalidError()

        username = parts[0]
        role = parts[1] if len(parts) > 1 else "learner"
        email = username if "@" in username else f"{username}@gatech.edu"

        return AuthClaims(
            sub=f"local-user:{username}",
            email=email,
            roles=(role,),
            scopes=(),
            issued_at=datetime.now(timezone.utc),
            expires_at=None,
        )


@pytest.fixture(autouse=True)
def _install_test_token_verifier(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    if request.node.get_closest_marker("integration") is not None:
        monkeypatch.setenv("DATABASE_URL", _get_test_database_url())

    from apps.control_plane.src.interfaces.http.main import app

    previous = getattr(app.state, "token_verifier", None)
    app.state.token_verifier = _LocalTestTokenVerifier()
    try:
        yield
    finally:
        if previous is None:
            try:
                delattr(app.state, "token_verifier")
            except AttributeError:
                pass
        else:
            app.state.token_verifier = previous


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    db_url = _get_test_database_url()
    engine = create_engine(url=db_url, future=True)

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, future=True)

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def repo(db_session: Session) -> SQLAlchemySessionRepository:
    return SQLAlchemySessionRepository(db=db_session)


@pytest.fixture
def uow() -> SQLAlchemyUnitOfWork:
    db_url = _get_test_database_url()
    return SQLAlchemyUnitOfWork(
        session_factory=sessionmaker(
            bind=create_engine(db_url, future=True),
            class_=Session,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    )
