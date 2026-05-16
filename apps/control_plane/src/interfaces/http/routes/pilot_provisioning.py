from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.pilot_provisioning.ports import (
    PilotProvisioningRepositoryPort,
)
from apps.control_plane.src.application.pilot_provisioning.service import (
    provision_pilot_request as provision_pilot_request_service,
)
from apps.control_plane.src.application.pilot_provisioning.types import (
    ProvisionPilotRequestInput,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import (
    get_pilot_provisioning_repository,
)
from apps.control_plane.src.interfaces.http.schemas import (
    ProvisionPilotRequestPayload,
    ProvisionPilotRequestResponse,
    ProvisioningSummaryResponse,
)

router = APIRouter()


def _require_admin(principal: PrincipalContext) -> None:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post(
    "/api/v1/pilot-requests/{request_id}/provision",
    response_model=ProvisionPilotRequestResponse,
)
def provision_pilot_request(
    request_id: UUID,
    payload: ProvisionPilotRequestPayload,
    principal: PrincipalContext = Depends(get_current_principal),
    repo: PilotProvisioningRepositoryPort = Depends(get_pilot_provisioning_repository),
) -> ProvisionPilotRequestResponse:
    _require_admin(principal)
    result = provision_pilot_request_service(
        repo=repo,
        request=ProvisionPilotRequestInput(
            pilot_request_id=request_id,
            course_id=payload.courseId,
            course_name=payload.courseName,
            class_code=payload.classCode,
            instructor_email=payload.instructorEmail,
            max_uses=payload.maxUses,
        ),
    )
    if not result.ok:
        if result.error_code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.error)
        if result.error_code == "CONFLICT":
            raise HTTPException(status_code=409, detail=result.error)
        raise HTTPException(status_code=422, detail=result.error)

    if result.summary is None:
        raise HTTPException(status_code=500, detail="Provisioning summary missing")

    return ProvisionPilotRequestResponse(
        created=result.created,
        provisioningSummary=ProvisioningSummaryResponse(
            pilotRequestId=str(result.summary.pilot_request_id),
            courseId=result.summary.course_id,
            courseName=result.summary.course_name,
            classCode=result.summary.class_code,
            classCodeStatus=result.summary.class_code_status,
            classCodeMaxUses=result.summary.class_code_max_uses,
            instructorEmail=result.summary.instructor_email,
            provisionedAt=result.summary.provisioned_at,
        ),
    )
