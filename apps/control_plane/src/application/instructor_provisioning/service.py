from datetime import UTC, datetime

from .ports import InstructorIdentityProviderPort, InstructorProvisioningRepositoryPort
from .types import (
    ProvisionInstructorInput,
    ProvisionInstructorResult,
    ProvisionInstructorSummary,
)


def provision_instructor(
    *,
    repo: InstructorProvisioningRepositoryPort,
    identity_provider: InstructorIdentityProviderPort,
    request: ProvisionInstructorInput,
) -> ProvisionInstructorResult:
    email = request.instructor_email.strip().lower()
    if not email:
        return ProvisionInstructorResult(
            ok=False,
            error="instructorEmail is required.",
            error_code="VALIDATION_ERROR",
        )

    context = repo.get_pilot_provision_context(
        pilot_request_id=request.pilot_request_id
    )
    if context is None:
        return ProvisionInstructorResult(
            ok=False,
            error="Pilot request has not been provisioned with a course/class code.",
            error_code="NOT_PROVISIONED",
        )

    if email != context.instructor_email:
        return ProvisionInstructorResult(
            ok=False,
            error="Instructor email does not match pilot provision context.",
            error_code="EMAIL_MISMATCH",
        )

    try:
        identity = identity_provider.ensure_instructor_group_membership(
            email=email,
            create_user_if_missing=request.create_user_if_missing,
        )
    except ValueError as exc:
        return ProvisionInstructorResult(
            ok=False,
            error=str(exc),
            error_code="IDENTITY_ERROR",
        )

    membership, membership_created = repo.upsert_instructor_course_membership(
        pilot_request_id=context.pilot_request_id,
        instructor_email=email,
        instructor_user_id=identity.user_id,
        course_id=context.course_id,
        course_name=context.course_name,
        provisioned_by=request.provisioned_by,
        provisioning_correlation_id=request.provisioning_correlation_id,
    )
    if membership_created:
        repo.commit()

    return ProvisionInstructorResult(
        ok=True,
        summary=ProvisionInstructorSummary(
            pilot_request_id=context.pilot_request_id,
            course_id=context.course_id,
            course_name=context.course_name,
            instructor_email=email,
            user_created=identity.user_created,
            group_assigned=identity.group_assigned,
            instructor_user_id=identity.user_id,
            membership_created=membership_created,
            provisioned_by=membership.provisioned_by,
            provisioning_correlation_id=membership.provisioning_correlation_id,
            provisioned_at=membership.created_at
            if membership_created
            else datetime.now(UTC),
        ),
    )
