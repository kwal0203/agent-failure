from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from apps.control_plane.src.application.orchestrator.service import (
    process_cleanup_pending_once,
)
from apps.control_plane.src.application.orchestrator.types import (
    RuntimeTeardownRequest,
    RuntimeTeardownResult,
)
from apps.control_plane.src.application.session_lifecycle.service import (
    transition_session,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.models import (
    OutboxEventModel,
    SessionModel,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work_cleanup_session import (
    SQLAlchemyUnitOfWorkCleanupSession,
)


class _TeardownDeleted:
    def teardown(self, request: RuntimeTeardownRequest) -> RuntimeTeardownResult:
        _ = request
        return RuntimeTeardownResult(status="deleted")


@pytest.mark.usefixtures("engine")
def test_cleanup_worker_consumes_cleanup_outbox_after_terminal_transition() -> None:
    session_id = uuid4()
    runtime_id = "runtime-integ-1"

    # Seed an ACTIVE session so ADMIN_CANCELLED is a legal terminal transition.
    with SessionFactory() as db:
        db.add(
            SessionModel(
                id=session_id,
                owner_user_id=uuid4(),
                state=SessionState.ACTIVE.value,
                runtime_id=runtime_id,
                last_transition_actor="seed",
                last_transition_reason=None,
            )
        )
        db.commit()

    transition_session(
        session_id=session_id,
        trigger=Trigger.ADMIN_CANCELLED,
        actor="admin",
        metadata={"source": "integration-cleanup-test"},
        idempotency_key=f"cleanup-transition-{uuid4()}",
        uow=SQLAlchemyUnitOfWork(session_factory=SessionFactory),
    )

    with SessionFactory() as db:
        cleanup_outbox = db.execute(
            select(OutboxEventModel).where(
                OutboxEventModel.aggregate_id == session_id,
                OutboxEventModel.event_type == "session.cleanup.requested.v1",
            )
        ).scalar_one()
        assert cleanup_outbox.status == "pending"
        payload = cleanup_outbox.payload
        assert payload["session_id"] == str(session_id)
        assert payload["runtime_id"] == runtime_id

    cleanup_uow = SQLAlchemyUnitOfWorkCleanupSession(session_factory=SessionFactory)
    result = process_cleanup_pending_once(
        uow=cleanup_uow,
        teardown=_TeardownDeleted(),
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert result.retried_count == 0

    with SessionFactory() as db:
        cleanup_outbox = db.execute(
            select(OutboxEventModel).where(
                OutboxEventModel.aggregate_id == session_id,
                OutboxEventModel.event_type == "session.cleanup.requested.v1",
            )
        ).scalar_one()
        assert cleanup_outbox.status == "processed"
        assert cleanup_outbox.processed_at is not None
