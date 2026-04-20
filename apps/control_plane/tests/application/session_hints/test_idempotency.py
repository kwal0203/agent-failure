from uuid import UUID

from apps.control_plane.src.application.session_hints.idempotency import (
    build_hint_unlock_idempotency_key,
)


def test_build_hint_unlock_idempotency_key_is_stable_and_normalized() -> None:
    session_id = UUID("12345678-1234-5678-1234-567812345678")

    key = build_hint_unlock_idempotency_key(session_id=session_id, hint_key=" Hint_1 ")

    assert key == "hint_unlock:12345678-1234-5678-1234-567812345678:hint_1"
