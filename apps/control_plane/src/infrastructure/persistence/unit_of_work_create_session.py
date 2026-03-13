from typing import Iterator
from sqlalchemy.orm import Session
from contextlib import contextmanager

from apps.control_plane.src.application.session_create.ports import (
    CreateSessionUnitOfWork,
    OutboxCreateSession,
    CreateSessionRepository,
    LabRepository,
)
from apps.control_plane.src.application.session_create.schemas import (
    CreateSessionResult,
)
from apps.control_plane.src.application.common.ports import IdempotencyStore

from .db import sessionmaker
from .session_repository import PostgresCreateSessionRepository
from .idempotency_store import PostgresCreateSessionIdempotencyStore
from .outbox_create_session import SQLAlchemyOutboxCreateSession
from .lab_repository import PostgresLabRepository


class SQLAlchemyCreateSessionUnitOfWork(CreateSessionUnitOfWork):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._sessions: PostgresCreateSessionRepository | None = None
        self._idempotency: IdempotencyStore[CreateSessionResult] | None = None
        self._outbox: OutboxCreateSession | None = None
        self._lab_repo: LabRepository | None = None

    @property
    def sessions(self) -> CreateSessionRepository:
        if self._sessions is None:
            raise RuntimeError("No active transaction.")
        return self._sessions

    @property
    def idempotency(self) -> IdempotencyStore[CreateSessionResult]:
        if self._idempotency is None:
            raise RuntimeError("No active idempotency store.")
        return self._idempotency

    @property
    def outbox(self) -> OutboxCreateSession:
        if self._outbox is None:
            raise RuntimeError("No active outbox.")
        return self._outbox

    @property
    def lab_repo(self) -> LabRepository:
        if self._lab_repo is None:
            raise RuntimeError("No active lab repository.")
        return self._lab_repo

    @contextmanager
    def transaction(self) -> Iterator[None]:
        db_session = self._session_factory()
        self._sessions = PostgresCreateSessionRepository(db=db_session)
        self._idempotency = PostgresCreateSessionIdempotencyStore(db=db_session)
        self._outbox = SQLAlchemyOutboxCreateSession(db=db_session)
        self._lab_repo = PostgresLabRepository(db=db_session)

        try:
            yield
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()
            self._sessions = None
            self._idempotency = None
            self._outbox = None
            self._lab_repo = None
