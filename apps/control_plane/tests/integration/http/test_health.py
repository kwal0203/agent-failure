from fastapi.testclient import TestClient

from apps.control_plane.src.infrastructure.config.settings import (
    PilotAlertEmailSettings,
)
from apps.control_plane.src.interfaces.http.dependencies import (
    get_pilot_alert_email_settings,
)
from apps.control_plane.src.interfaces.http.main import app


def test_healthz() -> None:
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_pilot_alert_healthz_ready() -> None:
    app.dependency_overrides[get_pilot_alert_email_settings] = lambda: (
        PilotAlertEmailSettings(
            enabled=True,
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username=None,
            smtp_password=None,
            smtp_starttls=True,
            from_email="alerts@example.com",
            to_emails=("ops@example.com",),
        )
    )
    try:
        client = TestClient(app)
        response = client.get("/healthz/pilot-alert")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"enabled": True, "ready": True, "missing": []}


def test_pilot_alert_healthz_not_ready_when_missing_config() -> None:
    app.dependency_overrides[get_pilot_alert_email_settings] = lambda: (
        PilotAlertEmailSettings(
            enabled=True,
            smtp_host="",
            smtp_port=587,
            smtp_username=None,
            smtp_password=None,
            smtp_starttls=True,
            from_email="",
            to_emails=(),
        )
    )
    try:
        client = TestClient(app)
        response = client.get("/healthz/pilot-alert")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "enabled": True,
        "ready": False,
        "missing": [
            "PILOT_ALERT_EMAIL_SMTP_HOST",
            "PILOT_ALERT_EMAIL_FROM",
            "PILOT_ALERT_EMAIL_TO",
        ],
    }
