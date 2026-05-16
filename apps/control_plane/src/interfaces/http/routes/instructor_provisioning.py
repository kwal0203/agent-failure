from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.instructor_provisioning.ports import (
    InstructorIdentityProviderPort,
    InstructorProvisioningRepositoryPort,
)
from apps.control_plane.src.application.instructor_provisioning.service import (
    provision_instructor as provision_instructor_service,
)
from apps.control_plane.src.application.instructor_provisioning.types import (
    ProvisionInstructorInput,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import (
    get_instructor_identity_provider,
    get_instructor_provisioning_repository,
)
from apps.control_plane.src.interfaces.http.schemas import (
    InstructorProvisioningSummaryResponse,
    ProvisionInstructorRequest,
    ProvisionInstructorResponse,
)

router = APIRouter()


def _require_admin(principal: PrincipalContext) -> None:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post(
    "/api/v1/admin/instructors/provision",
    response_model=ProvisionInstructorResponse,
)
def provision_instructor(
    payload: ProvisionInstructorRequest,
    principal: PrincipalContext = Depends(get_current_principal),
    repo: InstructorProvisioningRepositoryPort = Depends(
        get_instructor_provisioning_repository
    ),
    identity_provider: InstructorIdentityProviderPort = Depends(
        get_instructor_identity_provider
    ),
) -> ProvisionInstructorResponse:
    _require_admin(principal)
    try:
        pilot_request_id = UUID(payload.pilotRequestId)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid pilotRequestId") from exc

    result = provision_instructor_service(
        repo=repo,
        identity_provider=identity_provider,
        request=ProvisionInstructorInput(
            pilot_request_id=pilot_request_id,
            instructor_email=payload.instructorEmail,
            create_user_if_missing=payload.createUserIfMissing,
        ),
    )
    if not result.ok:
        if result.error_code == "NOT_PROVISIONED":
            raise HTTPException(status_code=404, detail=result.error)
        if result.error_code in {"EMAIL_MISMATCH", "IDENTITY_ERROR"}:
            raise HTTPException(status_code=409, detail=result.error)
        raise HTTPException(status_code=422, detail=result.error)

    if result.summary is None:
        raise HTTPException(status_code=500, detail="Provisioning summary missing")

    return ProvisionInstructorResponse(
        provisioningSummary=InstructorProvisioningSummaryResponse(
            pilotRequestId=str(result.summary.pilot_request_id),
            courseId=result.summary.course_id,
            courseName=result.summary.course_name,
            instructorEmail=result.summary.instructor_email,
            userCreated=result.summary.user_created,
            groupAssigned=result.summary.group_assigned,
            membershipCreated=result.summary.membership_created,
            provisionedAt=result.summary.provisioned_at,
        )
    )
