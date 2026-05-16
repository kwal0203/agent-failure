from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PilotProvisioningSuccessNotification:
    pilot_request_id: UUID
    course_id: str
    course_name: str
    class_code: str
    instructor_email: str
    create_user_if_missing: bool
    run_correlation_id: str
    provisioned_at: datetime


@dataclass(frozen=True)
class PilotProvisioningFailureNotification:
    pilot_request_id: UUID
    instructor_email: str
    step: str
    error_code: str | None
    error_message: str
    is_retry: bool
    run_correlation_id: str
    failed_at: datetime


class PilotProvisioningNotifierPort(Protocol):
    def notify_success(self, payload: PilotProvisioningSuccessNotification) -> None: ...

    def notify_failure(self, payload: PilotProvisioningFailureNotification) -> None: ...
