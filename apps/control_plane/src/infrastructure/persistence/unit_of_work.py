from apps.control_plane.src.application.session_lifecycle.ports import (
    UnitOfWork,
    SessionRepository,
)
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager
from collections.abc import Iterator
from .session_repository import SQLAlchemySessionRepository


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._sessions: SessionRepository | None = None

    @property
    def sessions(self) -> SessionRepository:
        if self._sessions is None:
            raise RuntimeError("No active transaction")
        return self._sessions

    @contextmanager
    def transaction(self) -> Iterator[None]:
        db_session = self._session_factory()
        self._sessions = SQLAlchemySessionRepository(db=db_session)

        try:
            yield
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()
            self._sessions = None
