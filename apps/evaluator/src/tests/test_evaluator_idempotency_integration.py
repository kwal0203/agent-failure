from __future__ import annotations

from datetime import datetime, timezone
from collections.abc import Generator
from urllib.parse import urlparse
from uuid import uuid4

import os
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from apps.control_plane.src.infrastructure.persistence.models import (
    Base,
    EvaluatorResultModel,
    SessionModel,
    TraceEventModel,
)
from apps.evaluator.src.application.service import evaluate_trace_window_once
from apps.evaluator.src.application.types import EvaluatorTaskInput
from apps.evaluator.src.infrastructure.evaluator_repository import (
    SQLAlchemyEvaluatorRepository,
)


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


def test_repeated_evaluation_of_same_input_does_not_duplicate_results(
    engine: Engine,
) -> None:
    session_id = uuid4()
    owner_user_id = uuid4()
    lab_id = uuid4()
    lab_version_id = uuid4()
    occurred_at = datetime.now(timezone.utc)

    with Session(bind=engine, future=True) as db:
        db.add(
            SessionModel(
                id=session_id,
                lab_id=lab_id,
                lab_version_id=lab_version_id,
                owner_user_id=owner_user_id,
                state="ACTIVE",
                last_transition_actor="learner",
                last_transition_reason=None,
            )
        )
        db.add_all(
            [
                TraceEventModel(
                    event_id=uuid4(),
                    session_id=session_id,
                    family="runtime",
                    event_type="RUNTIME_PROVISION_FAILED",
                    occurred_at=occurred_at,
                    source="test",
                    event_index=0,
                    payload={"reason_code": "K8S_APPLY_FAILED"},
                    trace_version=1,
                    lab_id=lab_id,
                    lab_version_id=lab_version_id,
                ),
                TraceEventModel(
                    event_id=uuid4(),
                    session_id=session_id,
                    family="model",
                    event_type="MODEL_TURN_FAILED",
                    occurred_at=occurred_at,
                    source="test",
                    event_index=1,
                    payload={"provider": "openrouter", "error_code": "TIMEOUT"},
                    trace_version=1,
                    lab_id=lab_id,
                    lab_version_id=lab_version_id,
                ),
            ]
        )
        db.commit()

    task = EvaluatorTaskInput(
        session_id=session_id,
        lab_id=lab_id,
        lab_version_id=lab_version_id,
        evaluator_version=1,
        start_event_index=0,
        end_event_index=1,
    )

    with Session(bind=engine, future=True) as db:
        repo = SQLAlchemyEvaluatorRepository(db=db)

        first = evaluate_trace_window_once(task=task, repo=repo)
        db.commit()
        second = evaluate_trace_window_once(task=task, repo=repo)
        db.commit()

        rows = (
            db.execute(
                select(EvaluatorResultModel).where(
                    EvaluatorResultModel.session_id == session_id
                )
            )
            .scalars()
            .all()
        )

    assert first.findings_count == 2
    assert second.findings_count == 2
    assert len(rows) == 2
