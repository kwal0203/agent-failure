from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.session_report_evidence.errors import (
    ForbiddenErrorSessionReportEvidence,
    InvalidSessionReportEvidenceError,
    SessionNotFoundErrorSessionReportEvidence,
)
from apps.control_plane.src.application.session_report_evidence.service import (
    get_session_report_evidence,
    import_selected_evidence,
    project_report_evidence,
    replace_session_report_evidence,
)
from apps.control_plane.src.application.session_report_evidence.types import (
    SessionReportEvidenceItemInput,
    SessionReportEvidenceRow,
)
from apps.control_plane.src.application.trace.types import TraceEvent


class _FakeReportEvidenceRepo:
    def __init__(
        self,
        *,
        owner_user_id: UUID | None,
        rows: list[SessionReportEvidenceRow] | None = None,
    ) -> None:
        self._owner_user_id = owner_user_id
        self._rows = rows or []
        self.last_replace_call: dict[str, object] | None = None

    def get_session_owner_user_id(self, *, session_id: UUID) -> UUID | None:
        _ = session_id
        return self._owner_user_id

    def list_report_evidence_for_session(
        self, *, session_id: UUID
    ) -> list[SessionReportEvidenceRow]:
        _ = session_id
        return list(self._rows)

    def replace_report_evidence_for_session(
        self,
        *,
        session_id: UUID,
        items: list[SessionReportEvidenceItemInput],
    ) -> None:
        self.last_replace_call = {"session_id": session_id, "items": list(items)}


class _FakeTraceRepo:
    def __init__(self, events: tuple[TraceEvent, ...]) -> None:
        self._events = events

    def append_trace_event(self, trace: TraceEvent) -> None:
        _ = trace

    def list_trace_events_for_session(self, session_id: UUID) -> tuple[TraceEvent, ...]:
        _ = session_id
        return self._events

    def get_next_event_index(self, session_id: UUID) -> int:
        _ = session_id
        return 0


def _trace_event(
    *, session_id: UUID, event_id: UUID, event_type: str, event_index: int = 1
) -> TraceEvent:
    return TraceEvent(
        event_id=event_id,
        session_id=session_id,
        family="learner",
        event_type=event_type,
        occurred_at=datetime(2026, 5, 17, 20, 0, 0, tzinfo=timezone.utc),
        source="runtime",
        event_index=event_index,
        payload={},
    )


def _item(*, event_id: UUID, position: int) -> SessionReportEvidenceItemInput:
    return SessionReportEvidenceItemInput(
        event_id=event_id,
        position=position,
        title="Evidence title",
        description="Evidence description",
        details=None,
        occurred_at=datetime(2026, 5, 17, 20, 0, 0, tzinfo=timezone.utc),
        trace_version=1,
        event_index=position,
        evidence_type="exploit_step",
        objective_keys=("lab1.token_disclosed",),
        why_it_matters="Useful exploit evidence",
        default_priority="high",
        student_note=None,
    )


def test_get_session_report_evidence_owner_allowed() -> None:
    session_id = uuid4()
    owner_user_id = uuid4()
    row = SessionReportEvidenceRow(
        id=uuid4(),
        session_id=session_id,
        event_id=uuid4(),
        position=0,
        title="Title",
        description=None,
        details=None,
        occurred_at=datetime(2026, 5, 17, 20, 0, 0, tzinfo=timezone.utc),
        trace_version=1,
        event_index=3,
        evidence_type="exploit_outcome",
        objective_keys=("lab1.token_disclosed",),
        why_it_matters=None,
        default_priority="high",
        student_note=None,
        created_at=datetime(2026, 5, 17, 20, 1, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 17, 20, 1, 0, tzinfo=timezone.utc),
    )
    repo = _FakeReportEvidenceRepo(owner_user_id=owner_user_id, rows=[row])

    result = get_session_report_evidence(
        session_id=session_id,
        principal=PrincipalContext(user_id=owner_user_id, role="learner"),
        repo=repo,
    )

    assert result == (row,)


def test_get_session_report_evidence_raises_forbidden_for_non_owner_non_admin() -> None:
    repo = _FakeReportEvidenceRepo(owner_user_id=uuid4())
    with pytest.raises(ForbiddenErrorSessionReportEvidence):
        get_session_report_evidence(
            session_id=uuid4(),
            principal=PrincipalContext(user_id=uuid4(), role="learner"),
            repo=repo,
        )


def test_get_session_report_evidence_raises_not_found_when_session_missing() -> None:
    repo = _FakeReportEvidenceRepo(owner_user_id=None)
    with pytest.raises(SessionNotFoundErrorSessionReportEvidence):
        get_session_report_evidence(
            session_id=uuid4(),
            principal=PrincipalContext(user_id=uuid4(), role="admin"),
            repo=repo,
        )


