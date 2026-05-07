import pytest

from apps.control_plane.src.infrastructure.config.settings import get_database_url


def test_get_database_url_requires_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL environment variable not set"):
        get_database_url()


def test_get_database_url_allows_localhost_outside_k8s(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:localdev@localhost:5432/agent_failure",
    )
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
    assert get_database_url().endswith("/agent_failure")


def test_get_database_url_rejects_localhost_in_k8s(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:localdev@localhost:5432/agent_failure",
    )
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.43.0.1")
    with pytest.raises(ValueError, match="Invalid DATABASE_URL for Kubernetes runtime"):
        get_database_url()


def test_get_database_url_accepts_cluster_service_in_k8s(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:localdev@postgres.runtime-pool.svc.cluster.local:5432/agent_failure",
    )
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.43.0.1")
    assert get_database_url().startswith("postgresql+psycopg://")
