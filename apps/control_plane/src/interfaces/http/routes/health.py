from fastapi import APIRouter, Depends

from apps.control_plane.src.infrastructure.config.settings import (
    PilotAlertEmailSettings,
    PilotProvisioningEmailSettings,
)
from apps.control_plane.src.interfaces.http.dependencies import (
    get_pilot_alert_email_settings,
    get_pilot_provisioning_email_settings,
)

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/healthz/pilot-alert")
def pilot_alert_healthz(
    settings: PilotAlertEmailSettings = Depends(get_pilot_alert_email_settings),
) -> dict[str, object]:
    missing: list[str] = []
    if not settings.smtp_host:
        missing.append("PILOT_ALERT_EMAIL_SMTP_HOST")
    if not settings.from_email:
        missing.append("PILOT_ALERT_EMAIL_FROM")
    if not settings.to_emails:
        missing.append("PILOT_ALERT_EMAIL_TO")

    ready = bool(settings.enabled and not missing)
    return {
        "enabled": settings.enabled,
        "ready": ready,
        "missing": missing,
    }


@router.get("/healthz/pilot-provisioning-email")
def pilot_provisioning_email_healthz(
    settings: PilotProvisioningEmailSettings = Depends(
        get_pilot_provisioning_email_settings
    ),
) -> dict[str, object]:
    missing: list[str] = []
    if not settings.smtp_host:
        missing.append("PILOT_PROVISIONING_EMAIL_SMTP_HOST")
    if not settings.from_email:
        missing.append("PILOT_PROVISIONING_EMAIL_FROM")
    if not settings.admin_to_emails:
        missing.append("PILOT_PROVISIONING_EMAIL_ADMIN_TO")
    if not settings.onboarding_login_url:
        missing.append("PILOT_PROVISIONING_ONBOARDING_LOGIN_URL")

    ready = bool(settings.enabled and not missing)
    return {
        "enabled": settings.enabled,
        "ready": ready,
        "missing": missing,
    }
