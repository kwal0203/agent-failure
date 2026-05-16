import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.control_plane.src.application.pilot_requests.notifications import (
    PilotRequestNotification,
    PilotRequestNotifierPort,
)
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
    get_pilot_request_notifier,
    get_pilot_request_repository,
)
from apps.control_plane.src.interfaces.http.schemas import (
    CreatePilotRequest,
    CreatePilotRequestResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/api/v1/pilot-requests",
    response_model=CreatePilotRequestResponse,
    status_code=201,
)
def create_pilot_request(
    payload: CreatePilotRequest,
    request: Request,
    repo: PilotRequestRepositoryPort = Depends(get_pilot_request_repository),
    notifier: PilotRequestNotifierPort = Depends(get_pilot_request_notifier),
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

    try:
        notifier.notify(
            PilotRequestNotification(
                request_id=created.id,
                status=created.status,
                created_at=created.created_at,
                full_name=payload.fullName.strip(),
                work_email=payload.workEmail.strip().lower(),
                university=payload.university.strip(),
                role=payload.role.strip() if payload.role else None,
                course_name=payload.courseName.strip() if payload.courseName else None,
                cohort_size=payload.cohortSize,
                notes=payload.notes.strip() if payload.notes else None,
                source_ip=source_ip,
            )
        )
    except Exception:
        # Notification delivery should not block pilot request creation.
        logger.exception(
            "pilot request email alert failed",
            extra={
                "event": "pilot_request_alert_failed",
                "request_id": str(created.id),
            },
        )

    return CreatePilotRequestResponse(
        requestId=str(created.id), status=created.status, createdAt=created.created_at
    )
