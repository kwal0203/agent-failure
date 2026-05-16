from datetime import datetime
from typing import Protocol
from uuid import UUID

from .types import CreatePilotRequestInput, PilotRequestRecord


class PilotRequestRepositoryPort(Protocol):
    def count_recent_by_work_email(
        self, *, work_email: str, since: datetime
    ) -> int: ...

    def count_recent_by_source_ip(self, *, source_ip: str, since: datetime) -> int: ...

    def exists_recent_duplicate(
        self, *, work_email: str, university: str, since: datetime
    ) -> bool: ...

    def create_pilot_request(
        self, request: CreatePilotRequestInput
    ) -> PilotRequestRecord: ...

    def list_pilot_requests(
        self,
        *,
        status: str | None,
        created_after: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[PilotRequestRecord, ...]: ...

    def get_pilot_request_by_id(
        self, *, request_id: UUID
    ) -> PilotRequestRecord | None: ...

    def update_pilot_request_status(
        self, *, request_id: UUID, status: str
    ) -> PilotRequestRecord | None: ...

    def commit(self) -> None: ...
