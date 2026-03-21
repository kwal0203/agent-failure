from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import (
    String,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from uuid import uuid4, UUID as PyUUID
from datetime import datetime


class Base(DeclarativeBase):
    pass


class SessionModel(Base):
    __tablename__ = "sessions"

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
