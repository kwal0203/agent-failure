from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.contracts.src.schemas import ApiErrorEnvelope
from apps.control_plane.src.application.common.errors import ForbiddenError
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.lab_catalog.service import (
    get_labs_for_principal,
)
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.lab_repository import (
    SQLAlchemyLabRepository,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.errors import forbidden, internal_error
from apps.control_plane.src.interfaces.http.schemas import (
    GetLabsResponse,
    LabCapabilitiesResponse,
    LabCatalogItemResponse,
)

import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/api/v1/labs",
    response_model=GetLabsResponse,
    status_code=200,
    responses={401: {"model": ApiErrorEnvelope}, 403: {"model": ApiErrorEnvelope}},
)
def get_labs(
    principal: PrincipalContext = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> GetLabsResponse | JSONResponse:
    lab_repo = SQLAlchemyLabRepository(db=db)

    try:
        labs_for_principal = get_labs_for_principal(
            principal=principal, lab_repo=lab_repo
        ).labs

        result: list[LabCatalogItemResponse] = []
        for lab in labs_for_principal:
            result.append(
                LabCatalogItemResponse(
                    id=lab.lab_id,
                    slug=lab.slug,
                    name=lab.name,
                    summary=lab.summary,
                    capabilities=LabCapabilitiesResponse(
                        supports_resume=lab.capabilities.supports_resume,
                        supports_uploads=lab.capabilities.supports_uploads,
                    ),
                )
            )
        return GetLabsResponse(labs=result)

    except ForbiddenError as exc:
        return forbidden(exc.message, exc.details)
    except Exception:
        logger.exception(
            "get labs endpoint failed user_id=%s role=%s",
            str(principal.user_id),
            principal.role,
        )
        return internal_error()
