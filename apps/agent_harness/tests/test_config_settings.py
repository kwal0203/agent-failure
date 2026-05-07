import pytest

from apps.agent_harness.src.infrastructure.config.settings import get_model_client_mode


def test_get_model_client_mode_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_CLIENT_MODE", "gateway")
    assert get_model_client_mode() == "gateway"


def test_get_model_client_mode_fake(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_CLIENT_MODE", "fake")
    assert get_model_client_mode() == "fake"


def test_get_model_client_mode_invalid_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_CLIENT_MODE", "gateways")
    with pytest.raises(ValueError, match="Invalid MODEL_CLIENT_MODE"):
        get_model_client_mode()