def test_replace_session_report_evidence_rejects_duplicate_event_ids() -> None:
    session_id = uuid4()
    owner_user_id = uuid4()
    shared_event_id = uuid4()
    repo = _FakeReportEvidenceRepo(owner_user_id=owner_user_id)
    trace_repo = _FakeTraceRepo(
        (
            _trace_event(
                session_id=session_id,
                event_id=shared_event_id,
                event_type="TOKEN_DISCLOSED",
            ),
        )
    )

    with pytest.raises(InvalidSessionReportEvidenceError):
        replace_session_report_evidence(
            session_id=session_id,
            principal=PrincipalContext(user_id=owner_user_id, role="learner"),
            items=(
                _item(event_id=shared_event_id, position=0),
                _item(event_id=shared_event_id, position=1),
            ),
            repo=repo,
            trace_repo=trace_repo,
        )


def test_replace_session_report_evidence_rejects_event_not_in_session_trace() -> None:
    session_id = uuid4()
    owner_user_id = uuid4()
    trace_event_id = uuid4()
    payload_event_id = uuid4()
    repo = _FakeReportEvidenceRepo(owner_user_id=owner_user_id)
    trace_repo = _FakeTraceRepo(
        (
            _trace_event(
                session_id=session_id,
                event_id=trace_event_id,
                event_type="TOKEN_DISCLOSED",
            ),
        )
    )

    with pytest.raises(InvalidSessionReportEvidenceError):
        replace_session_report_evidence(
            session_id=session_id,
            principal=PrincipalContext(user_id=owner_user_id, role="learner"),
            items=(_item(event_id=payload_event_id, position=0),),
            repo=repo,
            trace_repo=trace_repo,
        )


def test_replace_session_report_evidence_rejects_non_selectable_trace_event() -> None:
    session_id = uuid4()
    owner_user_id = uuid4()
    event_id = uuid4()
    repo = _FakeReportEvidenceRepo(owner_user_id=owner_user_id)
    trace_repo = _FakeTraceRepo(
        (
            _trace_event(
                session_id=session_id, event_id=event_id, event_type="SESSION_CREATED"
            ),
        )
    )

    with pytest.raises(InvalidSessionReportEvidenceError):
        replace_session_report_evidence(
            session_id=session_id,
            principal=PrincipalContext(user_id=owner_user_id, role="learner"),
            items=(_item(event_id=event_id, position=7),),
            repo=repo,
            trace_repo=trace_repo,
        )


def test_replace_session_report_evidence_normalizes_positions_from_request_order() -> (
    None
):
    session_id = uuid4()
    owner_user_id = uuid4()
    first_event_id = uuid4()
    second_event_id = uuid4()
    repo = _FakeReportEvidenceRepo(owner_user_id=owner_user_id)
    trace_repo = _FakeTraceRepo(
        (
            _trace_event(
                session_id=session_id,
                event_id=first_event_id,
                event_type="TOKEN_DISCLOSED",
            ),
            _trace_event(
                session_id=session_id,
                event_id=second_event_id,
                event_type="ATTACK_EMAIL_SENT",
                event_index=2,
            ),
        )
    )

    normalized = replace_session_report_evidence(
        session_id=session_id,
        principal=PrincipalContext(user_id=owner_user_id, role="learner"),
        items=(
            _item(event_id=first_event_id, position=99),
            _item(event_id=second_event_id, position=42),
        ),
        repo=repo,
        trace_repo=trace_repo,
    )

    assert [item.position for item in normalized] == [0, 1]
    assert repo.last_replace_call is not None
    saved_items = repo.last_replace_call["items"]
    assert isinstance(saved_items, list)
    assert [item.position for item in saved_items] == [0, 1]
    assert saved_items[0].trace_version == 1
    assert [item.event_index for item in saved_items] == [1, 2]


