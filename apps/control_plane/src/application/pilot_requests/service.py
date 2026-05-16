from datetime import UTC, datetime, timedelta
from uuid import UUID

from .ports import PilotRequestRepositoryPort
from .types import (
    CreatePilotRequestInput,
    CreatePilotRequestResult,
    ListPilotRequestsInput,
    ListPilotRequestsResult,
    UpdatePilotRequestStatusResult,
)


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
        work_email=work_email,
        university=university,
        since=duplicate_window,
    ):
        return CreatePilotRequestResult(
            accepted=False,
            error="A recent request for this email already exists.",
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


def list_pilot_requests(
    *,
    repo: PilotRequestRepositoryPort,
    query: ListPilotRequestsInput,
) -> ListPilotRequestsResult:
    safe_limit = min(max(query.limit, 1), 100)
    safe_offset = max(query.offset, 0)
    items = repo.list_pilot_requests(
        status=query.status,
        created_after=query.created_after,
        limit=safe_limit,
        offset=safe_offset,
    )
    return ListPilotRequestsResult(items=items, limit=safe_limit, offset=safe_offset)


def update_pilot_request_status(
    *,
    repo: PilotRequestRepositoryPort,
    request_id: UUID,
    next_status: str,
) -> UpdatePilotRequestStatusResult:
    allowed = {
        "new",
        "contacted",
        "approved",
        "approved_provisioning_failed",
        "rejected",
    }
    if next_status not in allowed:
        return UpdatePilotRequestStatusResult(
            updated=False,
            error="Invalid status",
            error_code="INVALID_STATUS",
        )

    existing = repo.get_pilot_request_by_id(request_id=request_id)
    if existing is None:
        return UpdatePilotRequestStatusResult(
            updated=False,
            error="Pilot request not found",
            error_code="NOT_FOUND",
        )

    allowed_transitions = {
        "new": {"contacted"},
        "contacted": {"approved", "approved_provisioning_failed", "rejected"},
        "approved": {"approved_provisioning_failed"},
        "approved_provisioning_failed": {"approved"},
        "rejected": set(),
    }
    if next_status == existing.status:
        return UpdatePilotRequestStatusResult(updated=True, request=existing)
    if next_status not in allowed_transitions.get(existing.status, set()):
        return UpdatePilotRequestStatusResult(
            updated=False,
            error="Invalid status transition",
            error_code="INVALID_TRANSITION",
        )

    updated = repo.update_pilot_request_status(
        request_id=request_id,
        status=next_status,
    )
    if updated is None:
        return UpdatePilotRequestStatusResult(
            updated=False,
            error="Pilot request not found",
            error_code="NOT_FOUND",
        )
    repo.commit()
    return UpdatePilotRequestStatusResult(updated=True, request=updated)
