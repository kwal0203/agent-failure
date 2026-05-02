from uuid import UUID

from apps.control_plane.src.application.orchestrator.idempotency import (
    build_expired_provisioning_transition_idempotency_key,
    build_expired_session_transition_idempotency_key,
    build_provision_request_idempotency_key,
    build_provisioning_failed_transition_idempotency_key,
    build_provisioning_succeeded_transition_idempotency_key,
    build_reconcile_failed_runtime_transition_idempotency_key,
    build_reconcile_missing_runtime_transition_idempotency_key,
)
from apps.control_plane.src.application.session_lifecycle.idempotency import (
    build_stop_session_transition_idempotency_key,
)
from apps.control_plane.src.application.session_stream.idempotency import (
    build_turn_idempotency_key,
)


def test_build_turn_idempotency_key_is_stable() -> None:
    session_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    turn_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    key = build_turn_idempotency_key(session_id=session_id, turn_id=turn_id)

    assert (
        key
        == "turn:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    )


def test_build_stop_session_transition_idempotency_key_is_stable() -> None:
    session_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    requester_user_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")

    key = build_stop_session_transition_idempotency_key(
        session_id=session_id, requester_user_id=requester_user_id
    )

    assert (
        key == "stop-session:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:"
        "cccccccc-cccc-cccc-cccc-cccccccccccc"
    )


def test_orchestrator_idempotency_keys_use_expected_prefixes_and_state_normalization() -> (
    None
):
    session_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    outbox_event_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")

    assert (
        build_provision_request_idempotency_key(
            session_id=session_id, outbox_event_id=outbox_event_id
        )
        == "provision:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:dddddddd-dddd-dddd-dddd-dddddddddddd"
    )
    assert (
        build_provisioning_succeeded_transition_idempotency_key(
            session_id=session_id, outbox_event_id=outbox_event_id
        )
        == "provisioning:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:dddddddd-dddd-dddd-dddd-dddddddddddd:succeeded"
    )
    assert (
        build_provisioning_failed_transition_idempotency_key(
            session_id=session_id, outbox_event_id=outbox_event_id
        )
        == "provisioning:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:dddddddd-dddd-dddd-dddd-dddddddddddd:failed"
    )
    assert (
        build_reconcile_missing_runtime_transition_idempotency_key(
            session_id=session_id, state=" active "
        )
        == "reconcile:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:missing-runtime:ACTIVE"
    )
    assert (
        build_reconcile_failed_runtime_transition_idempotency_key(
            session_id=session_id, state=" active "
        )
        == "reconcile:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:failed-runtime:ACTIVE"
    )
    assert (
        build_expired_provisioning_transition_idempotency_key(
            session_id=session_id, state="active "
        )
        == "expiry:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:expired-provisioning:ACTIVE"
    )
    assert (
        build_expired_session_transition_idempotency_key(
            session_id=session_id, state="active "
        )
        == "expiry:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:expired-session:ACTIVE"
    )
