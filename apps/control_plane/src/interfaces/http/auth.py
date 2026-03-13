from dataclasses import dataclass
from uuid import UUID, uuid4
from fastapi import Header


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    role: str


class UnauthenticatedError(Exception):
    pass


def get_current_principal(
    authorization: str = Header(..., alias="Authorization"),
) -> Principal:
    if not authorization.startswith("Bearer "):
        raise UnauthenticatedError()

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise UnauthenticatedError()

    return Principal(user_id=uuid4(), role="learner")
