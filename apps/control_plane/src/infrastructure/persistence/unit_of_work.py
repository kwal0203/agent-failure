from apps.control_plane.src.application.session_lifecycle.ports import (
    UnitOfWork,
    SessionRepository,
    IdempotencyStore,
)
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager
from collections.abc import Iterator
from .session_repository import SQLAlchemySessionRepository
from .idempotency_store import PostgresIdempotencyStore


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._sessions: SessionRepository | None = None
        self._idempotency: IdempotencyStore | None = None

    @property
    def sessions(self) -> SessionRepository:
        if self._sessions is None:
            raise RuntimeError("No active transaction")
        return self._sessions

    @property
    def idempotency(self) -> IdempotencyStore:
        if self._idempotency is None:
            raise RuntimeError("No active idempotency store")
        return self._idempotency

    @contextmanager
    def transaction(self) -> Iterator[None]:
        db_session = self._session_factory()
        self._sessions = SQLAlchemySessionRepository(db=db_session)
        self._idempotency = PostgresIdempotencyStore(db=db_session)

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
