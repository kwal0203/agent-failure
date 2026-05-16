from datetime import UTC, datetime, timedelta

from .ports import PilotRequestRepositoryPort
from .types import CreatePilotRequestInput, CreatePilotRequestResult


def create_pilot_request(
    *,
    repo: PilotRequestRepositoryPort,
    request: CreatePilotRequestInput,
) -> CreatePilotRequestResult:
    full_name = request.full_name.strip()
    work_email = request.work_email.strip().lower()
    university = request.university.strip()
    role = request.role.strip() if request.role is not None else None
    course_name = (
        request.course_name.strip() if request.course_name is not None else None
    )
    notes = request.notes.strip() if request.notes is not None else None

    if not full_name or not work_email or not university:
        return CreatePilotRequestResult(
            accepted=False,
            error="Name, work email, and university are required.",
            error_code="VALIDATION_ERROR",
        )

    now = datetime.now(UTC)
    duplicate_window = now - timedelta(days=7)
    if repo.exists_recent_duplicate(
        work_email=work_email, university=university, since=duplicate_window
    ):
        return CreatePilotRequestResult(
            accepted=False,
            error="A recent request for this email and university already exists.",
            error_code="DUPLICATE_REQUEST",
        )

    email_window = now - timedelta(hours=1)
    if repo.count_recent_by_work_email(work_email=work_email, since=email_window) >= 3:
        return CreatePilotRequestResult(
            accepted=False,
            error="Too many requests from this email. Please try again later.",
            error_code="RATE_LIMITED",
        )

    if request.source_ip:
        ip_window = now - timedelta(minutes=15)
        if (
            repo.count_recent_by_source_ip(source_ip=request.source_ip, since=ip_window)
            >= 10
        ):
            return CreatePilotRequestResult(
                accepted=False,
                error="Too many requests from this network. Please try again later.",
                error_code="RATE_LIMITED",
            )

    created = repo.create_pilot_request(
        CreatePilotRequestInput(
            full_name=full_name,
            work_email=work_email,
            university=university,
            role=role or None,
            course_name=course_name or None,
            cohort_size=request.cohort_size,
            notes=notes or None,
            source_ip=request.source_ip,
        )
    )
    repo.commit()

    return CreatePilotRequestResult(accepted=True, request=created)
