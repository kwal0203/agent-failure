from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import (
    String,
    Integer,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    func,
)
from uuid import uuid4, UUID as PyUUID
from datetime import datetime


class Base(DeclarativeBase):
    pass


class LabModel(Base):
    __tablename__ = "labs"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_labs_slug"),
        CheckConstraint("slug <> ''", name="ck_labs_slug_not_empty"),
        CheckConstraint("name <> ''", name="ck_labs_name_not_empty"),
        CheckConstraint(
            "catalog_order IS NULL OR catalog_order >= 0",
            name="ck_labs_catalog_order_non_negative",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    catalog_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    supports_resume: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    supports_uploads: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class LabVersionModel(Base):
    __tablename__ = "lab_versions"
    __table_args__ = (
        UniqueConstraint("lab_id", "version", name="uq_lab_versions_lab_id_version"),
        CheckConstraint("version <> ''", name="ck_lab_versions_version_not_empty"),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    lab_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("labs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SessionModel(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "lab_difficulty in ('easy', 'medium', 'hard')",
            name="ck_sessions_lab_difficulty",
        ),
        CheckConstraint(
            "completion_status in ('in_progress', 'completed_success', 'completed_failure')",
            name="ck_sessions_completion_status",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    lab_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    lab_version_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    owner_user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    runtime_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    runtime_substate: Mapped[str | None] = mapped_column(String(32), nullable=True)
    completion_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="in_progress", server_default="in_progress"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completion_reason_code: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    resume_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="hot_resume"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    last_transition_actor: Mapped[str] = mapped_column(String(32), nullable=False)
    last_transition_reason: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    # Add updated_at later on (can use it during reconciliation)
    # Add last_activity_at later on (cas use it during expiry)
    lab_difficulty: Mapped[str] = mapped_column(
        String(32), nullable=False, default="medium"
    )


class SessionTransitionEventModel(Base):
    __tablename__ = "session_transition_events"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "idempotency_key", name="uq_transition_session_idempo"
        ),
        CheckConstraint(
            "prev_state IN ('CREATED','PROVISIONING','ACTIVE','IDLE','COMPLETED','FAILED','EXPIRED','CANCELLED')",
            name="ck_prev_state",
        ),
        CheckConstraint(
            "next_state IN ('CREATED','PROVISIONING','ACTIVE','IDLE','COMPLETED','FAILED','EXPIRED','CANCELLED')",
            name="ck_next_state",
        ),
        CheckConstraint(
            "trigger in ('ADMIN_CANCELLED', 'LAUNCH_SUCCEEDED', 'LAUNCH_FAILED', 'PROVISIONING_SUCCEEDED', 'PROVISIONING_FAILED', 'PROVISIONING_MAX_TIME', 'IDLE_MAX_TIME', 'SESSION_MAX_TIME', 'RECONNECT', 'LAB_COMPLETED', 'LAB_FAILED', 'RUNTIME_FAILED')",
            name="ck_trigger",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    prev_state: Mapped[str] = mapped_column(String(32), nullable=False)
    next_state: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    event_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IdempotencyRecordModel(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "operation", "idempotency_key", name="uq_idempo_operation_key"
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    operation: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )

    session_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=True, index=True
    )

    transition_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("session_transition_events.id"),
        nullable=True,
        index=True,
    )

    response_payload: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OutboxEventModel(Base):
    __tablename__ = "outbox_events"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Domain event identity
    event_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    aggregate_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Event payload to replay/dispatch
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)

    # Dispatch lifecycle
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TraceEventModel(Base):
    __tablename__ = "trace_events"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "event_index", name="uq_trace_session_event_index"
        ),
        CheckConstraint(
            "family IN ('lifecycle', 'learner', 'runtime', 'tool', 'model')",
            name="ck_trace_family",
        ),
        CheckConstraint(
            "lab_difficulty IN ('easy', 'medium')",
            name="ck_trace_events_lab_difficulty",
        ),
    )

    event_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True
    )
    family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, server_default=func.now()
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    trace_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    correlation_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    request_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_user_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    lab_id: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    lab_version_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    lab_difficulty: Mapped[str] = mapped_column(
        String(32), nullable=True, default="medium"
    )


