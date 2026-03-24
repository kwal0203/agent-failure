#!/usr/bin/env python3
"""End-to-end smoke test for session create -> provision -> websocket response."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import websockets

# Ensure project root is importable when running as a standalone script.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


DEFAULT_LAB_ID = UUID("11111111-1111-1111-1111-111111111111")
DEFAULT_AUTH_TOKEN = "local:kane:learner"
DEFAULT_BASE_URL = "http://localhost:8000"


def _require_session_id(payload: object) -> UUID:
    if not isinstance(payload, dict):
        raise RuntimeError("session create response was not an object")
    session_obj = payload.get("session")
    if not isinstance(session_obj, dict):
        raise RuntimeError("session create response missing 'session' object")
    session_id_raw = session_obj.get("id")
    if not isinstance(session_id_raw, str):
        raise RuntimeError("session create response missing session.id")
    return UUID(session_id_raw)


def _create_session(*, base_url: str, auth_token: str, lab_id: UUID) -> UUID:
    idempotency_key = f"smoke-session-{uuid4()}"
    payload = {"lab_id": str(lab_id)}
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Idempotency-Key": idempotency_key,
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=20.0) as client:
        response = client.post(
            f"{base_url}/api/v1/sessions", headers=headers, json=payload
        )

    if response.status_code != 202:
        raise RuntimeError(
            f"session create failed status={response.status_code} body={response.text}"
        )

    return _require_session_id(response.json())


def _run_provisioning_tick() -> None:
    from apps.control_plane.src.application.orchestrator.service import (
        process_pending_once,
    )
    from apps.control_plane.src.infrastructure.orchestrator.k8s_provisioner import (
        K8sRuntimeProvisioner,
    )
    from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
    from apps.control_plane.src.infrastructure.persistence.unit_of_work_outbox_pending import (
        SQLAlchemyProcessPendingOnceUnitOfWork,
    )
    from apps.control_plane.src.infrastructure.runtime.image_resolver import (
        RuntimeImageResolver,
    )

    uow = SQLAlchemyProcessPendingOnceUnitOfWork(session_factory=SessionFactory)
    resolver = RuntimeImageResolver(
        lock_file=Path("deploy/k8s/staging/runtime-image.lock"),
        selection_file=Path("deploy/k8s/staging/runtime-image-selection.yaml"),
    )
    provisioner = K8sRuntimeProvisioner()
    result = process_pending_once(
        uow=uow, image_resolver=resolver, provisioner=provisioner
    )
    print(
        "provisioning_tick",
        f"claimed={result.claimed_count}",
        f"succeeded={result.succeeded_count}",
        f"failed={result.failed_count}",
        f"retried={result.retried_count}",
    )


def _kubectl(args: list[str], *, timeout_seconds: int = 20) -> str:
    completed = subprocess.run(
        ["kubectl", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return completed.stdout.strip()


def _wait_for_pod_running(
    *, namespace: str, pod_name: str, timeout_seconds: int, poll_seconds: float
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_phase = "<unknown>"

    while time.monotonic() < deadline:
        try:
            phase = _kubectl(
                [
                    "-n",
                    namespace,
                    "get",
                    "pod",
                    pod_name,
                    "-o",
                    "jsonpath={.status.phase}",
                ]
            )
        except subprocess.CalledProcessError:
            time.sleep(poll_seconds)
            continue

        last_phase = phase
        if phase == "Running":
            return
        if phase in {"Failed", "Succeeded"}:
            raise RuntimeError(f"pod reached terminal phase before running: {phase}")
        time.sleep(poll_seconds)

    raise RuntimeError(
        f"timed out waiting for pod to be Running pod={pod_name} last_phase={last_phase}"
    )


def _check_runtime_health(*, namespace: str, pod_name: str) -> str:
    # Avoid requiring curl in the runtime image; use Python stdlib request.
    return _kubectl(
        [
            "-n",
            namespace,
            "exec",
            pod_name,
            "--",
            "python",
            "-c",
            (
                "import urllib.request; "
                "print(urllib.request.urlopen('http://127.0.0.1:8000/healthz').read().decode())"
            ),
        ]
    )


async def _run_websocket_turn(
    *,
    base_url: str,
    auth_token: str,
    session_id: UUID,
    prompt: str,
    timeout_seconds: int,
) -> tuple[str, float]:
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/api/v1/sessions/{session_id}/stream"

    send_ts = 0.0
    first_chunk_delta = -1.0
    chunks: list[str] = []

    async with websockets.connect(
        ws_url,
        additional_headers={"Authorization": f"Bearer {auth_token}"},
        open_timeout=10,
    ) as ws:
        # Initial session status.
        initial_raw = await asyncio.wait_for(ws.recv(), timeout=10)
        initial = json.loads(initial_raw)
        if initial.get("type") != "SESSION_STATUS":
            raise RuntimeError(f"expected SESSION_STATUS, got: {initial}")

        user_prompt = {
            "type": "USER_PROMPT",
            "session_id": str(session_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"content": prompt},
        }

        send_ts = time.monotonic()
        await ws.send(json.dumps(user_prompt))

        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout_seconds)
            message = json.loads(raw)
            msg_type = message.get("type")

            if msg_type == "AGENT_TEXT_CHUNK":
                payload = message.get("payload", {})
                content = payload.get("content")
                final = payload.get("final")
                if isinstance(content, str):
                    chunks.append(content)
                    if first_chunk_delta < 0:
                        first_chunk_delta = time.monotonic() - send_ts
                if final is True:
                    return ("".join(chunks), first_chunk_delta)
                continue

            if msg_type == "POLICY_DENIAL":
                raise RuntimeError(f"policy denial: {message}")

            if msg_type == "SYSTEM_ERROR":
                raise RuntimeError(f"system error: {message}")

            # Ignore TRACE_EVENT and any other non-terminal message types.
            continue

    raise RuntimeError("timed out waiting for final AGENT_TEXT_CHUNK")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test: create session -> provision pod -> websocket prompt/response."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--auth-token", default=DEFAULT_AUTH_TOKEN)
    parser.add_argument("--lab-id", default=str(DEFAULT_LAB_ID))
    parser.add_argument("--namespace", default="runtime-pool")
    parser.add_argument(
        "--prompt",
        default="Give me one short sentence describing prompt injection.",
    )
    parser.add_argument("--pod-timeout-seconds", type=int, default=120)
    parser.add_argument("--ws-timeout-seconds", type=int, default=60)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()

    try:
        lab_id = UUID(args.lab_id)
        print(f"creating_session lab_id={lab_id}")
        session_id = _create_session(
            base_url=args.base_url,
            auth_token=args.auth_token,
            lab_id=lab_id,
        )
        print(f"session_created session_id={session_id}")

        _run_provisioning_tick()

        pod_name = f"session-{str(session_id)[:8]}"
        print(f"waiting_for_pod pod_name={pod_name}")
        _wait_for_pod_running(
            namespace=args.namespace,
            pod_name=pod_name,
            timeout_seconds=args.pod_timeout_seconds,
            poll_seconds=args.poll_seconds,
        )
        print(f"pod_running pod_name={pod_name}")

        health = _check_runtime_health(namespace=args.namespace, pod_name=pod_name)
        print(f"runtime_health response={health}")

        response_text, first_chunk_seconds = asyncio.run(
            _run_websocket_turn(
                base_url=args.base_url,
                auth_token=args.auth_token,
                session_id=session_id,
                prompt=args.prompt,
                timeout_seconds=args.ws_timeout_seconds,
            )
        )
        print(
            "websocket_ok",
            f"first_chunk_seconds={first_chunk_seconds:.3f}",
            f"response_preview={response_text[:160]!r}",
        )
        return 0
    except Exception as exc:
        print(f"smoke_failed error={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
