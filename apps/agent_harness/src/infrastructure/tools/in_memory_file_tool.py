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

DEFAULT_FILE_SEED: dict[str, str] = {
    OPS_RUNBOOK_PATH: OPS_RUNBOOK_CONTENT,
}


class InMemoryFileTool(FileToolPort):
    def __init__(self, files: dict[str, str] | None = None) -> None:
        self._files: dict[str, str] = (
            dict(DEFAULT_FILE_SEED) if files is None else dict(files)
        )

    def read_file(self, path: str) -> ReadFileResult:
        content = self._files.get(path)
        if content is None:
            return ReadFileResult(content=None, error_code="FILE_NOT_FOUND")
        return ReadFileResult(content=content, error_code=None)

    def delete_file(self, path: str) -> DeleteFileResult:
        existed = path in self._files
        if existed:
            del self._files[path]
        return DeleteFileResult(deleted=existed, exists_after=(path in self._files))
