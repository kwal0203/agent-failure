from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import (
    String,
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
    state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    last_transition_actor: Mapped[str] = mapped_column(String(32), nullable=False)
    last_transition_reason: Mapped[str | None] = mapped_column(
        String(32), nullable=True
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

    idempotency_key: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
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
    idempotency_key: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
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
