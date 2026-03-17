from typing import Protocol
from .types import ProvisionResult, RuntimeProvisionRequest


class RuntimeProvisionerPort(Protocol):
    def provision(self, request: RuntimeProvisionRequest) -> ProvisionResult: ...
