import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.common.observability import (
    get_correlation_id,
    log_fields,
)
from apps.control_plane.src.application.pilot_requests.notifications import (
    PilotRequestNotification,
    PilotRequestNotifierPort,
)
from apps.control_plane.src.application.pilot_requests.provisioning_notifications import (
    PilotProvisioningFailureNotification,
    PilotProvisioningNotifierPort,
    PilotProvisioningSuccessNotification,
)
from apps.control_plane.src.application.pilot_requests.ports import (
    PilotRequestRepositoryPort,
)
from apps.control_plane.src.application.pilot_requests.service import (
    create_pilot_request as create_pilot_request_service,
    list_pilot_requests as list_pilot_requests_service,
    update_pilot_request_status as update_pilot_request_status_service,
)
from apps.control_plane.src.application.pilot_provisioning.ports import (
    PilotProvisioningRepositoryPort,
)
from apps.control_plane.src.application.pilot_provisioning.service import (
    provision_pilot_request as provision_pilot_request_service,
)
from apps.control_plane.src.application.pilot_provisioning.types import (
    ProvisionPilotRequestInput,
)
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
from apps.control_plane.src.application.pilot_requests.types import (
    CreatePilotRequestInput,
    ListPilotRequestsInput,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import (
    get_instructor_identity_provider,
    get_instructor_provisioning_repository,
    get_pilot_provisioning_notifier,
    get_pilot_request_notifier,
    get_pilot_provisioning_repository,
    get_pilot_request_repository,
)
from apps.control_plane.src.interfaces.http.schemas import (
    ApproveAndProvisionRequest,
    ApproveAndProvisionResponse,
    CreatePilotRequest,
    CreatePilotRequestResponse,
    InstructorProvisioningSummaryResponse,
    ListPilotRequestsResponse,
    PilotRequestItemResponse,
    ProvisioningSummaryResponse,
    UpdatePilotRequestStatusRequest,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _require_admin_or_staff(principal: PrincipalContext) -> None:
    if principal.role not in {"admin", "staff"}:
        raise HTTPException(status_code=403, detail="Forbidden")


def _require_admin(principal: PrincipalContext) -> None:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")


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


@router.get("/api/v1/pilot-requests", response_model=ListPilotRequestsResponse)
def list_pilot_requests(
    principal: PrincipalContext = Depends(get_current_principal),
    repo: PilotRequestRepositoryPort = Depends(get_pilot_request_repository),
    status: str | None = None,
    created_after: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
) -> ListPilotRequestsResponse:
    _require_admin_or_staff(principal)
    allowed_statuses = {
        "new",
        "contacted",
        "approved",
        "approved_provisioning_failed",
        "rejected",
    }
    if status is not None and status not in allowed_statuses:
        raise HTTPException(status_code=422, detail="Invalid status filter")

    result = list_pilot_requests_service(
        repo=repo,
        query=ListPilotRequestsInput(
            status=status,
            created_after=created_after,
            limit=limit,
            offset=offset,
        ),
    )
    return ListPilotRequestsResponse(
        items=[
            PilotRequestItemResponse(
                requestId=str(item.id),
                fullName=item.full_name,
                workEmail=item.work_email,
                university=item.university,
                role=item.role,
                courseName=item.course_name,
                cohortSize=item.cohort_size,
                notes=item.notes,
                sourceIp=item.source_ip,
                status=item.status,
                createdAt=item.created_at,
            )
            for item in result.items
        ],
        limit=result.limit,
        offset=result.offset,
    )


@router.patch(
    "/api/v1/pilot-requests/{request_id}", response_model=PilotRequestItemResponse
)
def update_pilot_request_status(
    request_id: UUID,
    payload: UpdatePilotRequestStatusRequest,
    principal: PrincipalContext = Depends(get_current_principal),
    repo: PilotRequestRepositoryPort = Depends(get_pilot_request_repository),
) -> PilotRequestItemResponse:
    _require_admin_or_staff(principal)
    result = update_pilot_request_status_service(
        repo=repo, request_id=request_id, next_status=payload.status.strip().lower()
    )
    if not result.updated:
        if result.error_code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.error)
        if result.error_code == "INVALID_TRANSITION":
            raise HTTPException(status_code=409, detail=result.error)
        raise HTTPException(status_code=422, detail=result.error)

    item = result.request
    if item is None:
        raise HTTPException(status_code=500, detail="Pilot request update failed")

    return PilotRequestItemResponse(
        requestId=str(item.id),
        fullName=item.full_name,
        workEmail=item.work_email,
        university=item.university,
        role=item.role,
        courseName=item.course_name,
        cohortSize=item.cohort_size,
        notes=item.notes,
        sourceIp=item.source_ip,
        status=item.status,
        createdAt=item.created_at,
    )


@router.post(
    "/api/v1/pilot-requests/{request_id}/approve-and-provision",
    response_model=ApproveAndProvisionResponse,
)
def approve_and_provision_pilot_request(
    request_id: UUID,
    payload: ApproveAndProvisionRequest,
    principal: PrincipalContext = Depends(get_current_principal),
    pilot_request_repo: PilotRequestRepositoryPort = Depends(
        get_pilot_request_repository
    ),
    pilot_provisioning_repo: PilotProvisioningRepositoryPort = Depends(
        get_pilot_provisioning_repository
    ),
    instructor_repo: InstructorProvisioningRepositoryPort = Depends(
        get_instructor_provisioning_repository
    ),
    identity_provider: InstructorIdentityProviderPort = Depends(
        get_instructor_identity_provider
    ),
    provisioning_notifier: PilotProvisioningNotifierPort = Depends(
        get_pilot_provisioning_notifier
    ),
) -> ApproveAndProvisionResponse:
    _require_admin(principal)
    run_correlation_id = get_correlation_id()

    existing = pilot_request_repo.get_pilot_request_by_id(request_id=request_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Pilot request not found")

    approved_step = False
    is_retry = False
    if existing.status == "contacted":
        approved_result = update_pilot_request_status_service(
            repo=pilot_request_repo, request_id=request_id, next_status="approved"
        )
        if not approved_result.updated:
            if approved_result.error_code == "INVALID_TRANSITION":
                raise HTTPException(status_code=409, detail=approved_result.error)
            raise HTTPException(status_code=422, detail=approved_result.error)
        approved_step = True
    elif existing.status == "approved_provisioning_failed":
        approved_step = True
        is_retry = True
    else:
        raise HTTPException(
            status_code=409,
            detail="Pilot request must be contacted or approved_provisioning_failed.",
        )

    pilot_result = provision_pilot_request_service(
        repo=pilot_provisioning_repo,
        request=ProvisionPilotRequestInput(
            pilot_request_id=request_id,
            course_id=payload.courseId,
            course_name=payload.courseName,
            class_code=payload.classCode,
            instructor_email=payload.instructorEmail,
            max_uses=payload.classCodeMaxUses,
            provisioned_by=principal.user_id,
            provisioning_correlation_id=run_correlation_id,
        ),
    )
    if not pilot_result.ok or pilot_result.summary is None:
        pilot_error_message = pilot_result.error or "Pilot provisioning failed"
        try:
            provisioning_notifier.notify_failure(
                PilotProvisioningFailureNotification(
                    pilot_request_id=request_id,
                    instructor_email=payload.instructorEmail,
                    step="pilot_provision",
                    error_code=pilot_result.error_code,
                    error_message=pilot_error_message,
                    is_retry=is_retry,
                    run_correlation_id=run_correlation_id,
                    failed_at=datetime.now(UTC),
                )
            )
        except Exception:
            logger.exception(
                "pilot provisioning failure notification failed",
                extra={
                    "event": "pilot_provisioning_failure_notification_failed",
                    "pilot_request_id": str(request_id),
                    "step": "pilot_provision",
                },
            )
        failed_status_result = update_pilot_request_status_service(
            repo=pilot_request_repo,
            request_id=request_id,
            next_status="approved_provisioning_failed",
        )
        status_item = failed_status_result.request or existing
        logger.warning(
            "approve and provision failed in pilot provisioning step",
            extra={
                **log_fields(principal_id=principal.user_id),
                "event": "pilot_request_approve_and_provision_failed",
                "pilot_request_id": str(request_id),
                "step": "pilot_provision",
                "is_retry": is_retry,
                "error_code": pilot_result.error_code,
            },
        )
        return ApproveAndProvisionResponse(
            pilotRequest=PilotRequestItemResponse(
                requestId=str(status_item.id),
                fullName=status_item.full_name,
                workEmail=status_item.work_email,
                university=status_item.university,
                role=status_item.role,
                courseName=status_item.course_name,
                cohortSize=status_item.cohort_size,
                notes=status_item.notes,
                sourceIp=status_item.source_ip,
                status=status_item.status,
                createdAt=status_item.created_at,
            ),
            isRetry=is_retry,
            runCorrelationId=run_correlation_id,
            approvedStep=approved_step,
            pilotProvisionError=pilot_error_message,
        )

    instructor_result = provision_instructor_service(
        repo=instructor_repo,
        identity_provider=identity_provider,
        request=ProvisionInstructorInput(
            pilot_request_id=request_id,
            instructor_email=payload.instructorEmail,
            create_user_if_missing=payload.createInstructorIfMissing,
            provisioned_by=principal.user_id,
            provisioning_correlation_id=run_correlation_id,
        ),
    )
    if not instructor_result.ok or instructor_result.summary is None:
        instructor_error_message = (
            instructor_result.error or "Instructor provisioning failed"
        )
        try:
            provisioning_notifier.notify_failure(
                PilotProvisioningFailureNotification(
                    pilot_request_id=request_id,
                    instructor_email=payload.instructorEmail,
                    step="instructor_provision",
                    error_code=instructor_result.error_code,
                    error_message=instructor_error_message,
                    is_retry=is_retry,
                    run_correlation_id=run_correlation_id,
                    failed_at=datetime.now(UTC),
                )
            )
        except Exception:
            logger.exception(
                "pilot provisioning failure notification failed",
                extra={
                    "event": "pilot_provisioning_failure_notification_failed",
                    "pilot_request_id": str(request_id),
                    "step": "instructor_provision",
                },
            )
        failed_status_result = update_pilot_request_status_service(
            repo=pilot_request_repo,
            request_id=request_id,
            next_status="approved_provisioning_failed",
        )
        status_item = failed_status_result.request or existing
        pilot_summary = pilot_result.summary
        logger.warning(
            "approve and provision failed in instructor provisioning step",
            extra={
                **log_fields(principal_id=principal.user_id),
                "event": "pilot_request_approve_and_provision_failed",
                "pilot_request_id": str(request_id),
                "step": "instructor_provision",
                "is_retry": is_retry,
                "error_code": instructor_result.error_code,
            },
        )
        return ApproveAndProvisionResponse(
            pilotRequest=PilotRequestItemResponse(
                requestId=str(status_item.id),
                fullName=status_item.full_name,
                workEmail=status_item.work_email,
                university=status_item.university,
                role=status_item.role,
                courseName=status_item.course_name,
                cohortSize=status_item.cohort_size,
                notes=status_item.notes,
                sourceIp=status_item.source_ip,
                status=status_item.status,
                createdAt=status_item.created_at,
            ),
            isRetry=is_retry,
            runCorrelationId=run_correlation_id,
            approvedStep=approved_step,
            pilotProvisionStep=ProvisioningSummaryResponse(
                pilotRequestId=str(pilot_summary.pilot_request_id),
                courseId=pilot_summary.course_id,
                courseName=pilot_summary.course_name,
                classCode=pilot_summary.class_code,
                classCodeId=str(pilot_summary.class_code_id),
                classCodeStatus=pilot_summary.class_code_status,
                classCodeMaxUses=pilot_summary.class_code_max_uses,
                instructorEmail=pilot_summary.instructor_email,
                provisionedBy=(
                    str(pilot_summary.provisioned_by)
                    if pilot_summary.provisioned_by is not None
                    else None
                ),
                provisioningCorrelationId=pilot_summary.provisioning_correlation_id,
                provisionedAt=pilot_summary.provisioned_at,
            ),
            instructorProvisionError=instructor_error_message,
        )

    final_status_result = update_pilot_request_status_service(
        repo=pilot_request_repo, request_id=request_id, next_status="approved"
    )
    status_item = final_status_result.request or existing
    pilot_summary = pilot_result.summary
    instructor_summary = instructor_result.summary
    logger.info(
        "approve and provision completed",
        extra={
            **log_fields(principal_id=principal.user_id),
            "event": "pilot_request_approve_and_provision_completed",
            "pilot_request_id": str(request_id),
            "is_retry": is_retry,
        },
    )
    try:
        provisioning_notifier.notify_success(
            PilotProvisioningSuccessNotification(
                pilot_request_id=request_id,
                course_id=payload.courseId,
                course_name=payload.courseName,
                class_code=payload.classCode,
                instructor_email=payload.instructorEmail,
                create_user_if_missing=payload.createInstructorIfMissing,
                run_correlation_id=run_correlation_id,
                provisioned_at=datetime.now(UTC),
            )
        )
    except Exception:
        logger.exception(
            "pilot provisioning success notification failed",
            extra={
                "event": "pilot_provisioning_success_notification_failed",
                "pilot_request_id": str(request_id),
            },
        )
    return ApproveAndProvisionResponse(
        pilotRequest=PilotRequestItemResponse(
            requestId=str(status_item.id),
            fullName=status_item.full_name,
            workEmail=status_item.work_email,
            university=status_item.university,
            role=status_item.role,
            courseName=status_item.course_name,
            cohortSize=status_item.cohort_size,
            notes=status_item.notes,
            sourceIp=status_item.source_ip,
            status=status_item.status,
            createdAt=status_item.created_at,
        ),
        isRetry=is_retry,
        runCorrelationId=run_correlation_id,
        approvedStep=approved_step,
        pilotProvisionStep=ProvisioningSummaryResponse(
            pilotRequestId=str(pilot_summary.pilot_request_id),
            courseId=pilot_summary.course_id,
            courseName=pilot_summary.course_name,
            classCode=pilot_summary.class_code,
            classCodeId=str(pilot_summary.class_code_id),
            classCodeStatus=pilot_summary.class_code_status,
            classCodeMaxUses=pilot_summary.class_code_max_uses,
            instructorEmail=pilot_summary.instructor_email,
            provisionedBy=(
                str(pilot_summary.provisioned_by)
                if pilot_summary.provisioned_by is not None
                else None
            ),
            provisioningCorrelationId=pilot_summary.provisioning_correlation_id,
            provisionedAt=pilot_summary.provisioned_at,
        ),
        instructorProvisionStep=InstructorProvisioningSummaryResponse(
            pilotRequestId=str(instructor_summary.pilot_request_id),
            courseId=instructor_summary.course_id,
            courseName=instructor_summary.course_name,
            instructorEmail=instructor_summary.instructor_email,
            userCreated=instructor_summary.user_created,
            groupAssigned=instructor_summary.group_assigned,
            instructorUserId=instructor_summary.instructor_user_id,
            membershipCreated=instructor_summary.membership_created,
            provisionedBy=(
                str(instructor_summary.provisioned_by)
                if instructor_summary.provisioned_by is not None
                else None
            ),
            provisioningCorrelationId=instructor_summary.provisioning_correlation_id,
            provisionedAt=instructor_summary.provisioned_at,
        ),
    )
