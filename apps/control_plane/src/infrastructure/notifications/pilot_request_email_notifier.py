import logging
import smtplib
from email.message import EmailMessage

from apps.control_plane.src.application.pilot_requests.notifications import (
    PilotRequestNotification,
    PilotRequestNotifierPort,
)
from apps.control_plane.src.infrastructure.config.settings import (
    PilotAlertEmailSettings,
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


def _truncate(text: str, *, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 3]}..."


class NoopPilotRequestNotifier(PilotRequestNotifierPort):
    def notify(self, payload: PilotRequestNotification) -> None:
        _ = payload


class SmtpPilotRequestNotifier(PilotRequestNotifierPort):
    def __init__(self, settings: PilotAlertEmailSettings) -> None:
        self._settings = settings

    def notify(self, payload: PilotRequestNotification) -> None:
        notes = payload.notes.strip() if payload.notes else ""
        notes_excerpt = _truncate(notes, max_len=240) if notes else "(none)"
        safe_email = _mask_email(payload.work_email)

        message = EmailMessage()
        message["Subject"] = "New pilot request submitted"
        message["From"] = self._settings.from_email
        message["To"] = ", ".join(self._settings.to_emails)
        message.set_content(
            "\n".join(
                [
                    "A new university pilot request was submitted.",
                    "",
                    f"request_id: {payload.request_id}",
                    f"created_at: {payload.created_at.isoformat()}",
                    f"status: {payload.status}",
                    f"full_name: {payload.full_name}",
                    f"work_email: {safe_email}",
                    f"university: {payload.university}",
                    f"role: {payload.role or '(none)'}",
                    f"course_name: {payload.course_name or '(none)'}",
                    f"cohort_size: {payload.cohort_size if payload.cohort_size is not None else '(none)'}",
                    f"source_ip: {payload.source_ip or '(none)'}",
                    "notes_excerpt:",
                    notes_excerpt,
                ]
            )
        )

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

        logger.info(
            "pilot request alert email sent",
            extra={"event": "pilot_request_alert_email_sent"},
        )