def test_import_selected_evidence_defaults_to_persisted_order() -> None:
    session_id = uuid4()
    owner_user_id = uuid4()
    row_a = SessionReportEvidenceRow(
        id=uuid4(),
        session_id=session_id,
        event_id=uuid4(),
        position=0,
        title="A",
        description=None,
        details=None,
        occurred_at=datetime(2026, 5, 17, 20, 0, 0, tzinfo=timezone.utc),
        trace_version=1,
        event_index=1,
        evidence_type="exploit_step",
        objective_keys=(),
        why_it_matters=None,
        default_priority="low",
        student_note=None,
        created_at=datetime(2026, 5, 17, 20, 1, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 17, 20, 1, 0, tzinfo=timezone.utc),
    )
    row_b = SessionReportEvidenceRow(
        id=uuid4(),
        session_id=session_id,
        event_id=uuid4(),
        position=1,
        title="B",
        description=None,
        details=None,
        occurred_at=datetime(2026, 5, 17, 20, 0, 1, tzinfo=timezone.utc),
        trace_version=1,
        event_index=2,
        evidence_type="exploit_step",
        objective_keys=(),
        why_it_matters=None,
        default_priority="low",
        student_note=None,
        created_at=datetime(2026, 5, 17, 20, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 17, 20, 1, 1, tzinfo=timezone.utc),
    )
    repo = _FakeReportEvidenceRepo(owner_user_id=owner_user_id, rows=[row_a, row_b])

    result = import_selected_evidence(
        session_id=session_id,
        principal=PrincipalContext(user_id=owner_user_id, role="learner"),
        repo=repo,
        event_ids_override=None,
    )

    assert [row.event_id for row in result] == [row_a.event_id, row_b.event_id]


def test_import_selected_evidence_supports_subset_and_order_override() -> None:
    session_id = uuid4()
    owner_user_id = uuid4()
    row_a = SessionReportEvidenceRow(
        id=uuid4(),
        session_id=session_id,
        event_id=uuid4(),
        position=0,
        title="A",
        description=None,
        details=None,
        occurred_at=datetime(2026, 5, 17, 20, 0, 0, tzinfo=timezone.utc),
        trace_version=1,
        event_index=1,
        evidence_type="exploit_step",
        objective_keys=(),
        why_it_matters=None,
        default_priority="low",
        student_note=None,
        created_at=datetime(2026, 5, 17, 20, 1, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 17, 20, 1, 0, tzinfo=timezone.utc),
    )
    row_b = SessionReportEvidenceRow(
        id=uuid4(),
        session_id=session_id,
        event_id=uuid4(),
        position=1,
        title="B",
        description=None,
        details=None,
        occurred_at=datetime(2026, 5, 17, 20, 0, 1, tzinfo=timezone.utc),
        trace_version=1,
        event_index=2,
        evidence_type="exploit_step",
        objective_keys=(),
        why_it_matters=None,
        default_priority="low",
        student_note=None,
        created_at=datetime(2026, 5, 17, 20, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 17, 20, 1, 1, tzinfo=timezone.utc),
    )
    repo = _FakeReportEvidenceRepo(owner_user_id=owner_user_id, rows=[row_a, row_b])

    result = import_selected_evidence(
        session_id=session_id,
        principal=PrincipalContext(user_id=owner_user_id, role="learner"),
        repo=repo,
        event_ids_override=(row_b.event_id,),
    )

    assert [row.event_id for row in result] == [row_b.event_id]


def test_project_report_evidence_adds_mapping_and_strength_rules() -> None:
    session_id = uuid4()
    row = SessionReportEvidenceRow(
        id=uuid4(),
        session_id=session_id,
        event_id=uuid4(),
        position=0,
        title="Token disclosed",
        description=None,
        details=None,
        occurred_at=datetime(2026, 5, 17, 20, 0, 0, tzinfo=timezone.utc),
        trace_version=1,
        event_index=4,
        evidence_type="exploit_outcome",
        objective_keys=("lab1.token_disclosed",),
        why_it_matters=None,
        default_priority="medium",
        student_note=None,
        created_at=datetime(2026, 5, 17, 20, 1, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 17, 20, 1, 0, tzinfo=timezone.utc),
    )

    projected = project_report_evidence((row,))
    assert projected[0].citation_label == "E1"
    assert projected[0].evidence_strength == "high"
    assert projected[0].objective_mapping[0].rubric_target == (
        "sensitive_data_exposure_outcome"
    )


def test_project_report_evidence_preserves_stored_snapshot_content() -> None:
    row = SessionReportEvidenceRow(
        id=uuid4(),
        session_id=uuid4(),
        event_id=uuid4(),
        position=5,
        title="Stored title from selection time",
        description="Stored description from selection time",
        details={"raw_message": "stored payload snapshot"},
        occurred_at=datetime(2026, 5, 17, 20, 0, 0, tzinfo=timezone.utc),
        trace_version=2,
        event_index=77,
        evidence_type="system_context",
        objective_keys=("lab1.unknown_objective",),
        why_it_matters="stored rationale",
        default_priority="high",
        student_note="stored note",
        created_at=datetime(2026, 5, 17, 20, 1, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 17, 20, 1, 0, tzinfo=timezone.utc),
    )

    projected = project_report_evidence((row,))
    first = projected[0]
    assert first.title == "Stored title from selection time"
    assert first.description == "Stored description from selection time"
    assert first.details == {"raw_message": "stored payload snapshot"}
    assert first.citation_label == "E6"
