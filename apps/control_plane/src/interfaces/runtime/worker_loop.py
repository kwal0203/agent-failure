import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import NoReturn

from apps.control_plane.src.application.common.observability import (
    log_fields,
    reset_correlation_id,
    set_correlation_id,
)


def run_worker_loop(
    *,
    worker_name: str,
    run_once: Callable[[], object],
    poll_interval_seconds: float,
    logger: logging.Logger,
) -> NoReturn:
    """Run an isolated polling tick with fresh correlation context."""
    while True:
        token = set_correlation_id(None)
        try:
            run_once()
        except Exception:
            logger.exception(
                "%s tick failed",
                worker_name.replace("_", " "),
                extra={**log_fields(), "worker_name": worker_name},
            )
        finally:
            reset_correlation_id(token)
        time.sleep(poll_interval_seconds)


async def run_async_worker_loop(
    *,
    worker_name: str,
    run_once: Callable[[], Awaitable[object]],
    poll_interval_seconds: float,
    logger: logging.Logger,
) -> NoReturn:
    """Async equivalent of :func:`run_worker_loop`."""
    while True:
        token = set_correlation_id(None)
        try:
            await run_once()
        except Exception:
            logger.exception(
                "%s tick failed",
                worker_name.replace("_", " "),
                extra={**log_fields(), "worker_name": worker_name},
            )
        finally:
            reset_correlation_id(token)
        await asyncio.sleep(poll_interval_seconds)
