from typing import Protocol
from uuid import UUID

from .types import PilotProvisionRecord, ProvisionPilotRequestInput


class PilotProvisioningRepositoryPort(Protocol):
    def pilot_request_exists(self, *, request_id: UUID) -> bool: ...

    def get_provision_by_pilot_request_id(
        self, *, request_id: UUID
    ) -> PilotProvisionRecord | None: ...

    def create_or_get_provision(
        self, *, request: ProvisionPilotRequestInput
    ) -> tuple[PilotProvisionRecord, bool]: ...

    def commit(self) -> None: ...
