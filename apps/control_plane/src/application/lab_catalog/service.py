from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.common.ports import LabRepository
from apps.control_plane.src.application.common.errors import ForbiddenError

from .types import GetLabsForPrincipalResult, GetLabsItemResult, GetLabsCapabilities


def get_labs_for_principal(
    principal: PrincipalContext, lab_repo: LabRepository
) -> GetLabsForPrincipalResult:
    if principal.role not in {"learner", "admin"}:
        raise ForbiddenError(role=principal.role)

    lab_rows = lab_repo.get_lab_catalog()
    labs: list[GetLabsItemResult] = []
    for lab in lab_rows:
        lab_id = lab.lab_id
        slug = lab.slug
        name = lab.name
        summary = lab.summary

        supports_resume = lab.supports_resume
        supports_uploads = lab.supports_uploads

        labs.append(
            GetLabsItemResult(
                lab_id=lab_id,
                slug=slug,
                name=name,
                summary=summary,
                capabilities=GetLabsCapabilities(
                    supports_resume=supports_resume, supports_uploads=supports_uploads
                ),
            )
        )

    return GetLabsForPrincipalResult(labs=labs)
