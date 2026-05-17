from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

import sqlalchemy as sa


def test_session_report_evidence_migration_upgrade_creates_table_constraints_and_indexes() -> (
    None
):
    migration_path = (
        Path(__file__).resolve().parents[5]
        / "alembic"
        / "versions"
        / "7f3c2a1d9b50_add_session_report_evidence_table.py"
    )
    spec = spec_from_file_location("session_report_evidence_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)

    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    class FakeOp:
        def create_table(self, *args: Any, **kwargs: Any) -> None:
            calls.append(("create_table", args, kwargs))

        def create_index(self, *args: Any, **kwargs: Any) -> None:
            calls.append(("create_index", args, kwargs))

    setattr(migration, "op", FakeOp())
    migration.upgrade()

    create_table_calls = [call for call in calls if call[0] == "create_table"]
    assert len(create_table_calls) == 1
    table_call = create_table_calls[0]
    assert table_call[1][0] == "session_report_evidence"

    table_args = table_call[1][1:]
    constraint_names = {
        getattr(arg, "name", None)
        for arg in table_args
        if isinstance(arg, sa.CheckConstraint | sa.UniqueConstraint)
    }
    assert "ck_session_report_evidence_type" in constraint_names
    assert "ck_session_report_evidence_default_priority" in constraint_names
    assert "uq_session_report_evidence_session_id_event_id" in constraint_names

    create_index_calls = [call for call in calls if call[0] == "create_index"]
    created_index_names = {call[1][0] for call in create_index_calls}
    assert "ix_session_report_evidence_session_id" in created_index_names
    assert "ix_session_report_evidence_event_id" in created_index_names
