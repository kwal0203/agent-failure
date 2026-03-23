from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from apps.control_plane.src.application.orchestrator.service import process_pending_once
from apps.control_plane.src.application.orchestrator.types import (
    ProvisionResult,
    RuntimeProvisionRequest,
)
from apps.control_plane.src.application.session_create.service import create_session
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.models import (
    OutboxEventModel,
    SessionModel,
    SessionTransitionEventModel,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work_create_session import (
    SQLAlchemyCreateSessionUnitOfWork,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work_outbox_pending import (
    SQLAlchemyProcessPendingOnceUnitOfWork,
)
from apps.control_plane.src.infrastructure.policy.admission import StubAdmissionPolicy


class _ResolverOK:
    def resolve(self, lab_slug: str, lab_version: str) -> str:
        _ = (lab_slug, lab_version)
        return "ghcr.io/test/runtime@sha256:abc123"


class _ProvisionerAccepted:
    def provision(self, request: RuntimeProvisionRequest) -> ProvisionResult:
        _ = request
        return ProvisionResult(status="accepted", runtime_id="runtime-1")


class _ProvisionerFailed:
    def provision(self, request: RuntimeProvisionRequest) -> ProvisionResult:
        _ = request
        return ProvisionResult(
            status="failed",
            reason_code="K8S_APPLY_FAILED",
            details={"stderr": "simulated"},
        )


def _launch_session() -> UUID:
    principal = PrincipalContext(user_id=uuid4(), role="learner")
    lab_id = uuid4()
    key = f"idem-{uuid4()}"
    create_uow = SQLAlchemyCreateSessionUnitOfWork(session_factory=SessionFactory)
    admission = StubAdmissionPolicy()

    created = create_session(
        principal=principal,
        admission_policy=admission,
        lab_id=lab_id,
        idempotency_key=key,
        uow=create_uow,
    )
    return created.session_id


@pytest.mark.usefixtures("engine")
def test_provisioning_worker_success_consumes_outbox_and_transitions_active() -> None:
    session_id = _launch_session()

    with SessionFactory() as db:
        pending = (
            db.execute(
                select(OutboxEventModel).where(
                    OutboxEventModel.aggregate_id == session_id,
                    OutboxEventModel.event_type == "session.provisioning.v1",
                )
            )
            .scalars()
            .all()
        )
        assert len(pending) == 1
        assert pending[0].status == "pending"

    worker_uow = SQLAlchemyProcessPendingOnceUnitOfWork(session_factory=SessionFactory)
    result = process_pending_once(
        uow=worker_uow,
        image_resolver=_ResolverOK(),
        provisioner=_ProvisionerAccepted(),
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0

    with SessionFactory() as db:
        session_row = db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        ).scalar_one()
        assert session_row.state == SessionState.ACTIVE.value

        prov_outbox = db.execute(
            select(OutboxEventModel).where(
                OutboxEventModel.aggregate_id == session_id,
                OutboxEventModel.event_type == "session.provisioning.v1",
            )
        ).scalar_one()
        assert prov_outbox.status == "processed"

        transition = db.execute(
            select(SessionTransitionEventModel)
            .where(SessionTransitionEventModel.session_id == session_id)
            .order_by(SessionTransitionEventModel.created_at.desc())
        ).scalar_one()
        assert transition.next_state == SessionState.ACTIVE.value
        assert transition.trigger == "PROVISIONING_SUCCEEDED"


@pytest.mark.usefixtures("engine")
def test_provisioning_worker_failure_consumes_outbox_and_transitions_failed() -> None:
    session_id = _launch_session()

    worker_uow = SQLAlchemyProcessPendingOnceUnitOfWork(session_factory=SessionFactory)
    result = process_pending_once(
        uow=worker_uow,
        image_resolver=_ResolverOK(),
        provisioner=_ProvisionerFailed(),
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 1

    with SessionFactory() as db:
        session_row = db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        ).scalar_one()
        assert session_row.state == SessionState.FAILED.value

        prov_outbox = db.execute(
            select(OutboxEventModel).where(
                OutboxEventModel.aggregate_id == session_id,
                OutboxEventModel.event_type == "session.provisioning.v1",
            )
        ).scalar_one()
        assert prov_outbox.status == "failed"

        transition = db.execute(
            select(SessionTransitionEventModel)
            .where(SessionTransitionEventModel.session_id == session_id)
            .order_by(SessionTransitionEventModel.created_at.desc())
        ).scalar_one()
        assert transition.next_state == SessionState.FAILED.value
        assert transition.trigger == "PROVISIONING_FAILED"
