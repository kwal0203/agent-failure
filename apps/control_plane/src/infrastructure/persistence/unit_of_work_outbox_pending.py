from typing import Iterator
from sqlalchemy.orm import Session, sessionmaker
from apps.control_plane.src.application.orchestrator.ports import (
    ProcessPendingOnceUnitOfWork,
    OutboxProvisioningSessionPort,
    SessionRuntimeBindingPort,
)
from apps.control_plane.src.application.session_create.ports import LabRepository
from apps.control_plane.src.application.session_lifecycle.ports import UnitOfWork
from apps.control_plane.src.application.trace.ports import TraceEventPort
from apps.control_plane.src.application.session_objectives.ports import (
    LabObjectiveTemplateReaderPort,
    SessionObjectiveWriterPort,
)
from apps.control_plane.src.application.session_hints.ports import (
    LabHintTemplateReaderPort,
    SessionHintWriterPort,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)

from contextlib import contextmanager

from .outbox_provision_session import SQLAlchemyOutboxProvisionSession
from .lab_repository import SQLAlchemyLabRepository
from .session_repository import (
    SQLAlchemySessionRuntimeBindingRepository,
    SQLAlchemyTraceEventRepository,
)
from .session_objectives_repository import (
    SQLAlchemyLabObjectiveTemplateRepository,
    SQLAlchemySessionObjectiveWriterRepository,
)
from .session_hints_repository import (
    SQLAlchemyLabHintTemplateRepository,
    SQLAlchemySessionHintWriterRepository,
)


class SQLAlchemyProcessPendingOnceUnitOfWork(ProcessPendingOnceUnitOfWork):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._outbox: OutboxProvisioningSessionPort | None = None
        self._lab: LabRepository | None = None
        self._lifecycle_uow: UnitOfWork | None = None
        self._trace: TraceEventPort | None = None
        self._runtime_binding: SessionRuntimeBindingPort | None = None
        self._objective_templates: LabObjectiveTemplateReaderPort | None = None
        self._session_objectives: SessionObjectiveWriterPort | None = None
        self._hint_templates: LabHintTemplateReaderPort | None = None
        self._session_hints: SessionHintWriterPort | None = None

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

    @property
    def trace(self) -> TraceEventPort:
        if self._trace is None:
            raise RuntimeError("No active trace repository")
        return self._trace

    @property
    def runtime_binding(self) -> SessionRuntimeBindingPort:
        if self._runtime_binding is None:
            raise RuntimeError("No active runtime binding")
        return self._runtime_binding

    @property
    def session_objectives(self) -> SessionObjectiveWriterPort:
        if self._session_objectives is None:
            raise RuntimeError("No active session objectives")
        return self._session_objectives

    @property
    def objective_templates(self) -> LabObjectiveTemplateReaderPort:
        if self._objective_templates is None:
            raise RuntimeError("No active objective templates")
        return self._objective_templates

    @property
    def hint_templates(self) -> LabHintTemplateReaderPort:
        if self._hint_templates is None:
            raise RuntimeError("No active hint templates")
        return self._hint_templates

    @property
    def session_hints(self) -> SessionHintWriterPort:
        if self._session_hints is None:
            raise RuntimeError("No active session hints")
        return self._session_hints

    @contextmanager
    def transaction(self) -> Iterator[None]:
        db_session = self._session_factory()
        self._outbox = SQLAlchemyOutboxProvisionSession(db=db_session)
        self._lab = SQLAlchemyLabRepository(db=db_session)
        # Lifecycle transitions own their transaction because they may be
        # retried independently. The claimed outbox row remains locked in this
        # transaction until the worker records the final delivery outcome.
        self._lifecycle_uow = SQLAlchemyUnitOfWork(
            session_factory=self._session_factory
        )
        self._trace = SQLAlchemyTraceEventRepository(db=db_session)
        self._runtime_binding = SQLAlchemySessionRuntimeBindingRepository(db=db_session)
        self._session_objectives = SQLAlchemySessionObjectiveWriterRepository(
            db=db_session
        )
        self._objective_templates = SQLAlchemyLabObjectiveTemplateRepository(
            db=db_session
        )
        self._session_hints = SQLAlchemySessionHintWriterRepository(db=db_session)
        self._hint_templates = SQLAlchemyLabHintTemplateRepository(db=db_session)

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
            self._trace = None
            self._runtime_binding = None
            self._session_objectives = None
            self._objective_templates = None
            self._session_hints = None
            self._hint_templates = None
