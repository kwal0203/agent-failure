from pytest import MonkeyPatch
from typing import Literal

from apps.evaluator.src.application.types import EvaluatorOnceResult
from apps.evaluator.src.interfaces.runtime import evaluator_worker


class _FakeSessionFactory:
    class _FakeDBSession:
        def __init__(self) -> None:
            self.committed = False
            self.rolled_back = False

        def commit(self) -> None:
            self.committed = True

        def rollback(self) -> None:
            self.rolled_back = True

    last_db: "_FakeSessionFactory._FakeDBSession | None" = None

    def __enter__(self) -> object:
        db = self._FakeDBSession()
        _FakeSessionFactory.last_db = db
        return db

    def __exit__(self, exc_type: object, exc: object, tb: object) -> Literal[False]:
        _ = (exc_type, exc, tb)
        return False


def test_run_once_invokes_service_and_commits(monkeypatch: MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    class _FakeRepo:
        def __init__(self, db: object) -> None:
            calls["repo_db"] = db

    class _FakeLookupRepo:
        def __init__(self, db: object) -> None:
            calls["lookup_db"] = db

    class _FakeOutboxRepo:
        def __init__(self, db: object) -> None:
            calls["outbox_db"] = db

    def _fake_process_once(
        *, repo: object, lab_lookup_repo: object, outbox_repo: object
    ) -> EvaluatorOnceResult:
        calls["repo"] = repo
        calls["lab_lookup_repo"] = lab_lookup_repo
        calls["outbox_repo"] = outbox_repo
        return EvaluatorOnceResult(
            claimed_count=1,
            succeeded_count=1,
            failed_count=0,
            retried_count=0,
        )

    monkeypatch.setattr(evaluator_worker, "SessionFactory", _FakeSessionFactory)
    monkeypatch.setattr(evaluator_worker, "SQLAlchemyEvaluatorRepository", _FakeRepo)
    monkeypatch.setattr(
        evaluator_worker, "SQLAlchemyEvaluatorLabLookupRepository", _FakeLookupRepo
    )
    monkeypatch.setattr(
        evaluator_worker, "SQLAlchemyOutboxEvaluatorRepository", _FakeOutboxRepo
    )
    monkeypatch.setattr(
        evaluator_worker, "process_evaluate_pending_once", _fake_process_once
    )

    evaluator_worker.run_once()

    assert calls["repo"].__class__ is _FakeRepo
    assert calls["lab_lookup_repo"].__class__ is _FakeLookupRepo
    assert calls["outbox_repo"].__class__ is _FakeOutboxRepo
    assert _FakeSessionFactory.last_db is not None
    assert _FakeSessionFactory.last_db.committed is True
    assert _FakeSessionFactory.last_db.rolled_back is False


def test_run_once_rolls_back_and_reraises_on_service_error(
    monkeypatch: MonkeyPatch,
) -> None:
    class _FakeRepo:
        def __init__(self, db: object) -> None:
            _ = db

    class _FakeLookupRepo:
        def __init__(self, db: object) -> None:
            _ = db

    class _FakeOutboxRepo:
        def __init__(self, db: object) -> None:
            _ = db

    def _fake_process_once(
        *, repo: object, lab_lookup_repo: object, outbox_repo: object
    ) -> EvaluatorOnceResult:
        _ = (repo, lab_lookup_repo, outbox_repo)
        raise RuntimeError("boom")

    monkeypatch.setattr(evaluator_worker, "SessionFactory", _FakeSessionFactory)
    monkeypatch.setattr(evaluator_worker, "SQLAlchemyEvaluatorRepository", _FakeRepo)
    monkeypatch.setattr(
        evaluator_worker, "SQLAlchemyEvaluatorLabLookupRepository", _FakeLookupRepo
    )
    monkeypatch.setattr(
        evaluator_worker, "SQLAlchemyOutboxEvaluatorRepository", _FakeOutboxRepo
    )
    monkeypatch.setattr(
        evaluator_worker, "process_evaluate_pending_once", _fake_process_once
    )

    try:
        evaluator_worker.run_once()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert str(exc) == "boom"

    assert _FakeSessionFactory.last_db is not None
    assert _FakeSessionFactory.last_db.committed is False
    assert _FakeSessionFactory.last_db.rolled_back is True
