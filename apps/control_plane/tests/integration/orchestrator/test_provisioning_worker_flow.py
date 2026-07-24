from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from apps.control_plane.src.application.orchestrator.service import process_pending_once
from apps.control_plane.src.application.orchestrator.types import (
    ProvisionResult,
    RuntimeInspectorRequest,
    RuntimeInspectorResult,
    RuntimeProvisionRequest,
)
from apps.control_plane.src.application.session_create.service import create_session
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.models import (
    LabHintTemplateModel,
    LabModel,
    LabVersionModel,
    OutboxEventModel,
    SessionModel,
    SessionHintModel,
    SessionTransitionEventModel,
    TraceEventModel,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work_create_session import (
    SQLAlchemyCreateSessionUnitOfWork,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work_outbox_pending import (
    SQLAlchemyProcessPendingOnceUnitOfWork,
)
from apps.control_plane.src.infrastructure.policy.admission_policy import (
    StubAdmissionPolicy,
)

AGENT_LAB_2_ID = UUID("55555555-5555-5555-5555-555555555555")
AGENT_LAB_2_VERSION_ID = UUID("55555555-5555-5555-5555-aaaaaaaaaaa2")


class _ResolverOK:
    def resolve(self, lab_slug: str, lab_version: str) -> str:
        _ = (lab_slug, lab_version)
        return "ghcr.io/test/runtime@sha256:abc123"


class _ResolverCapture:
    last: tuple[str, str] | None = None

    def resolve(self, lab_slug: str, lab_version: str) -> str:
        self.last = (lab_slug, lab_version)
        return "ghcr.io/test/runtime@sha256:abc123"


class _ProvisionerAccepted:
    last_request: RuntimeProvisionRequest | None = None

    def provision(self, request: RuntimeProvisionRequest) -> ProvisionResult:
        self.last_request = request
        return ProvisionResult(
            status="accepted",
            runtime_id="runtime-1",
            details={"base_url": "http://runtime.test.local:8000"},
        )


class _ProvisionerFailed:
    def provision(self, request: RuntimeProvisionRequest) -> ProvisionResult:
        _ = request
        return ProvisionResult(
            status="failed",
            reason_code="K8S_APPLY_FAILED",
            details={"stderr": "simulated"},
        )


class _InspectorReady:
    def inspect(self, request: RuntimeInspectorRequest) -> RuntimeInspectorResult:
        return RuntimeInspectorResult(
            session_id=request.session_id,
            requested_runtime_id=request.runtime_id,
            matched_runtime_ids=(request.runtime_id or "runtime-1",),
            exists=True,
            duplicate_count=0,
            phase="Running",
            ready=True,
            reason=None,
            details=None,
        )


def _launch_session() -> UUID:
    principal = PrincipalContext(user_id=uuid4(), role="learner")
    lab_id = uuid4()
    with SessionFactory() as db:
        lab_version_id = uuid4()
        db.add(
            LabModel(
                id=lab_id,
                slug=f"lab-{str(lab_id)[:8]}",
                name="Test Lab",
                summary="test",
                is_active=True,
                is_published=True,
            )
        )
        db.add(
            LabVersionModel(
                id=lab_version_id,
                lab_id=lab_id,
                version="v1",
                is_active=True,
            )
        )
        db.commit()

        db.add_all(
            [
                LabHintTemplateModel(
                    id=uuid4(),
                    lab_version_id=lab_version_id,
                    hint_key="hint_1",
                    text="Ask what tools are available.",
                    offset_seconds=90,
                    sort_order=0,
                    is_active=True,
                ),
                LabHintTemplateModel(
                    id=uuid4(),
                    lab_version_id=lab_version_id,
                    hint_key="hint_2",
                    text="Check if email instructions are trusted.",
                    offset_seconds=210,
                    sort_order=1,
                    is_active=True,
                ),
            ]
        )
        db.commit()
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


def _launch_agent_lab2_seeded_session() -> UUID:
    principal = PrincipalContext(user_id=uuid4(), role="learner")
    with SessionFactory() as db:
        existing_lab = db.execute(
            select(LabModel).where(LabModel.id == AGENT_LAB_2_ID)
        ).scalar_one_or_none()
        if existing_lab is None:
            db.add(
                LabModel(
                    id=AGENT_LAB_2_ID,
                    slug="agent-tool-misuse",
                    name="Agent Tool Misuse",
                    summary="Agent runtime Lab 2",
                    is_active=True,
                    is_published=True,
                )
            )

        existing_version = db.execute(
            select(LabVersionModel).where(LabVersionModel.id == AGENT_LAB_2_VERSION_ID)
        ).scalar_one_or_none()
        if existing_version is None:
            db.add(
                LabVersionModel(
                    id=AGENT_LAB_2_VERSION_ID,
                    lab_id=AGENT_LAB_2_ID,
                    version="v1",
                    is_active=True,
                )
            )
        db.commit()

        existing_template_count = (
            db.execute(
                select(LabHintTemplateModel).where(
                    LabHintTemplateModel.lab_version_id == AGENT_LAB_2_VERSION_ID
                )
            )
            .scalars()
            .all()
        )
        if not existing_template_count:
            db.add_all(
                [
                    LabHintTemplateModel(
                        id=uuid4(),
                        lab_version_id=AGENT_LAB_2_VERSION_ID,
                        hint_key="hint_1",
                        text="Hint 1: TBD",
                        offset_seconds=90,
                        sort_order=0,
                        is_active=True,
                    ),
                    LabHintTemplateModel(
                        id=uuid4(),
                        lab_version_id=AGENT_LAB_2_VERSION_ID,
                        hint_key="hint_2",
                        text="Hint 2: TBD",
                        offset_seconds=210,
                        sort_order=1,
                        is_active=True,
                    ),
                    LabHintTemplateModel(
                        id=uuid4(),
                        lab_version_id=AGENT_LAB_2_VERSION_ID,
                        hint_key="hint_3",
                        text="Hint 3: TBD",
                        offset_seconds=360,
                        sort_order=2,
                        is_active=True,
                    ),
                    LabHintTemplateModel(
                        id=uuid4(),
                        lab_version_id=AGENT_LAB_2_VERSION_ID,
                        hint_key="hint_4",
                        text="Hint 4: TBD",
                        offset_seconds=540,
                        sort_order=3,
                        is_active=True,
                    ),
                ]
            )
        db.commit()

    key = f"idem-{uuid4()}"
    create_uow = SQLAlchemyCreateSessionUnitOfWork(session_factory=SessionFactory)
    admission = StubAdmissionPolicy()
    created = create_session(
        principal=principal,
        admission_policy=admission,
        lab_id=AGENT_LAB_2_ID,
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
    provisioner = _ProvisionerAccepted()
    result = process_pending_once(
        uow=worker_uow,
        image_resolver=_ResolverOK(),
        provisioner=provisioner,
        runtime_inspector=_InspectorReady(),
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert provisioner.last_request is not None

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

        runtime_trace_events = (
            db.execute(
                select(TraceEventModel)
                .where(
                    TraceEventModel.session_id == session_id,
                    TraceEventModel.family == "runtime",
                )
                .order_by(TraceEventModel.event_index.asc())
            )
            .scalars()
            .all()
        )
        assert [event.event_type for event in runtime_trace_events] == [
            "RUNTIME_PROVISION_REQUESTED",
            "RUNTIME_PROVISION_ACCEPTED",
        ]

        session_hints = (
            db.execute(
                select(SessionHintModel)
                .where(SessionHintModel.session_id == session_id)
                .order_by(SessionHintModel.sort_order.asc())
            )
            .scalars()
            .all()
        )
        assert len(session_hints) == 2
        assert [hint.hint_key for hint in session_hints] == ["hint_1", "hint_2"]
        assert [hint.status for hint in session_hints] == ["pending", "pending"]
        assert session_hints[0].unlock_at < session_hints[1].unlock_at


@pytest.mark.usefixtures("engine")
def test_provisioning_worker_agent_lab2_uses_seeded_hint_templates_in_order() -> None:
    session_id = _launch_agent_lab2_seeded_session()

    worker_uow = SQLAlchemyProcessPendingOnceUnitOfWork(session_factory=SessionFactory)
    result = process_pending_once(
        uow=worker_uow,
        image_resolver=_ResolverOK(),
        provisioner=_ProvisionerAccepted(),
        runtime_inspector=_InspectorReady(),
    )
    assert result.succeeded_count == 1

    with SessionFactory() as db:
        session_row = db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        ).scalar_one()
        assert session_row.lab_id == AGENT_LAB_2_ID
        assert session_row.lab_version_id == AGENT_LAB_2_VERSION_ID

        session_hints = (
            db.execute(
                select(SessionHintModel)
                .where(SessionHintModel.session_id == session_id)
                .order_by(SessionHintModel.sort_order.asc())
            )
            .scalars()
            .all()
        )
        assert [hint.hint_key for hint in session_hints] == [
            "hint_1",
            "hint_2",
            "hint_3",
            "hint_4",
        ]
        assert [hint.status for hint in session_hints] == [
            "pending",
            "pending",
            "pending",
            "pending",
        ]

        base_unlock_at = session_hints[0].unlock_at
        offsets_from_first = [
            int((hint.unlock_at - base_unlock_at).total_seconds())
            for hint in session_hints
        ]
        assert offsets_from_first == [0, 120, 270, 450]


@pytest.mark.usefixtures("engine")
def test_provisioning_worker_failure_consumes_outbox_and_transitions_failed() -> None:
    session_id = _launch_session()

    worker_uow = SQLAlchemyProcessPendingOnceUnitOfWork(session_factory=SessionFactory)
    result = process_pending_once(
        uow=worker_uow,
        image_resolver=_ResolverOK(),
        provisioner=_ProvisionerFailed(),
        runtime_inspector=_InspectorReady(),
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

        runtime_trace_events = (
            db.execute(
                select(TraceEventModel)
                .where(
                    TraceEventModel.session_id == session_id,
                    TraceEventModel.family == "runtime",
                )
                .order_by(TraceEventModel.event_index.asc())
            )
            .scalars()
            .all()
        )
        assert [event.event_type for event in runtime_trace_events] == [
            "RUNTIME_PROVISION_REQUESTED",
            "RUNTIME_PROVISION_FAILED",
        ]
        failed_event = runtime_trace_events[-1]
        assert failed_event.payload["reason_code"] == "K8S_APPLY_FAILED"


@pytest.mark.usefixtures("engine")
def test_provisioning_worker_lab3_resolves_memory_poisoning_runtime_binding() -> None:
    principal = PrincipalContext(user_id=uuid4(), role="learner")
    lab_id = UUID("33333333-3333-3333-3333-333333333333")
    lab_version_id = UUID("33333333-3333-3333-3333-aaaaaaaaaaa3")

    with SessionFactory() as db:
        db.add(
            LabModel(
                id=lab_id,
                slug="memory-poisoning",
                name="Memory Poisoning",
                summary="test",
                is_active=True,
                is_published=True,
            )
        )
        db.add(
            LabVersionModel(
                id=lab_version_id,
                lab_id=lab_id,
                version="v1",
                is_active=True,
            )
        )
        db.commit()

    created = create_session(
        principal=principal,
        admission_policy=StubAdmissionPolicy(),
        lab_id=lab_id,
        idempotency_key=f"idem-{uuid4()}",
        uow=SQLAlchemyCreateSessionUnitOfWork(session_factory=SessionFactory),
    )
    session_id = created.session_id

    resolver = _ResolverCapture()
    provisioner = _ProvisionerAccepted()
    worker_uow = SQLAlchemyProcessPendingOnceUnitOfWork(session_factory=SessionFactory)
    result = process_pending_once(
        uow=worker_uow,
        image_resolver=resolver,
        provisioner=provisioner,
        runtime_inspector=_InspectorReady(),
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert resolver.last == ("memory-poisoning", "v1")
    assert provisioner.last_request is not None
    assert provisioner.last_request.session_id == session_id
