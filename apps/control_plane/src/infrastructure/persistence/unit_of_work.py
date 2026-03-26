from apps.control_plane.src.application.session_lifecycle.ports import (
    UnitOfWork,
    SessionRepository,
    Outbox,
)
from apps.control_plane.src.application.common.ports import IdempotencyStore
from apps.control_plane.src.application.session_lifecycle.schemas import (
    TransitionResult,
)
from apps.control_plane.src.application.trace.ports import TraceEventPort

from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager
from collections.abc import Iterator
from .session_repository import (
    SQLAlchemySessionRepository,
    SQLAlchemyTraceEventRepository,
)
from .idempotency_store import SQLAlchemyTransitionIdempotencyStore
from .outbox import SQLAlchemyOutbox


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._sessions: SessionRepository | None = None
        self._idempotency: IdempotencyStore[TransitionResult] | None = None
        self._outbox: Outbox | None = None
        self._trace: TraceEventPort | None = None

    @property
    def sessions(self) -> SessionRepository:
        if self._sessions is None:
            raise RuntimeError("No active transaction")
        return self._sessions

    @property
    def idempotency(self) -> IdempotencyStore[TransitionResult]:
        if self._idempotency is None:
            raise RuntimeError("No active idempotency store")
        return self._idempotency

    @property
    def outbox(self) -> Outbox:
        if self._outbox is None:
            raise RuntimeError("No active outbox")
        return self._outbox

    @property
    def trace(self) -> TraceEventPort:
        if self._trace is None:
            raise RuntimeError("No active trace event")
        return self._trace

    @contextmanager
    def transaction(self) -> Iterator[None]:
        db_session = self._session_factory()
        self._sessions = SQLAlchemySessionRepository(db=db_session)
        self._idempotency = SQLAlchemyTransitionIdempotencyStore(db=db_session)
        self._outbox = SQLAlchemyOutbox(db=db_session)
        self._trace = SQLAlchemyTraceEventRepository(db=db_session)

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
            self._trace = None
