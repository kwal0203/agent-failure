"""HTTP route for injecting learner emails into a session runtime."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.contracts.src.schemas import ApiErrorEnvelope, EmailArtifact
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.email_classification.ports import (
    EmailMaliciousnessClassifierPort,
)
from apps.control_plane.src.application.runtime.errors import RuntimeClientError
from apps.control_plane.src.application.runtime.ports import RuntimeClientFactoryPort
from apps.control_plane.src.application.session_email.service import (
    InjectSessionEmailCommand,
    SessionEmailPolicyError,
    inject_session_email_for_session,
)
from apps.control_plane.src.application.session_query.errors import (
    ForbiddenErrorSessionQuery,
)
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    SessionObjectiveModel,
)
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
    SQLAlchemySessionRuntimeBindingRepository,
    SQLAlchemyTraceEventRepository,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import (
    get_email_maliciousness_classifier,
    get_runtime_client_factory,
)
from apps.control_plane.src.interfaces.http.errors import (
    api_error,
    forbidden,
    internal_error,
    session_not_found,
)
from apps.control_plane.src.interfaces.http.schemas import InjectSessionEmailResponse

logger = logging.getLogger(__name__)
router = APIRouter()


class _SessionEmailObjectiveStatus:
    def __init__(self, *, db: Session):
        self._db = db

    def is_malicious_email_injected_complete(self, *, session_id: UUID) -> bool:
        objective = (
            self._db.execute(
                select(SessionObjectiveModel).where(
                    SessionObjectiveModel.session_id == session_id,
                    SessionObjectiveModel.objective_key == "malicious_email_injected",
                )
            )
            .scalars()
            .one_or_none()
        )
        return bool(objective is not None and objective.status == "complete")


class _SessionEmailDeps:
    def __init__(self, *, db: Session):
        self._db = db
        self.metadata_repo = SQLAlchemySessionMetadataRepository(db=db)
        self.runtime_binding_repo = SQLAlchemySessionRuntimeBindingRepository(db=db)
        self.trace_repo = SQLAlchemyTraceEventRepository(db=db)
        self.outbox_repo = SQLAlchemyOutbox(db=db)
        self.objective_status = _SessionEmailObjectiveStatus(db=db)
        self.tx = db


@router.post(
    "/api/v1/sessions/{session_id}/inbox/email",
    status_code=202,
    response_model=InjectSessionEmailResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
        409: {"model": ApiErrorEnvelope},
        502: {"model": ApiErrorEnvelope},
    },
)
async def inject_session_email(
    request: EmailArtifact,
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    runtime_client_factory: RuntimeClientFactoryPort = Depends(
        get_runtime_client_factory
    ),
    email_classifier: EmailMaliciousnessClassifierPort = Depends(
        get_email_maliciousness_classifier
    ),
    db: Session = Depends(get_db_session),
) -> InjectSessionEmailResponse | JSONResponse:
    try:
        result = await inject_session_email_for_session(
            command=InjectSessionEmailCommand(
                session_id=session_id,
                principal=principal,
                email_from=request.email_from,
                email_subject=request.email_subject,
                email_body=request.email_body,
                email_id=request.email_id,
                source=request.source,
            ),
            deps=_SessionEmailDeps(db=db),
            runtime_client_factory=runtime_client_factory,
            email_classifier=email_classifier,
        )
        if result is None:
            return session_not_found(str(session_id))
        return InjectSessionEmailResponse(session_id=result.session_id)

    except ForbiddenErrorSessionQuery as exc:
        return forbidden(exc.message, exc.details)
    except SessionEmailPolicyError as exc:
        db.rollback()
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            status_code=exc.status_code,
            details=exc.details,
        )

    except RuntimeClientError as exc:
        db.rollback()
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            status_code=502,
            details={"session_id": str(session_id)},
        )
    except RuntimeError as exc:
        db.rollback()
        return api_error(
            code="EMAIL_CLASSIFICATION_FAILED",
            message=str(exc),
            retryable=True,
            status_code=502,
            details={"session_id": str(session_id)},
        )
    except Exception:
        db.rollback()
        logger.exception("inject session email failed")
        return internal_error(
            "Unexpected server error", details={"session_id": str(session_id)}
        )
