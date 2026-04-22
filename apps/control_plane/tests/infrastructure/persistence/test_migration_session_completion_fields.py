from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any


def test_completion_fields_migration_upgrade_includes_backfill_and_constraint() -> None:
    migration_path = (
        Path(__file__).resolve().parents[5]
        / "alembic"
        / "versions"
        / "aa4b2f6c1d9e_add_session_completion_fields.py"
    )
    spec = spec_from_file_location("session_completion_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)

    calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    class FakeOp:
        def add_column(self, *args: Any, **kwargs: Any) -> None:
            calls.append(("add_column", args, kwargs))

        def execute(self, *args: Any, **kwargs: Any) -> None:
            calls.append(("execute", args, kwargs))

        def alter_column(self, *args: Any, **kwargs: Any) -> None:
            calls.append(("alter_column", args, kwargs))

        def create_check_constraint(self, *args: Any, **kwargs: Any) -> None:
            calls.append(("create_check_constraint", args, kwargs))

    setattr(migration, "op", FakeOp())
    migration.upgrade()

    add_column_calls = [call for call in calls if call[0] == "add_column"]
    assert len(add_column_calls) == 3
    assert all(call[1][0] == "sessions" for call in add_column_calls)

    execute_calls = [call for call in calls if call[0] == "execute"]
    assert len(execute_calls) == 1
    assert (
        "UPDATE sessions SET completion_status = 'in_progress'"
        in execute_calls[0][1][0]
    )
    assert "WHERE completion_status IS NULL" in execute_calls[0][1][0]

    alter_calls = [call for call in calls if call[0] == "alter_column"]
    assert len(alter_calls) == 1
    assert alter_calls[0][1][0] == "sessions"
    assert alter_calls[0][1][1] == "completion_status"
    assert alter_calls[0][2]["nullable"] is False

    ck_calls = [call for call in calls if call[0] == "create_check_constraint"]
    assert len(ck_calls) == 1
    assert ck_calls[0][1][0] == "ck_sessions_completion_status"
    assert ck_calls[0][1][1] == "sessions"
    assert "completed_success" in ck_calls[0][1][2]
    assert "completed_failure" in ck_calls[0][1][2]
