from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from apps.contracts.src.schemas import (
    ApiErrorEnvelope,
    GetLabsResponse,
    LabCapabilitiesResponse,
    LabCatalogItemResponse,
)
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.lab_catalog import (
    service as lab_catalog_service,
)
from apps.control_plane.src.application.session_create.ports import LabRepository
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import get_lab_repository
from apps.control_plane.src.interfaces.http.error_mapping import (
    map_exception_to_http_response,
    map_unexpected_exception,
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
    lab_repo: LabRepository = Depends(get_lab_repository),
) -> GetLabsResponse | JSONResponse:
    try:
        labs_for_principal = lab_catalog_service.get_labs_for_principal(
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

    except Exception as exc:
        mapped = map_exception_to_http_response(exc)
        if mapped is not None:
            return mapped
        logger.exception(
            "get labs endpoint failed user_id=%s role=%s",
            str(principal.user_id),
            principal.role,
        )
        return map_unexpected_exception()
