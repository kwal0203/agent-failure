from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import pytest
import apps.control_plane.src.application.orchestrator.service as orchestrator_service

from apps.control_plane.src.application.orchestrator.service import process_expiry_once
from apps.control_plane.src.application.orchestrator.types import ExpiryCandidate
from apps.control_plane.src.domain.session_lifecycle.state_machine import Trigger


class _FakeExpiryQueryRepo:
    def __init__(self, sessions: list[ExpiryCandidate]) -> None:
        self._sessions = sessions

    def get_expiry_candidates(self, *, limit: int = 100) -> list[ExpiryCandidate]:
        _ = limit
        return self._sessions


def test_process_expiry_once_provisioning_timeout_transitions_expired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = uuid4()
    now = datetime.now(timezone.utc)
    repo = _FakeExpiryQueryRepo(
        [
            ExpiryCandidate(
                state="PROVISIONING",
                session_id=session_id,
                created_at=now - timedelta(minutes=20),
                started_at=None,
                ended_at=None,
            )
        ]
    )

    calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_expiry_once(
        session_query_repo=repo,
        uow=object(),  # type: ignore[arg-type]
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(calls) == 1
    assert calls[0]["trigger"] == Trigger.PROVISIONING_MAX_TIME
    assert calls[0]["session_id"] == session_id


def test_process_expiry_once_max_lifetime_transitions_expired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = uuid4()
    now = datetime.now(timezone.utc)
    repo = _FakeExpiryQueryRepo(
        [
            ExpiryCandidate(
                state="ACTIVE",
                session_id=session_id,
                created_at=now - timedelta(days=2),
                started_at=now - timedelta(days=2),
                ended_at=None,
            )
        ]
    )

    calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_expiry_once(
        session_query_repo=repo,
        uow=object(),  # type: ignore[arg-type]
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(calls) == 1
    assert calls[0]["trigger"] == Trigger.SESSION_MAX_TIME
    assert calls[0]["session_id"] == session_id


def test_process_expiry_once_non_expired_no_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = uuid4()
    now = datetime.now(timezone.utc)
    repo = _FakeExpiryQueryRepo(
        [
            ExpiryCandidate(
                state="ACTIVE",
                session_id=session_id,
                created_at=now - timedelta(minutes=1),
                started_at=now - timedelta(minutes=1),
                ended_at=None,
            )
        ]
    )

    calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_expiry_once(
        session_query_repo=repo,
        uow=object(),  # type: ignore[arg-type]
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(calls) == 0


def test_process_expiry_once_transition_failure_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    first_id = uuid4()
    second_id = uuid4()
    repo = _FakeExpiryQueryRepo(
        [
            ExpiryCandidate(
                state="PROVISIONING",
                session_id=first_id,
                created_at=now - timedelta(minutes=20),
                started_at=None,
                ended_at=None,
            ),
            ExpiryCandidate(
                state="PROVISIONING",
                session_id=second_id,
                created_at=now - timedelta(minutes=20),
                started_at=None,
                ended_at=None,
            ),
        ]
    )

    calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        calls.append(kwargs)
        if kwargs["session_id"] == first_id:
            raise RuntimeError("simulated transition failure")
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_expiry_once(
        session_query_repo=repo,
        uow=object(),  # type: ignore[arg-type]
    )

    assert result.claimed_count == 2
    assert result.succeeded_count == 1
    assert result.failed_count == 1
    assert len(calls) == 2
