from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from apps.control_plane.src.application.orchestrator.service import process_expiry_once
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.models import (
    SessionModel,
    SessionTransitionEventModel,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyExpirySessionRepository,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)


@pytest.mark.usefixtures("engine")
def test_expiry_worker_provisioning_timeout_transitions_expired() -> None:
    session_id = uuid4()

    with SessionFactory() as db:
        db.add(
            SessionModel(
                id=session_id,
                owner_user_id=uuid4(),
                state=SessionState.PROVISIONING.value,
                created_at=datetime.now(timezone.utc) - timedelta(minutes=20),
                started_at=None,
                last_transition_actor="seed",
                last_transition_reason=None,
            )
        )
        db.commit()

    lifecycle_uow = SQLAlchemyUnitOfWork(session_factory=SessionFactory)

    with SessionFactory() as db:
        session_query_repo = SQLAlchemyExpirySessionRepository(db=db)
        result = process_expiry_once(
            session_query_repo=session_query_repo,
            uow=lifecycle_uow,
        )

    assert result.claimed_count >= 1
    assert result.failed_count == 0

    with SessionFactory() as db:
        session_row = db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        ).scalar_one()
        assert session_row.state == SessionState.EXPIRED.value

        transition = db.execute(
            select(SessionTransitionEventModel)
            .where(SessionTransitionEventModel.session_id == session_id)
            .order_by(SessionTransitionEventModel.created_at.desc())
        ).scalar_one()
        assert transition.created_at is not None
        assert transition.next_state == SessionState.EXPIRED.value
        assert transition.trigger == "PROVISIONING_MAX_TIME"
