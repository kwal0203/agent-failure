import logging
import smtplib
from email.message import EmailMessage

from apps.control_plane.src.application.pilot_requests.provisioning_notifications import (
    PilotProvisioningFailureNotification,
    PilotProvisioningNotifierPort,
    PilotProvisioningSuccessNotification,
)
from apps.control_plane.src.infrastructure.config.settings import (
    PilotProvisioningEmailSettings,
)

logger = logging.getLogger(__name__)


def _mask_email(email: str) -> str:
    parts = email.split("@", 1)
    if len(parts) != 2:
        return "***"
    local, domain = parts
    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}"
    return f"{masked_local}@{domain}"


class NoopPilotProvisioningNotifier(PilotProvisioningNotifierPort):
    def notify_success(self, payload: PilotProvisioningSuccessNotification) -> None:
        _ = payload

    def notify_failure(self, payload: PilotProvisioningFailureNotification) -> None:
        _ = payload


class SmtpPilotProvisioningNotifier(PilotProvisioningNotifierPort):
    def __init__(self, settings: PilotProvisioningEmailSettings) -> None:
        self._settings = settings

    def notify_success(self, payload: PilotProvisioningSuccessNotification) -> None:
        message = EmailMessage()
        message["Subject"] = "Agent Failure pilot approved and provisioned"
        message["From"] = self._settings.from_email
        message["To"] = payload.instructor_email.strip().lower()
        message.set_content(
            "\n".join(
                [
                    "Your Agent Failure university pilot has been approved.",
                    "",
                    f"Course: {payload.course_name}",
                    f"Course ID: {payload.course_id}",
                    f"Class code: {payload.class_code}",
                    "",
                    "Next steps:",
                    "1. Sign in with your instructor account.",
                    "2. Open the lab catalog and verify course setup.",
                    "3. Share the class code with students.",
                    "",
                    f"Login URL: {self._settings.onboarding_login_url}",
                    (
                        f"Quickstart: {self._settings.onboarding_quickstart_url}"
                        if self._settings.onboarding_quickstart_url
                        else "Quickstart: (not configured)"
                    ),
                    "",
                    f"Request ID: {payload.pilot_request_id}",
                    f"Correlation ID: {payload.run_correlation_id}",
                    f"Created account if missing: {'yes' if payload.create_user_if_missing else 'no'}",
                ]
            )
        )
        self._send_message(message)
        logger.info(
            "pilot provisioning onboarding email sent",
            extra={"event": "pilot_provisioning_onboarding_email_sent"},
        )

    def notify_failure(self, payload: PilotProvisioningFailureNotification) -> None:
        message = EmailMessage()
        message["Subject"] = "Agent Failure pilot provisioning failed"
        message["From"] = self._settings.from_email
        message["To"] = ", ".join(self._settings.admin_to_emails)
        message.set_content(
            "\n".join(
                [
                    "Pilot request approval/provisioning failed.",
                    "",
                    f"request_id: {payload.pilot_request_id}",
                    f"failed_at: {payload.failed_at.isoformat()}",
                    f"step: {payload.step}",
                    f"is_retry: {'yes' if payload.is_retry else 'no'}",
                    f"error_code: {payload.error_code or '(none)'}",
                    f"error_message: {payload.error_message}",
                    f"instructor_email: {_mask_email(payload.instructor_email)}",
                    f"correlation_id: {payload.run_correlation_id}",
                ]
            )
        )
        self._send_message(message)
        logger.info(
            "pilot provisioning failure alert email sent",
            extra={"event": "pilot_provisioning_failure_email_sent"},
        )

    def _send_message(self, message: EmailMessage) -> None:
        with smtplib.SMTP(
            host=self._settings.smtp_host,
            port=self._settings.smtp_port,
            timeout=10,
        ) as smtp:
            if self._settings.smtp_starttls:
                smtp.starttls()
            if self._settings.smtp_username and self._settings.smtp_password:
                smtp.login(
                    self._settings.smtp_username,
                    self._settings.smtp_password,
                )
            smtp.send_message(message)
