from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import asyncio
import contextlib

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.control_plane.src.interfaces.http.auth import UnauthenticatedError
from apps.control_plane.src.interfaces.http.dependencies import (
    get_auth_verifier_config,
    get_token_verifier,
)
from apps.control_plane.src.interfaces.http.helpers import build_api_error_response
from apps.control_plane.src.interfaces.http.routes.health import router as health_router
from apps.control_plane.src.interfaces.http.routes.labs import router as labs_router
from apps.control_plane.src.interfaces.http.routes.metadata import (
    router as metadata_router,
)
from apps.control_plane.src.interfaces.http.routes.sessions import (
    router as sessions_router,
)
from apps.control_plane.src.interfaces.http.routes.ws_stream import (
    router as ws_stream_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.auth_verifier_config = get_auth_verifier_config()
    app.state.token_verifier = get_token_verifier()

    from apps.control_plane.src.interfaces.http import main as main_module

    app.state.learner_feedback_task = asyncio.create_task(
        main_module.run_forever(session_manager=main_module.ws_manager)
    )
    try:
        yield
    finally:
        task = app.state.learner_feedback_task
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(UnauthenticatedError)
async def handle_unauthenticated(
    request: Request, exc: UnauthenticatedError
) -> JSONResponse:
    _ = request, exc
    return build_api_error_response(
        "UNAUTHENTICATED", "Missing or invalid bearer token", False, 401
    )


app.include_router(sessions_router)
app.include_router(labs_router)
app.include_router(health_router)
app.include_router(metadata_router)
app.include_router(ws_stream_router)
