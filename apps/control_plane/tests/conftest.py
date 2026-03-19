from collections.abc import Generator
from urllib.parse import urlparse

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

load_dotenv()


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


os.environ["DATABASE_URL"] = _get_test_database_url()


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
