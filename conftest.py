from pathlib import Path

import pytest


_DATABASE_FIXTURES = frozenset({"engine", "db_session", "uow"})


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Classify tests that require PostgreSQL as integration tests."""
    integration_marker = pytest.mark.integration
    for item in items:
        path_parts = Path(str(item.path)).parts
        fixture_names: tuple[str, ...] | list[str] = getattr(item, "fixturenames", ())
        uses_database_fixture = bool(_DATABASE_FIXTURES.intersection(fixture_names))
        if "integration" in path_parts or uses_database_fixture:
            item.add_marker(integration_marker)
