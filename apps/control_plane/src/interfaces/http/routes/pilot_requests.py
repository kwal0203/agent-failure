from fastapi import APIRouter, Depends, HTTPException, Request

from apps.control_plane.src.application.pilot_requests.ports import (
    PilotRequestRepositoryPort,
)
from apps.control_plane.src.application.pilot_requests.service import (
    create_pilot_request as create_pilot_request_service,
)
from apps.control_plane.src.application.pilot_requests.types import (
    CreatePilotRequestInput,
)
from apps.control_plane.src.interfaces.http.dependencies import (
    get_pilot_request_repository,
)
from apps.control_plane.src.interfaces.http.schemas import (
    CreatePilotRequest,
    CreatePilotRequestResponse,
)

router = APIRouter()


@router.post(
    "/api/v1/pilot-requests",
    response_model=CreatePilotRequestResponse,
    status_code=201,
)
def create_pilot_request(
    payload: CreatePilotRequest,
    request: Request,
    repo: PilotRequestRepositoryPort = Depends(get_pilot_request_repository),
) -> CreatePilotRequestResponse:
    source_ip = request.client.host if request.client is not None else None
    result = create_pilot_request_service(
        repo=repo,
        request=CreatePilotRequestInput(
            full_name=payload.fullName,
            work_email=payload.workEmail,
            university=payload.university,
            role=payload.role,
            course_name=payload.courseName,
            cohort_size=payload.cohortSize,
            notes=payload.notes,
            source_ip=source_ip,
        ),
    )

    if not result.accepted:
        if result.error_code == "DUPLICATE_REQUEST":
            raise HTTPException(status_code=409, detail=result.error)
        if result.error_code == "RATE_LIMITED":
            raise HTTPException(status_code=429, detail=result.error)
        raise HTTPException(status_code=422, detail=result.error)

    created = result.request
    if created is None:
        raise HTTPException(status_code=500, detail="Pilot request was not persisted")

    return CreatePilotRequestResponse(
        requestId=str(created.id), status=created.status, createdAt=created.created_at
    )
