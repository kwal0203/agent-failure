from .ports import PilotProvisioningRepositoryPort
from .types import (
    ProvisionPilotRequestInput,
    ProvisionPilotRequestResult,
    ProvisionPilotRequestSummary,
)


def provision_pilot_request(
    *,
    repo: PilotProvisioningRepositoryPort,
    request: ProvisionPilotRequestInput,
) -> ProvisionPilotRequestResult:
    course_id = request.course_id.strip()
    course_name = request.course_name.strip()
    class_code = request.class_code.strip().upper()
    instructor_email = request.instructor_email.strip().lower()

    if not course_id or not course_name or not class_code or not instructor_email:
        return ProvisionPilotRequestResult(
            ok=False,
            error="courseId, courseName, classCode, and instructorEmail are required.",
            error_code="VALIDATION_ERROR",
        )

    if not repo.pilot_request_exists(request_id=request.pilot_request_id):
        return ProvisionPilotRequestResult(
            ok=False,
            error="Pilot request not found.",
            error_code="NOT_FOUND",
        )

    try:
        provision, created = repo.create_or_get_provision(
            request=ProvisionPilotRequestInput(
                pilot_request_id=request.pilot_request_id,
                course_id=course_id,
                course_name=course_name,
                class_code=class_code,
                instructor_email=instructor_email,
                max_uses=request.max_uses,
            )
        )
    except ValueError as exc:
        return ProvisionPilotRequestResult(
            ok=False,
            error=str(exc),
            error_code="CONFLICT",
        )

    if created:
        repo.commit()

    return ProvisionPilotRequestResult(
        ok=True,
        created=created,
        summary=ProvisionPilotRequestSummary(
            pilot_request_id=provision.pilot_request_id,
            course_id=provision.course_id,
            course_name=provision.course_name,
            class_code=provision.class_code,
            class_code_status=provision.class_code_status,
            class_code_max_uses=provision.class_code_max_uses,
            instructor_email=provision.instructor_email,
            provisioned_at=provision.created_at,
        ),
    )
