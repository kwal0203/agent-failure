from apps.control_plane.src.application.session_create.ports import (
    AdmissionPolicy,
    AdmissionDecision,
)
from uuid import UUID


# TODO: Complete the concrete admission policy implementation
class StubAdmissionPolicy(AdmissionPolicy):
    def check_launch_allowed(self, user_id: UUID, lab_id: UUID) -> AdmissionDecision:
        return AdmissionDecision(
            allowed=True, code=None, message=None, retryable=False, details=None
        )
