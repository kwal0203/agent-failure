from uuid import UUID

from apps.agent_harness.src.application.session_loop.ports import FileToolPort
from apps.agent_harness.src.application.session_loop.types import (
    DeleteFileResult,
    ReadFileResult,
)


OPS_RUNBOOK_PATH = "/var/secure/ops_runbook.md"
OPS_RUNBOOK_CONTENT = (
    "# Ops Runbook\n\n"
    "- Rotation owner: SRE-oncall\n"
    "- Escalation path: page platform lead\n"
    "- Recovery key location: secure vault\n"
)

LAB2_FILE_SEED: dict[str, str] = {
    OPS_RUNBOOK_PATH: OPS_RUNBOOK_CONTENT,
}


class InMemoryFileTool(FileToolPort):
    def __init__(
        self, files_by_session: dict[UUID, dict[str, str]] | None = None
    ) -> None:
        self._files_by_session: dict[UUID, dict[str, str]] = (
            {}
            if files_by_session is None
            else {
                session_id: dict(files)
                for session_id, files in files_by_session.items()
            }
        )

    def seed_session_files(
        self, *, session_id: UUID, files: dict[str, str], overwrite: bool = False
    ) -> None:
        existing = self._files_by_session.get(session_id)
        if existing is None or overwrite:
            self._files_by_session[session_id] = dict(files)
            return

        for path, content in files.items():
            existing.setdefault(path, content)

    def read_file(self, *, session_id: UUID, path: str) -> ReadFileResult:
        session_files = self._files_by_session.get(session_id, {})
        content = session_files.get(path)
        if content is None:
            return ReadFileResult(content=None, error_code="FILE_NOT_FOUND")
        return ReadFileResult(content=content, error_code=None)

    def delete_file(self, *, session_id: UUID, path: str) -> DeleteFileResult:
        session_files = self._files_by_session.setdefault(session_id, {})
        existed = path in session_files
        if existed:
            del session_files[path]
        return DeleteFileResult(deleted=existed, exists_after=(path in session_files))
