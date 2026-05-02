"""Compatibility router that aggregates session route modules."""

from fastapi import APIRouter

from apps.control_plane.src.interfaces.http.routes.session_actions import (
    router as session_actions_router,
)
from apps.control_plane.src.interfaces.http.routes.session_create import (
    router as session_create_router,
)
from apps.control_plane.src.interfaces.http.routes.session_email import (
    router as session_email_router,
)
from apps.control_plane.src.interfaces.http.routes.session_explanations import (
    router as session_explanations_router,
)
from apps.control_plane.src.interfaces.http.routes.session_queries import (
    router as session_queries_router,
)

router = APIRouter()
router.include_router(session_create_router)
router.include_router(session_actions_router)
router.include_router(session_queries_router)
router.include_router(session_email_router)
router.include_router(session_explanations_router)
