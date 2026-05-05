from sqlalchemy import func
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_create.ports import (
    AdmissionPolicy,
    AdmissionDecision,
)
from apps.control_plane.src.infrastructure.config.settings import AdmissionSettings
from apps.control_plane.src.infrastructure.persistence.models import SessionModel
from uuid import UUID

ACTIVE_STATES = ("CREATED", "PROVISIONING", "ACTIVE", "IDLE")


class StubAdmissionPolicy(AdmissionPolicy):
    def check_launch_allowed(self, user_id: UUID, lab_id: UUID) -> AdmissionDecision:
        return AdmissionDecision(
            allowed=True, code=None, message=None, retryable=False, details=None
        )


class ConcreteAdmissionPolicy(AdmissionPolicy):
    def __init__(self, db: Session, settings: AdmissionSettings) -> None:
        self._db = db
        self._settings = settings

    def check_launch_allowed(self, user_id: UUID, lab_id: UUID) -> AdmissionDecision:
        user_count = (
            self._db.query(func.count())
            .select_from(SessionModel)
            .filter(
                SessionModel.owner_user_id == user_id,
                SessionModel.state.in_(ACTIVE_STATES),
            )
            .scalar()
        )

        if user_count >= self._settings.max_sessions_per_user:
            return AdmissionDecision(
                allowed=False,
                code="QUOTA_EXCEEDED",
                message="You have reached the maximum number of active sessions.",
                retryable=True,
                details={
                    "current": user_count,
                    "quota": self._settings.max_sessions_per_user,
                    "limit": self._settings.max_sessions_per_user,
                },
            )

        global_count = (
            self._db.query(func.count())
            .select_from(SessionModel)
            .filter(SessionModel.state.in_(ACTIVE_STATES))
            .scalar()
        )

        if global_count >= self._settings.max_sessions_global:
            return AdmissionDecision(
                allowed=False,
                code="RATE_LIMITED",
                message="The platform is at capacity. Please try again later.",
                retryable=True,
                details={
                    "current": global_count,
                    "quota": self._settings.max_sessions_global,
                    "limit": self._settings.max_sessions_global,
                },
            )

        return AdmissionDecision(
            allowed=True, code=None, message=None, retryable=False, details=None
        )
