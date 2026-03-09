from pydantic import BaseModel
from uuid import UUID


class PostgresIdempotencyStore(BaseModel):
    def get(self, key: UUID) -> object | None:
        return None

    def save(self, key: UUID, result: object) -> None:
        return None
