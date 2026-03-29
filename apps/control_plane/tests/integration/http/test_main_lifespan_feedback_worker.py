import asyncio

import apps.control_plane.src.interfaces.http.main as main_module


def test_main_lifespan_starts_and_cancels_learner_feedback_worker(
    monkeypatch,
) -> None:
    started = False
    cancelled = False

    async def _fake_run_forever(
        *, session_manager, polling_interval_seconds: float = 1.0
    ) -> None:
        nonlocal started, cancelled
        _ = (session_manager, polling_interval_seconds)
        started = True
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            cancelled = True
            raise

    monkeypatch.setattr(main_module, "run_forever", _fake_run_forever)

    async def _run() -> None:
        async with main_module.app.router.lifespan_context(main_module.app):
            await asyncio.sleep(0)
            assert started is True
            task = main_module.app.state.learner_feedback_task
            assert task is not None
            assert task.done() is False

        assert cancelled is True
        assert main_module.app.state.learner_feedback_task.cancelled() is True

    asyncio.run(_run())
