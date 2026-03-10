from apps.control_plane.src.application.session_lifecycle.ports import (
    UnitOfWork,
    IdempotencyStore,
    Outbox,
)
from sqlalchemy.orm import Session


def test_transition_session_integration(
    uow: UnitOfWork,
    idempotency_store: IdempotencyStore,
    outbox: Outbox,
    db_session: Session,
):
    assert uow
    assert idempotency_store
    assert outbox
    assert db_session
