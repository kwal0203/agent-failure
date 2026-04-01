import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.control_plane.src.application.runtime.types import RuntimeClientConfig
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    Base,
    SessionModel,
    TraceEventModel,
)
from apps.control_plane.src.infrastructure.runtime.client import RuntimeHttpClient
from apps.control_plane.src.interfaces.http.dependencies import get_runtime_client
from apps.control_plane.src.interfaces.http.main import app


def _override_db_session(db_session: Session):
    def _dependency_override():
        try:
            yield db_session
        finally:
            pass

    return _dependency_override


def _owner_user_id(username: str) -> UUID:
    return uuid5(namespace=NAMESPACE_URL, name=f"local-user:{username}")


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_active_session(db_session: Session, owner_username: str) -> SessionModel:
    session = SessionModel(
        id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        owner_user_id=_owner_user_id(owner_username),
        state=SessionState.ACTIVE.value,
        runtime_substate="WAITING_FOR_INPUT",
        resume_mode="hot_resume",
        last_transition_actor="seed",
        last_transition_reason=None,
    )
    db_session.add(session)
    db_session.flush()
    return session


def _user_prompt_message(session_id: UUID, content: str) -> dict[str, object]:
    return {
        "type": "USER_PROMPT",
        "session_id": str(session_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {"content": content},
    }


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_for_runtime(url: str, timeout_s: float = 8.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            response = httpx.get(f"{url}/healthz", timeout=0.5)
            if response.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.1)
    raise RuntimeError("runtime server did not become ready")


@pytest.mark.integration
@pytest.mark.usefixtures("engine")
def test_session_stream_websocket_uses_runtime_http_client_e2e(
    db_session: Session,
) -> None:
    Base.metadata.create_all(bind=db_session.get_bind())

    runtime_token = "runtime-e2e-token"
    runtime_port = _free_port()
    runtime_base_url = f"http://127.0.0.1:{runtime_port}"

    env = os.environ.copy()
    env["RUNTIME_SHARED_TOKEN"] = runtime_token
    env["MODEL_CLIENT_MODE"] = "fake"
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") or "."

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "runtimes.baseline.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(runtime_port),
            "--log-level",
            "error",
        ],
        cwd="/home/kane/Projects/agent-failure",
        env=env,
    )

    try:
        _wait_for_runtime(runtime_base_url)

        owner_username = "runtime-e2e-owner"
        session = _seed_active_session(db_session, owner_username=owner_username)

        app.dependency_overrides[get_db_session] = _override_db_session(db_session)
        app.dependency_overrides[get_runtime_client] = lambda: RuntimeHttpClient(
            RuntimeClientConfig(
                base_url=runtime_base_url,
                timeout_seconds=5.0,
                auth_token=runtime_token,
            )
        )

        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ) as ws:
            _ = ws.receive_json()  # SESSION_STATUS
            ws.send_json(_user_prompt_message(session.id, "hello from e2e"))

            trace_msg_1 = ws.receive_json()
            trace_msg_2 = ws.receive_json()
            chunk_msg_1 = ws.receive_json()
            chunk_msg_2 = ws.receive_json()

        assert trace_msg_1["type"] == "TRACE_EVENT"
        assert trace_msg_1["payload"]["event_code"] == "TURN_STARTED"

        assert trace_msg_2["type"] == "TRACE_EVENT"
        assert trace_msg_2["payload"]["event_code"] == "MODEL_REQUEST_STARTED"

        assert chunk_msg_1["type"] == "AGENT_TEXT_CHUNK"
        assert chunk_msg_1["payload"]["content"] == "I can help with that. "
        assert chunk_msg_1["payload"]["final"] is False

        assert chunk_msg_2["type"] == "AGENT_TEXT_CHUNK"
        assert chunk_msg_2["payload"]["content"] == "You asked: hello from e2e"
        assert chunk_msg_2["payload"]["final"] is True

        model_events = (
            db_session.execute(
                select(TraceEventModel)
                .where(
                    TraceEventModel.session_id == session.id,
                    TraceEventModel.family == "model",
                )
                .order_by(TraceEventModel.event_index.asc())
            )
            .scalars()
            .all()
        )
        assert [event.event_type for event in model_events] == [
            "MODEL_TURN_STARTED",
            "MODEL_TURN_COMPLETED",
        ]

    finally:
        app.dependency_overrides.clear()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
