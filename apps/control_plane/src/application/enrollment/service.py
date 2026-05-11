from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from apps.control_plane.src.application.common.types import PrincipalContext

from .ports import EnrollmentRepositoryPort
from .types import CourseSummary, RedeemEnrollmentResult, ValidateClassCodeResult


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def validate_class_code(
    *,
    repo: EnrollmentRepositoryPort,
    class_code: str,
    email: str,
    token_secret: str,
    token_ttl_seconds: int,
) -> ValidateClassCodeResult:
    code = class_code.strip()
    normalized_email = _normalize_email(email)
    now = _utc_now()

    row = repo.get_class_code(code)
    if row is None or row.status != "active":
        return ValidateClassCodeResult(
            valid=False, error="Invalid or expired class code"
        )

    if row.expires_at is not None and row.expires_at <= now:
        return ValidateClassCodeResult(
            valid=False, error="Invalid or expired class code"
        )

    if row.max_uses is not None and row.uses >= row.max_uses:
        return ValidateClassCodeResult(
            valid=False, error="Class code usage limit reached"
        )

    ttl = max(token_ttl_seconds, 60)
    expires_at = now + timedelta(seconds=ttl)
    nonce = uuid4().hex
    token_payload = {
        "jti": nonce,
        "courseId": row.course_id,
        "email": normalized_email,
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(token_payload, token_secret, algorithm="HS256")

    repo.create_enrollment_token(
        nonce=nonce,
        email=normalized_email,
        course_id=row.course_id,
        course_name=row.course_name,
        expires_at_epoch_sec=int(expires_at.timestamp()),
    )
    repo.increment_class_code_uses(code)
    repo.commit()

    return ValidateClassCodeResult(
        valid=True,
        enrollment_token=token,
        expires_in_seconds=ttl,
        course=CourseSummary(id=row.course_id, name=row.course_name),
    )


def redeem_enrollment(
    *,
    repo: EnrollmentRepositoryPort,
    principal: PrincipalContext,
    enrollment_token: str,
    token_secret: str,
) -> RedeemEnrollmentResult:
    now = _utc_now()

    try:
        claims = jwt.decode(enrollment_token, token_secret, algorithms=["HS256"])
    except Exception:
        return RedeemEnrollmentResult(enrolled=False, error="Invalid enrollment token")

    nonce = str(claims.get("jti") or "").strip()
    claimed_email = _normalize_email(str(claims.get("email") or ""))
    claimed_course_id = str(claims.get("courseId") or "").strip()
    if not nonce or not claimed_email or not claimed_course_id:
        return RedeemEnrollmentResult(enrolled=False, error="Invalid enrollment token")

    token_row = repo.get_enrollment_token(nonce)
    if token_row is None or token_row.expires_at <= now:
        return RedeemEnrollmentResult(
            enrolled=False,
            error="Token expired or already redeemed",
        )

    if token_row.redeemed_at is not None:
        if repo.is_user_enrolled(
            user_id=principal.user_id, course_id=token_row.course_id
        ):
            return RedeemEnrollmentResult(
                enrolled=True,
                course=CourseSummary(
                    id=token_row.course_id, name=token_row.course_name
                ),
            )
        return RedeemEnrollmentResult(
            enrolled=False,
            error="Token expired or already redeemed",
        )

    principal_email = _normalize_email(principal.email or "")
    if not principal_email or principal_email != claimed_email:
        return RedeemEnrollmentResult(
            enrolled=False,
            error="Enrollment token email does not match authenticated user",
        )

    if repo.is_user_enrolled(user_id=principal.user_id, course_id=token_row.course_id):
        repo.mark_enrollment_token_redeemed(nonce)
        repo.commit()
        return RedeemEnrollmentResult(
            enrolled=True,
            course=CourseSummary(id=token_row.course_id, name=token_row.course_name),
        )

    repo.create_enrollment(
        user_sub=str(principal.user_id),
        user_id=principal.user_id,
        email=principal_email,
        course_id=token_row.course_id,
        course_name=token_row.course_name,
    )
    repo.mark_enrollment_token_redeemed(nonce)
    repo.commit()

    return RedeemEnrollmentResult(
        enrolled=True,
        course=CourseSummary(id=token_row.course_id, name=token_row.course_name),
    )
