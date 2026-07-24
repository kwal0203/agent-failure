"""Public orchestration use cases.

The worker entry points stay stable here while each lifecycle concern is handled
by a focused module. Keeping this facade also makes policy injection explicit
without coupling callers to handler implementation details.
"""

import time

from apps.control_plane.src.application.session_lifecycle.ports import UnitOfWork
from apps.control_plane.src.application.session_lifecycle.service import (
    transition_session,
)

from .cleanup import process_cleanup_batch
from .expiry import process_expiry_batch
from .policy import CleanupPolicy, ExpiryPolicy, ProvisioningPolicy
from .ports import (
    ExpirySessionPort,
    ProcessCleanupOnceUnitOfWork,
    ProcessPendingOnceUnitOfWork,
    ReconciliationSessionQueryPort,
    RuntimeImageResolverPort,
    RuntimeInspectorPort,
    RuntimeProvisionerPort,
    RuntimeTeardownPort,
)
from .provisioning import process_provisioning_batch
from .reconciliation import process_reconciliation_batch
from .types import (
    ExpiryOnceResult,
    ProcessCleanupOnceResult,
    ProcessPendingOnceResult,
    ReconciliationOnceResult,
)


def process_pending_once(
    uow: ProcessPendingOnceUnitOfWork,
    image_resolver: RuntimeImageResolverPort,
    provisioner: RuntimeProvisionerPort,
    runtime_inspector: RuntimeInspectorPort,
    *,
    policy: ProvisioningPolicy | None = None,
) -> ProcessPendingOnceResult:
    return process_provisioning_batch(
        uow=uow,
        image_resolver=image_resolver,
        provisioner=provisioner,
        runtime_inspector=runtime_inspector,
        policy=policy or ProvisioningPolicy(),
        transition=transition_session,
        monotonic=time.monotonic,
        sleep=time.sleep,
    )


def process_cleanup_pending_once(
    uow: ProcessCleanupOnceUnitOfWork,
    teardown: RuntimeTeardownPort,
    *,
    policy: CleanupPolicy | None = None,
) -> ProcessCleanupOnceResult:
    return process_cleanup_batch(
        uow=uow,
        teardown=teardown,
        policy=policy or CleanupPolicy(),
    )


def process_reconciliation_once(
    session_query_repo: ReconciliationSessionQueryPort,
    uow: UnitOfWork,
    inspector: RuntimeInspectorPort,
) -> ReconciliationOnceResult:
    return process_reconciliation_batch(
        session_query_repo=session_query_repo,
        uow=uow,
        inspector=inspector,
        transition=transition_session,
    )


def process_expiry_once(
    session_query_repo: ExpirySessionPort,
    uow: UnitOfWork,
    *,
    policy: ExpiryPolicy | None = None,
) -> ExpiryOnceResult:
    return process_expiry_batch(
        session_query_repo=session_query_repo,
        uow=uow,
        policy=policy or ExpiryPolicy(),
        transition=transition_session,
    )
