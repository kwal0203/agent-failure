from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from apps.control_plane.src.application.session_hints.service import (
    initialize_session_hints,
)
from apps.control_plane.src.application.session_hints.types import HintTemplate


class _FakeTemplateReader:
    def __init__(self, templates: list[HintTemplate]) -> None:
        self._templates = templates

    def list_hint_templates(self, lab_version_id):
        _ = lab_version_id
        return self._templates


class _IdempotentFakeHintWriter:
    def __init__(self) -> None:
        self.rows: dict[tuple[object, str], dict[str, object]] = {}

    def upsert_hint(
        self,
        *,
        session_id,
        hint_key,
        text,
        sort_order,
        unlock_at,
    ) -> None:
        self.rows[(session_id, hint_key)] = {
            "session_id": session_id,
            "hint_key": hint_key,
            "text": text,
            "sort_order": sort_order,
            "unlock_at": unlock_at,
        }


def test_initialize_session_hints_materializes_templates_with_unlock_schedule() -> None:
    session_id = uuid4()
    lab_version_id = uuid4()
    activated_at = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
    templates = [
        HintTemplate(
            hint_key="hint_1",
            text="h1",
            offset_seconds=90,
            sort_order=0,
        ),
        HintTemplate(
            hint_key="hint_2",
            text="h2",
            offset_seconds=210,
            sort_order=1,
        ),
    ]
    reader = _FakeTemplateReader(templates=templates)
    writer = _IdempotentFakeHintWriter()

    processed = initialize_session_hints(
        session_id=session_id,
        lab_version_id=lab_version_id,
        activated_at=activated_at,
        template_reader=reader,
        hint_writer=writer,
    )

    assert processed == 2
    assert len(writer.rows) == 2
    hint_1 = writer.rows[(session_id, "hint_1")]
    hint_2 = writer.rows[(session_id, "hint_2")]
    assert hint_1["unlock_at"] == datetime(2026, 4, 19, 12, 1, 30, tzinfo=timezone.utc)
    assert hint_2["unlock_at"] == datetime(2026, 4, 19, 12, 3, 30, tzinfo=timezone.utc)
    assert hint_1["sort_order"] == 0
    assert hint_2["sort_order"] == 1


def test_initialize_session_hints_replay_keeps_single_row_per_hint_with_idempotent_writer() -> (
    None
):
    session_id = uuid4()
    lab_version_id = uuid4()
    activated_at = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
    templates = [
        HintTemplate(
            hint_key="hint_1",
            text="h1",
            offset_seconds=90,
            sort_order=0,
        ),
        HintTemplate(
            hint_key="hint_2",
            text="h2",
            offset_seconds=210,
            sort_order=1,
        ),
    ]
    reader = _FakeTemplateReader(templates=templates)
    writer = _IdempotentFakeHintWriter()

    initialize_session_hints(
        session_id=session_id,
        lab_version_id=lab_version_id,
        activated_at=activated_at,
        template_reader=reader,
        hint_writer=writer,
    )
    initialize_session_hints(
        session_id=session_id,
        lab_version_id=lab_version_id,
        activated_at=activated_at,
        template_reader=reader,
        hint_writer=writer,
    )

    assert len(writer.rows) == 2
    assert (session_id, "hint_1") in writer.rows
    assert (session_id, "hint_2") in writer.rows
