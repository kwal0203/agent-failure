import logging

import pytest

from apps.control_plane.src.interfaces.runtime import worker_loop


class _StopLoop(Exception):
    pass


def test_sync_worker_loop_logs_failure_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls = 0

    def run_once() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("tick failed")

    def stop_after_retry(_: float) -> None:
        if calls == 2:
            raise _StopLoop

    monkeypatch.setattr(worker_loop.time, "sleep", stop_after_retry)
    with caplog.at_level(logging.ERROR), pytest.raises(_StopLoop):
        worker_loop.run_worker_loop(
            worker_name="test_worker",
            run_once=run_once,
            poll_interval_seconds=0.1,
            logger=logging.getLogger("test.sync.worker"),
        )

    assert calls == 2
    failure = next(record for record in caplog.records if record.exc_info)
    assert getattr(failure, "worker_name") == "test_worker"
    assert getattr(failure, "correlation_id")


@pytest.mark.asyncio
async def test_async_worker_loop_logs_failure_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    calls = 0

    async def run_once() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("tick failed")

    async def stop_after_retry(_: float) -> None:
        if calls == 2:
            raise _StopLoop

    monkeypatch.setattr(worker_loop.asyncio, "sleep", stop_after_retry)
    with caplog.at_level(logging.ERROR), pytest.raises(_StopLoop):
        await worker_loop.run_async_worker_loop(
            worker_name="test_async_worker",
            run_once=run_once,
            poll_interval_seconds=0.1,
            logger=logging.getLogger("test.async.worker"),
        )

    assert calls == 2
    failure = next(record for record in caplog.records if record.exc_info)
    assert getattr(failure, "worker_name") == "test_async_worker"
    assert getattr(failure, "correlation_id")
