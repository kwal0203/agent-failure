from fastapi import FastAPI
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from pydantic import BaseModel


class HealthStatus(BaseModel):
    status: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/healthz", status_code=200)
def health_status() -> dict[str, str]:
    return HealthStatus(status="ok").model_dump(mode="json")
