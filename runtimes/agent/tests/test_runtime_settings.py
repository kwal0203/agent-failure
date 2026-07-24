from uuid import uuid4

import pytest
from pydantic import ValidationError

from runtimes.agent.config.settings import get_runtime_settings


def test_runtime_settings_parse_assigned_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = uuid4()
    monkeypatch.setenv("RUNTIME_SESSION_ID", str(session_id))

    settings = get_runtime_settings()

    assert settings.runtime_session_id == session_id


def test_runtime_settings_reject_invalid_assigned_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RUNTIME_SESSION_ID", "not-a-uuid")

    with pytest.raises(ValidationError, match="runtime_session_id"):
        get_runtime_settings()
