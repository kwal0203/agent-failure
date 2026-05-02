"""HTTP routes for session lifecycle and seen-state actions."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.contracts.src.schemas import ApiErrorEnvelope
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.session_feedback.service import (
    mark_session_feedback_seen,
)
from apps.control_plane.src.application.session_hints.service import (
    mark_session_hints_seen,
)
from apps.control_plane.src.application.session_lifecycle.errors import SessionNotFound
from apps.control_plane.src.application.session_lifecycle.service import (
    transition_session,
)
from apps.control_plane.src.application.session_query.ports import (
    SessionMetadataRepository,
)
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import Trigger
from apps.control_plane.src.infrastructure.persistence.db import (
    SessionFactory,
    get_db_session,
)
from apps.control_plane.src.infrastructure.persistence.session_feedback_repository import (
    SQLAlchemySessionFeedbackRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_hints_repository import (
    SQLAlchemySessionHintSeenRepository,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import (
    get_session_metadata_repository,
)
from apps.control_plane.src.interfaces.http.errors import session_not_found
from apps.control_plane.src.interfaces.http.schemas import (
    MarkSessionFeedbackSeenResponse,
    MarkSessionHintsSeenResponse,
    StopSessionResponse,
)
from apps.control_plane.src.interfaces.http.translators import (
    translate_mark_feedback_seen_error,
    translate_mark_hints_seen_error,
    translate_stop_session_error,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/api/v1/sessions/{session_id}/stop",
    status_code=202,
    response_model=StopSessionResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
        409: {"model": ApiErrorEnvelope},
        500: {"model": ApiErrorEnvelope},
    },
)
def stop_session_endpoint(
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    metadata_repo: SessionMetadataRepository = Depends(get_session_metadata_repository),
) -> StopSessionResponse | JSONResponse:
    try:
        session_metadata = get_session_metadata(
            session_id=session_id,
            principal=principal,
            repo=metadata_repo,
        )
        if session_metadata is None:
            return session_not_found(str(session_id))

        if session_metadata.state in {"COMPLETED", "FAILED", "EXPIRED", "CANCELLED"}:
            return StopSessionResponse(
                session_id=session_id,
                accepted=True,
                state=session_metadata.state,
            )

        uow = SQLAlchemyUnitOfWork(session_factory=SessionFactory)
        transition_session(
            session_id=session_id,
            trigger=Trigger.ADMIN_CANCELLED,
            actor="admin",
            metadata={
                "reason_code": "USER_REQUESTED_STOP",
                "requested_by_user_id": str(principal.user_id),
                "requested_via": "session_ui",
            },
            idempotency_key=f"stop-session:{session_id}:{principal.user_id}",
            uow=uow,
        )

        return StopSessionResponse(
            session_id=session_id,
            accepted=True,
            state="CANCELLED",
        )

    except SessionNotFound:
        return session_not_found(str(session_id))
    except Exception as exc:
        response = translate_stop_session_error(exc, session_id=session_id)
        if response.status_code == 500:
            logger.exception("stop session failed for session=%s", str(session_id))
        return response


@router.post(
    "/api/v1/sessions/{session_id}/hints/mark-seen",
    response_model=MarkSessionHintsSeenResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
    },
)
def mark_hints_seen_endpoint(
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> MarkSessionHintsSeenResponse | JSONResponse:
    seen_repo = SQLAlchemySessionHintSeenRepository(db=db)
    try:
        updated_count = mark_session_hints_seen(
            session_id=session_id,
            principal=principal,
            seen_repo=seen_repo,
        )
        db.commit()
        return MarkSessionHintsSeenResponse(
            session_id=session_id,
            updated_count=updated_count,
        )
    except Exception as exc:
        db.rollback()
        response = translate_mark_hints_seen_error(exc, session_id=session_id)
        if response.status_code == 500:
            logger.exception("mark hints seen failed")
        return response


@router.post(
    "/api/v1/sessions/{session_id}/feedback/mark-seen",
    response_model=MarkSessionFeedbackSeenResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
    },
)
def mark_feedback_seen_endpoint(
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> MarkSessionFeedbackSeenResponse | JSONResponse:
    feedback_repo = SQLAlchemySessionFeedbackRepository(db=db)
    try:
        updated_count = mark_session_feedback_seen(
            session_id=session_id,
            principal=principal,
            feedback_repo=feedback_repo,
        )
        db.commit()
        return MarkSessionFeedbackSeenResponse(
            session_id=session_id,
            updated_count=updated_count,
        )
    except Exception as exc:
        db.rollback()
        response = translate_mark_feedback_seen_error(exc, session_id=session_id)
        if response.status_code == 500:
            logger.exception("mark feedback seen failed")
        return response
