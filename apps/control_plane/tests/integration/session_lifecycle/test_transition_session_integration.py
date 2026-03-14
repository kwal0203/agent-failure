from uuid import uuid4

from sqlalchemy import func, select

from apps.control_plane.src.application.session_lifecycle.service import (
    transition_session,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.models import (
    IdempotencyRecordModel,
    OutboxEventModel,
    SessionModel,
    SessionTransitionEventModel,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)

import pytest


@pytest.mark.usefixtures("engine")
def test_transition_session_replay_is_idempotent() -> None:
    session_id = uuid4()
    idempotency_key = str(uuid4())

    # Seed a CREATED session row.
    with SessionFactory() as seed_db:
        seed_db.add(
            SessionModel(
                id=session_id,
                state=SessionState.CREATED.value,
                last_transition_actor="seed",
                last_transition_reason=None,
            )
        )
        seed_db.commit()

    uow = SQLAlchemyUnitOfWork(session_factory=SessionFactory)

    first = transition_session(
        session_id=session_id,
        trigger=Trigger.LAUNCH_SUCCEEDED,
        actor="system",
        metadata={"reason_code": "launch_succeeded"},
        idempotency_key=idempotency_key,
        uow=uow,
    )
    second = transition_session(
        session_id=session_id,
        trigger=Trigger.LAUNCH_SUCCEEDED,
        actor="system",
        metadata={"reason_code": "launch_succeeded"},
        idempotency_key=idempotency_key,
        uow=uow,
    )

    assert second == first

    with SessionFactory() as verify_db:
        persisted_session = verify_db.get(SessionModel, session_id)
        assert persisted_session is not None
        assert persisted_session.state == SessionState.PROVISIONING.value

        transition_count = verify_db.execute(
            select(func.count())
            .select_from(SessionTransitionEventModel)
            .where(SessionTransitionEventModel.session_id == session_id)
        ).scalar_one()
        assert transition_count == 1

        outbox_count = verify_db.execute(
            select(func.count())
            .select_from(OutboxEventModel)
            .where(OutboxEventModel.aggregate_id == session_id)
        ).scalar_one()
        assert outbox_count == 1

        idempotency_count = verify_db.execute(
            select(func.count())
            .select_from(IdempotencyRecordModel)
            .where(
                IdempotencyRecordModel.operation == "transition_session",
                IdempotencyRecordModel.idempotency_key == idempotency_key,
            )
        ).scalar_one()
        assert idempotency_count == 1
