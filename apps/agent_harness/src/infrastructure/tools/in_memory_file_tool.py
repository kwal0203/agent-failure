from apps.agent_harness.src.application.session_loop.ports import FileToolPort
from apps.agent_harness.src.application.session_loop.types import DeleteFileResult


class InMemoryFileTool(FileToolPort):
    def __init__(self, files: dict[str, str] | None = None) -> None:
        self._files: dict[str, str] = dict(files or {})

    def read_file(self, path: str) -> str | None:
        return self._files.get(path)

    def delete_file(self, path: str) -> DeleteFileResult:
        existed = path in self._files
        if existed:
            del self._files[path]
        return DeleteFileResult(deleted=existed, exists_after=(path in self._files))
