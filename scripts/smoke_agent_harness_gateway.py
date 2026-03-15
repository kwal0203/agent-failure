#!/usr/bin/env python3
"""Manual smoke test for Agent Harness gateway mode."""

from apps.agent_harness.src.application.session_loop.types import HarnessTurnInput
from apps.agent_harness.src.interfaces.runtime.local_loop import run_local_one_turn

import argparse
import os
import sys
from pathlib import Path
from uuid import UUID, uuid4

# Ensure project root is importable when running as a standalone script.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_LAB_ID = UUID("11111111-1111-1111-1111-111111111111")
DEFAULT_LAB_VERSION_ID = UUID("22222222-2222-2222-2222-222222222222")


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one Agent Harness turn against configured gateway provider."
    )
    parser.add_argument(
        "--prompt",
        default="Give me a 1-sentence explanation of prompt injection.",
        help="Learner prompt for smoke test.",
    )
    parser.add_argument(
        "--lab-id",
        default=str(DEFAULT_LAB_ID),
        help="Lab ID (must match supported local V1 context builder).",
    )
    parser.add_argument(
        "--lab-version-id",
        default=str(DEFAULT_LAB_VERSION_ID),
        help="Lab version ID (must match supported local V1 context builder).",
    )
    args = parser.parse_args()

    # Required config for gateway mode.
    _require_env("PROVIDER_ENDPOINT")
    _require_env("OPENROUTER_API_KEY")
    _require_env("MODEL_NAME")
    os.environ["MODEL_CLIENT_MODE"] = "gateway"

    turn = HarnessTurnInput(
        session_id=uuid4(),
        lab_id=UUID(args.lab_id),
        lab_version_id=UUID(args.lab_version_id),
        prompt=args.prompt,
    )

    result = run_local_one_turn(turn)
    joined = "".join(chunk.content for chunk in result.chunks)

    print("failure:", result.failure)
    print("chunk_count:", len(result.chunks))
    print("preview:", joined[:300])

    return 0 if result.failure is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
