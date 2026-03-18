from typing import Iterator
from sqlalchemy.orm import Session, sessionmaker
from apps.control_plane.src.application.orchestrator.ports import (
    ProcessPendingOnceUnitOfWork,
    OutboxProvisioningSessionPort,
)
from apps.control_plane.src.application.session_create.ports import LabRepository
from apps.control_plane.src.application.session_lifecycle.ports import UnitOfWork
from apps.control_plane.src.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)

from contextlib import contextmanager

from .outbox_provision_session import SQLAlchemyOutboxProvisionSession
from .lab_repository import PostgresLabRepository


class SQLAlchemyProcessPendingOnceUnitOfWork(ProcessPendingOnceUnitOfWork):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._outbox: OutboxProvisioningSessionPort | None = None
        self._lab: LabRepository | None = None
        self._lifecycle_uow: UnitOfWork | None = None

    @property
    def outbox(self) -> OutboxProvisioningSessionPort:
        if self._outbox is None:
            raise RuntimeError("No active outbox")
        return self._outbox

    @property
    def lab(self) -> LabRepository:
        if self._lab is None:
            raise RuntimeError("No active lab repository")
        return self._lab

    @property
    def lifecycle_uow(self) -> UnitOfWork:
        if self._lifecycle_uow is None:
            raise RuntimeError("No active lifecycle unit of work")
        return self._lifecycle_uow

    @contextmanager
    def transaction(self) -> Iterator[None]:
        db_session = self._session_factory()
        self._outbox = SQLAlchemyOutboxProvisionSession(db=db_session)
        self._lab = PostgresLabRepository(db=db_session)
        # TODO(E4 follow-up): this lifecycle UoW uses a separate DB session/
        # transaction from outbox claim/mark writes in this UoW. This is
        # acceptable for E4-T3 baseline wiring, but should be tightened to a
        # shared-session adapter for stronger atomicity.
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
            self._lab = None
            self._lifecycle_uow = None
