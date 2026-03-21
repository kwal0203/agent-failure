from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from apps.control_plane.src.application.orchestrator.service import (
    process_reconciliation_once,
)
from apps.control_plane.src.application.orchestrator.types import (
    RuntimeInspectorRequest,
    RuntimeInspectorResult,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.models import (
    OutboxEventModel,
    SessionModel,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyReconciliationSessionRepository,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


class _InspectorMissingRuntime:
    def inspect(self, request: RuntimeInspectorRequest) -> RuntimeInspectorResult:
        return RuntimeInspectorResult(
            session_id=request.session_id,
            requested_runtime_id=request.runtime_id,
            matched_runtime_ids=tuple(),
            exists=False,
            duplicate_count=0,
            phase=None,
            ready=None,
            reason="NotFound",
        )


@pytest.mark.usefixtures("engine")
def test_reconciliation_worker_missing_runtime_transitions_failed() -> None:
    session_id = uuid4()

    with SessionFactory() as db:
        db.add(
            SessionModel(
                id=session_id,
                owner_user_id=uuid4(),
                state=SessionState.ACTIVE.value,
                runtime_id="runtime-integ-reconcile-1",
                last_transition_actor="seed",
                last_transition_reason=None,
            )
        )
        db.commit()

    lifecycle_uow = SQLAlchemyUnitOfWork(session_factory=SessionFactory)
    inspector = _InspectorMissingRuntime()

    with SessionFactory() as db:
        session_query_repo = SQLAlchemyReconciliationSessionRepository(db=db)
        result = process_reconciliation_once(
            session_query_repo=session_query_repo,
            uow=lifecycle_uow,
            inspector=inspector,
        )

    assert result.claimed_count >= 1
    assert result.failed_count == 0

    with SessionFactory() as db:
        session_row = db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        ).scalar_one()
        assert session_row.state == SessionState.FAILED.value

        cleanup_outbox = (
            db.execute(
                select(OutboxEventModel).where(
                    OutboxEventModel.aggregate_id == session_id,
                    OutboxEventModel.event_type == "session.cleanup.requested.v1",
                )
            )
            .scalars()
            .all()
        )
        assert len(cleanup_outbox) >= 1
