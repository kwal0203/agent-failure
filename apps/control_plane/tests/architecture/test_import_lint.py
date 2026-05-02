from pathlib import Path
import subprocess


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".importlinter").exists():
            return parent
    raise AssertionError("Could not locate repo root with .importlinter")


def test_import_linter_contracts_hold() -> None:
    result = subprocess.run(
        ["uv", "run", "lint-imports"],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Import-linter contract failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
