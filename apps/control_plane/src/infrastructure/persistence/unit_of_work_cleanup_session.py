from typing import Iterator
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager

from apps.control_plane.src.application.orchestrator.ports import (
    OutboxCleanupSessionPort,
    ProcessCleanupOnceUnitOfWork,
)
from apps.control_plane.src.application.session_lifecycle.ports import UnitOfWork

from .outbox_cleanup_session import SQLAlchemyCleanupSession
from .unit_of_work import SQLAlchemyUnitOfWork


class SQLAlchemyUnitOfWorkCleanupSession(ProcessCleanupOnceUnitOfWork):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._outbox: SQLAlchemyCleanupSession | None = None
        self._lifecycle_uow: UnitOfWork | None = None

    @property
    def outbox(self) -> OutboxCleanupSessionPort:
        if self._outbox is None:
            raise RuntimeError("No active outbox")
        return self._outbox

    @property
    def lifecycle_uow(self) -> UnitOfWork:
        if self._lifecycle_uow is None:
            raise RuntimeError("No active lifecycle unit of work")
        return self._lifecycle_uow

    @contextmanager
    def transaction(self) -> Iterator[None]:
        db_session = self._session_factory()
        self._outbox = SQLAlchemyCleanupSession(db=db_session)
        # Caveat: lifecycle_uow uses a separate SQLAlchemy session/transaction from
        # this cleanup outbox claim/mark transaction, so cross-write atomicity is
        # not guaranteed in this baseline implementation.
        self._lifecycle_uow = SQLAlchemyUnitOfWork(
            session_factory=self._session_factory
        )

        try:
            yield
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()
            self._outbox = None
            self._lifecycle_uow = None
