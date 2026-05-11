"""HTTP routes for class-code validation and enrollment redemption."""

from fastapi import APIRouter, Depends

from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.enrollment.ports import EnrollmentRepositoryPort
from apps.control_plane.src.application.enrollment.service import (
    redeem_enrollment as redeem_enrollment_service,
)
from apps.control_plane.src.application.enrollment.service import (
    validate_class_code as validate_class_code_service,
)
from apps.control_plane.src.infrastructure.config.settings import (
    EnrollmentSettings,
    get_enrollment_settings,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import (
    get_enrollment_repository,
)
from apps.control_plane.src.interfaces.http.schemas import (
    CourseSummary,
    RedeemEnrollmentRequest,
    RedeemEnrollmentResponse,
    ValidateClassCodeRequest,
    ValidateClassCodeResponse,
)

router = APIRouter()


@router.post("/api/v1/enrollment/validate-class-code")
def validate_class_code(
    request: ValidateClassCodeRequest,
    repo: EnrollmentRepositoryPort = Depends(get_enrollment_repository),
    settings: EnrollmentSettings = Depends(get_enrollment_settings),
) -> ValidateClassCodeResponse:
    result = validate_class_code_service(
        repo=repo,
        class_code=request.classCode,
        email=request.email,
        token_secret=settings.token_secret,
        token_ttl_seconds=settings.token_ttl_seconds,
    )

    return ValidateClassCodeResponse(
        valid=result.valid,
        enrollmentToken=result.enrollment_token,
        expiresInSeconds=result.expires_in_seconds,
        course=CourseSummary(id=result.course.id, name=result.course.name)
        if result.course is not None
        else None,
        error=result.error,
    )


@router.post("/api/v1/enrollment/redeem")
def redeem_enrollment(
    request: RedeemEnrollmentRequest,
    principal: PrincipalContext = Depends(get_current_principal),
    repo: EnrollmentRepositoryPort = Depends(get_enrollment_repository),
    settings: EnrollmentSettings = Depends(get_enrollment_settings),
) -> RedeemEnrollmentResponse:
    result = redeem_enrollment_service(
        repo=repo,
        principal=principal,
        enrollment_token=request.enrollmentToken,
        token_secret=settings.token_secret,
    )

    return RedeemEnrollmentResponse(
        enrolled=result.enrolled,
        course=CourseSummary(id=result.course.id, name=result.course.name)
        if result.course is not None
        else None,
        error=result.error,
    )
