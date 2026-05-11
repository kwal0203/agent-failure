from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CourseSummary:
    id: str
    name: str


@dataclass(frozen=True)
class ValidateClassCodeResult:
    valid: bool
    enrollment_token: str | None = None
    expires_in_seconds: int | None = None
    course: CourseSummary | None = None
    error: str | None = None


@dataclass(frozen=True)
class RedeemEnrollmentResult:
    enrolled: bool
    course: CourseSummary | None = None
    error: str | None = None


@dataclass(frozen=True)
class ClassCodeRecord:
    code: str
    course_id: str
    course_name: str
    expires_at: datetime | None
    max_uses: int | None
    uses: int
    status: str


@dataclass(frozen=True)
class EnrollmentTokenRecord:
    nonce: str
    email: str
    course_id: str
    course_name: str
    expires_at: datetime
    redeemed_at: datetime | None
