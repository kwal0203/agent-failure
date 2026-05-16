from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class MarkSessionHintsSeenResponse(BaseModel):
    session_id: UUID
    updated_count: int


class MarkSessionFeedbackSeenResponse(BaseModel):
    session_id: UUID
    updated_count: int


class StopSessionResponse(BaseModel):
    session_id: UUID
    accepted: bool = True
    state: str


class SessionResponse(BaseModel):
    id: UUID
    lab_id: UUID
    # TODO: Make lab_version_id non-null once lab version binding is implemented in create flow.
    lab_version_id: UUID | None
    lab_difficulty: str
    state: str
    resume_mode: str
    created_at: datetime


class CreateSessionResponse(BaseModel):
    session: SessionResponse


class CreateSessionRequest(BaseModel):
    lab_id: UUID
    lab_difficulty: str = "medium"


class InjectSessionEmailResponse(BaseModel):
    session_id: UUID
    email_id: str | None = None
    accepted: bool = True


class LearnerExplanationRequest(BaseModel):
    explanation: str = Field(min_length=20, max_length=2048)


class LearnerExplanationResponse(BaseModel):
    session_id: UUID
    explanation_id: UUID
    accepted: bool = True


class ValidateClassCodeRequest(BaseModel):
    classCode: str = Field(min_length=1, max_length=128)
    email: str = Field(min_length=3, max_length=320)


class CourseSummary(BaseModel):
    id: str
    name: str


class ValidateClassCodeResponse(BaseModel):
    valid: bool
    enrollmentToken: str | None = None
    expiresInSeconds: int | None = None
    course: CourseSummary | None = None
    error: str | None = None


class RedeemEnrollmentRequest(BaseModel):
    enrollmentToken: str = Field(min_length=1)


class RedeemEnrollmentResponse(BaseModel):
    enrolled: bool
    course: CourseSummary | None = None
    error: str | None = None


class CreatePilotRequest(BaseModel):
    fullName: str = Field(min_length=1, max_length=120)
    workEmail: str = Field(min_length=3, max_length=254)
    university: str = Field(min_length=1, max_length=160)
    role: str | None = Field(default=None, max_length=120)
    courseName: str | None = Field(default=None, max_length=120)
    cohortSize: int | None = Field(default=None, ge=1, le=100000)
    notes: str | None = Field(default=None, max_length=2000)


class CreatePilotRequestResponse(BaseModel):
    requestId: str
    status: str
    createdAt: datetime


class PilotRequestItemResponse(BaseModel):
    requestId: str
    fullName: str
    workEmail: str
    university: str
    role: str | None = None
    courseName: str | None = None
    cohortSize: int | None = None
    notes: str | None = None
    sourceIp: str | None = None
    status: str
    createdAt: datetime


class ListPilotRequestsResponse(BaseModel):
    items: list[PilotRequestItemResponse]
    limit: int
    offset: int


class UpdatePilotRequestStatusRequest(BaseModel):
    status: str = Field(min_length=1, max_length=32)


class ProvisionPilotRequestPayload(BaseModel):
    courseId: str = Field(min_length=1, max_length=128)
    courseName: str = Field(min_length=1, max_length=256)
    classCode: str = Field(min_length=1, max_length=128)
    instructorEmail: str = Field(min_length=3, max_length=320)
    maxUses: int | None = Field(default=None, ge=1)


class ProvisioningSummaryResponse(BaseModel):
    pilotRequestId: str
    courseId: str
    courseName: str
    classCode: str
    classCodeStatus: str
    classCodeMaxUses: int | None = None
    instructorEmail: str
    provisionedAt: datetime


class ProvisionPilotRequestResponse(BaseModel):
    created: bool
    provisioningSummary: ProvisioningSummaryResponse


class ProvisionInstructorRequest(BaseModel):
    pilotRequestId: str = Field(min_length=1)
    instructorEmail: str = Field(min_length=3, max_length=320)
    createUserIfMissing: bool = False


class InstructorProvisioningSummaryResponse(BaseModel):
    pilotRequestId: str
    courseId: str
    courseName: str
    instructorEmail: str
    userCreated: bool
    groupAssigned: bool
    membershipCreated: bool
    provisionedAt: datetime


class ProvisionInstructorResponse(BaseModel):
    provisioningSummary: InstructorProvisioningSummaryResponse