class SessionReportEvidenceModel(Base):
    __tablename__ = "session_report_evidence"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "event_id",
            name="uq_session_report_evidence_session_id_event_id",
        ),
        CheckConstraint(
            "evidence_type IN ('exploit_step', 'exploit_outcome', 'system_context', 'coaching_feedback', 'noise')",
            name="ck_session_report_evidence_type",
        ),
        CheckConstraint(
            "default_priority IN ('high', 'medium', 'low')",
            name="ck_session_report_evidence_default_priority",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True
    )
    event_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    trace_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    objective_keys: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_priority: Mapped[str] = mapped_column(String(16), nullable=False)
    student_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_section: Mapped[str] = mapped_column(
        String(64), nullable=False, default="unassigned", server_default="unassigned"
    )
    section_position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SessionReportDraftModel(Base):
    __tablename__ = "session_report_drafts"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            name="uq_session_report_drafts_session_id",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True
    )
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    threat_model: Mapped[str] = mapped_column(Text, nullable=False, default="")
    methodology: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evidence_and_results: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mitigations: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ClassCodeModel(Base):
    __tablename__ = "class_codes"
    __table_args__ = (
        CheckConstraint("code <> ''", name="ck_class_codes_code_not_empty"),
        CheckConstraint("course_id <> ''", name="ck_class_codes_course_id_not_empty"),
        CheckConstraint(
            "course_name <> ''", name="ck_class_codes_course_name_not_empty"
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    code: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    course_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    course_name: Mapped[str] = mapped_column(String(256), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uses: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", server_default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EnrollmentTokenModel(Base):
    __tablename__ = "enrollment_tokens"
    __table_args__ = (UniqueConstraint("nonce", name="uq_enrollment_tokens_nonce"),)

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    nonce: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    course_name: Mapped[str] = mapped_column(String(256), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EnrollmentModel(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("user_sub", "course_id", name="uq_enrollments_user_course"),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_sub: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    course_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    course_name: Mapped[str] = mapped_column(String(256), nullable=False)
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="class_code", server_default="class_code"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PilotRequestModel(Base):
    __tablename__ = "pilot_requests"
    __table_args__ = (
        CheckConstraint(
            "full_name <> ''", name="ck_pilot_requests_full_name_not_empty"
        ),
        CheckConstraint(
            "work_email <> ''", name="ck_pilot_requests_work_email_not_empty"
        ),
        CheckConstraint(
            "university <> ''", name="ck_pilot_requests_university_not_empty"
        ),
        CheckConstraint("status <> ''", name="ck_pilot_requests_status_not_empty"),
        CheckConstraint(
            "status IN ('new', 'contacted', 'approved', 'approved_provisioning_failed', 'rejected')",
            name="ck_pilot_requests_status",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    work_email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)
    university: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    course_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cohort_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="new", server_default="new"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PilotRequestProvisionModel(Base):
    __tablename__ = "pilot_request_provisions"
    __table_args__ = (
        UniqueConstraint(
            "pilot_request_id", name="uq_pilot_request_provisions_request_id"
        ),
        CheckConstraint(
            "course_id <> ''", name="ck_pilot_request_provisions_course_id_not_empty"
        ),
        CheckConstraint(
            "course_name <> ''",
            name="ck_pilot_request_provisions_course_name_not_empty",
        ),
        CheckConstraint(
            "class_code <> ''", name="ck_pilot_request_provisions_class_code_not_empty"
        ),
        CheckConstraint(
            "instructor_email <> ''",
            name="ck_pilot_request_provisions_instructor_email_not_empty",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    pilot_request_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    course_id: Mapped[str] = mapped_column(String(128), nullable=False)
    course_name: Mapped[str] = mapped_column(String(256), nullable=False)
    class_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    class_code_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    instructor_email: Mapped[str] = mapped_column(
        String(320), nullable=False, index=True
    )
    provisioned_by: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    provisioning_correlation_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class InstructorCourseMembershipModel(Base):
    __tablename__ = "instructor_course_memberships"
    __table_args__ = (
        UniqueConstraint(
            "instructor_email",
            "course_id",
            name="uq_instructor_course_memberships_email_course",
        ),
        CheckConstraint(
            "instructor_email <> ''",
            name="ck_instructor_course_memberships_email_not_empty",
        ),
        CheckConstraint(
            "course_id <> ''",
            name="ck_instructor_course_memberships_course_id_not_empty",
        ),
        CheckConstraint(
            "course_name <> ''",
            name="ck_instructor_course_memberships_course_name_not_empty",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    pilot_request_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    instructor_email: Mapped[str] = mapped_column(
        String(320), nullable=False, index=True
    )
    instructor_user_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    course_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    course_name: Mapped[str] = mapped_column(String(256), nullable=False)
    provisioned_by: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    provisioning_correlation_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EvaluatorResultModel(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_evaluation_results_idempo"),
        CheckConstraint(
            "lab_difficulty IN ('easy', 'medium')",
            name="ck_evaluation_results_lab_difficulty",
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(256), nullable=False, index=True
    )
    result_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_event_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trigger_start_event_index: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    trigger_end_event_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback_level: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    feedback_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    session_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True
    )
    lab_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    lab_version_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    lab_difficulty: Mapped[str] = mapped_column(
        String(32), nullable=False, default="medium"
    )
    evaluator_version: Mapped[int] = mapped_column(Integer, nullable=False)


class SessionRuntimeBindingModel(Base):
    __tablename__ = "session_runtime_bindings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('provisioning', 'ready', 'failed', 'terminated')",
            name="ck_session_runtime_binding_status",
        ),
        CheckConstraint(
            "status != 'ready' OR "
            "(base_url IS NOT NULL AND length(trim(base_url)) > 0)",
            name="ck_session_runtime_binding_ready_base_url",
        ),
    )

    session_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), primary_key=True
    )
    runtime_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_token_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class LearnerExplanationModel(Base):
    __tablename__ = "learner_explanations"
    __table_args__ = (
        CheckConstraint("source IN ('learner')", name="ck_learner_explanations_source"),
        CheckConstraint(
            "lab_difficulty IN ('easy', 'medium')",
            name="ck_learner_explanations_lab_difficulty",
        ),
        UniqueConstraint(
            "session_id", "idempotency_key", name="uq_learner_explanations_idempo"
        ),
    )

    explanation_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    explanation: Mapped[str] = mapped_column(String(2048), nullable=False)
    session_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True
    )
    lab_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    lab_version_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    lab_difficulty: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="medium"
    )
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="learner"
    )
    actor_user_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SessionObjectiveModel(Base):
    __tablename__ = "session_objectives"
    __table_args__ = (
        UniqueConstraint(
            "session_id", "objective_key", name="uq_session_objective_key"
        ),
        CheckConstraint(
            "status in ('pending', 'complete')", name="ck_session_objectives_status"
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    objective_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class LabObjectivesModel(Base):
    __tablename__ = "lab_objectives"
    __table_args__ = (
        UniqueConstraint(
            "lab_version_id", "objective_key", name="uq_lab_objectives_objective_key"
        ),
        UniqueConstraint(
            "lab_version_id", "sort_order", name="uq_lab_objectives_sort_order"
        ),
        CheckConstraint(
            "objective_key <> ''", name="ck_lab_objectives_objective_key_not_empty"
        ),
        CheckConstraint("label <> ''", name="ck_lab_objectives_label_not_empty"),
        CheckConstraint(
            "sort_order >= 0", name="ck_lab_objectives_sort_order_nonnegative"
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    lab_version_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    objective_key: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class LabHintTemplateModel(Base):
    __tablename__ = "lab_hint_templates"
    __table_args__ = (
        UniqueConstraint(
            "lab_version_id", "hint_key", name="uq_lab_hint_templates_version_key"
        ),
        UniqueConstraint(
            "lab_version_id", "sort_order", name="uq_lab_hint_templates_version_sort"
        ),
        CheckConstraint(
            "hint_key <> ''", name="ck_lab_hint_templates_hint_key_not_empty"
        ),
        CheckConstraint("text <> ''", name="ck_lab_hint_templates_text_not_empty"),
        CheckConstraint(
            "offset_seconds >= 0", name="ck_lab_hint_templates_offset_nonnegative"
        ),
        CheckConstraint(
            "sort_order >= 0", name="ck_lab_hint_templates_sort_nonnegative"
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    lab_version_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lab_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hint_key: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    offset_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SessionHintModel(Base):
    __tablename__ = "session_hints"
    __table_args__ = (
        UniqueConstraint("session_id", "hint_key", name="uq_session_hints_session_key"),
        CheckConstraint("hint_key <> ''", name="ck_session_hints_hint_key_not_empty"),
        CheckConstraint("text <> ''", name="ck_session_hints_text_not_empty"),
        CheckConstraint("sort_order >= 0", name="ck_session_hints_sort_nonnegative"),
        CheckConstraint(
            "status in ('pending', 'unlocked')", name="ck_session_hints_status"
        ),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hint_key: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unlock_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    unlocked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
    )


class SessionFeedbackModel(Base):
    __tablename__ = "session_feedback"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_session_feedback_idempotency_key"),
        CheckConstraint(
            "feedback_key <> ''", name="ck_session_feedback_feedback_key_not_empty"
        ),
        CheckConstraint(
            "reason_code <> ''", name="ck_session_feedback_reason_code_not_empty"
        ),
        CheckConstraint("message <> ''", name="ck_session_feedback_message_not_empty"),
        CheckConstraint(
            "severity in ('info', 'warning', 'error')",
            name="ck_session_feedback_severity",
        ),
        Index("ix_session_feedback_session_id_created_at", "session_id", "created_at"),
        Index("ix_session_feedback_session_id_seen_at", "session_id", "seen_at"),
    )

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feedback_key: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    trigger_event_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(256), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
