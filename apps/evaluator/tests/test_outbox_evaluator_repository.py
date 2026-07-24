from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import uuid4

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from apps.control_plane.src.infrastructure.persistence.models import (
    Base,
    OutboxEventModel,
)
from apps.evaluator.src.infrastructure.outbox_evaluator_repository import (
    SQLAlchemyOutboxEvaluatorRepository,
)

pytestmark = pytest.mark.integration


def _get_test_database_url() -> str:
    db_url = os.getenv("TEST_DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "TEST_DATABASE_URL must be set for evaluator integration tests."
        )

    parsed = urlparse(db_url)
    db_name = parsed.path.lstrip("/").lower()
    if "test" not in db_name:
        raise RuntimeError(
            f"Refusing to run tests against non-test database '{db_name}'."
        )
    return db_url


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    engine = create_engine(_get_test_database_url(), future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_claim_pending_evaluate_accepts_canonical_payload(
    engine: Engine,
) -> None:
    session_id = uuid4()
    with Session(bind=engine, future=True) as db:
        db.add(
            OutboxEventModel(
                event_type="session.evaluate.requested.v1",
                aggregate_id=session_id,
                payload={
                    "lab_id": str(uuid4()),
                    "lab_version_id": str(uuid4()),
                    "evaluator_version": 1,
                    "start_event_index": 10,
                    "end_event_index": 10,
                },
                status="pending",
                available_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            )
        )
        db.commit()

        repo = SQLAlchemyOutboxEvaluatorRepository(db=db)
        claimed = repo.claim_pending_evaluate(limit=10)

    assert len(claimed) == 1
    assert claimed[0].task.session_id == session_id


def test_claim_pending_evaluate_rejects_obsolete_difficulty_field(
    engine: Engine,
) -> None:
    with Session(bind=engine, future=True) as db:
        db.add(
            OutboxEventModel(
                event_type="session.evaluate.requested.v1",
                aggregate_id=uuid4(),
                payload={
                    "lab_id": str(uuid4()),
                    "lab_version_id": str(uuid4()),
                    "lab_difficulty": "easy",
                    "evaluator_version": 1,
                    "start_event_index": 11,
                    "end_event_index": 11,
                },
                status="pending",
                available_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            )
        )
        db.commit()

        repo = SQLAlchemyOutboxEvaluatorRepository(db=db)
        claimed = repo.claim_pending_evaluate(limit=10)

    assert claimed == []
