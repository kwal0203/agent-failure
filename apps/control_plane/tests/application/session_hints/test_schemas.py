from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from apps.control_plane.src.application.session_hints.schemas import (
    HintUnlockedEventPayload,
)


def test_hint_unlocked_payload_accepts_valid_shape() -> None:
    payload = HintUnlockedEventPayload(
        session_id=uuid4(),
        hint_key="Hint_1",
        text="Ask what tools are available.",
        sort_order=0,
        unlocked_at=datetime.now(timezone.utc),
        idempotency_key="hint_unlock:abc",
    )
    assert payload.hint_key == "hint_1"


def test_hint_unlocked_payload_rejects_invalid_hint_key() -> None:
    with pytest.raises(ValidationError):
        HintUnlockedEventPayload(
            session_id=uuid4(),
            hint_key="hint-1",
            text="x",
            sort_order=0,
            unlocked_at=datetime.now(timezone.utc),
            idempotency_key="hint_unlock:abc",
        )


def test_hint_unlocked_payload_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        HintUnlockedEventPayload(
            session_id=uuid4(),
            hint_key="hint_1",
            text="   ",
            sort_order=0,
            unlocked_at=datetime.now(timezone.utc),
            idempotency_key="hint_unlock:abc",
        )


def test_hint_unlocked_payload_rejects_negative_sort_order() -> None:
    with pytest.raises(ValidationError):
        HintUnlockedEventPayload(
            session_id=uuid4(),
            hint_key="hint_1",
            text="x",
            sort_order=-1,
            unlocked_at=datetime.now(timezone.utc),
            idempotency_key="hint_unlock:abc",
        )
