from __future__ import annotations

from pathlib import Path


class WorkspaceAccessError(ValueError):
    """Raised when a tool attempts to access a path outside the arena workspace."""


class FileMCPServer:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.resolve()

    def read(self, path: str) -> dict[str, str]:
        target = self._resolve_inside(path)
        if not target.is_file():
            raise FileNotFoundError(f"arena file not found: {path}")
        return {"path": self._display_path(target), "content": target.read_text(encoding="utf-8")}

    def write(self, path: str, content: str) -> dict[str, str | int]:
        target = self._resolve_inside(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": self._display_path(target), "bytes": len(content.encode("utf-8"))}

    def _resolve_inside(self, path: str) -> Path:
        candidate = (self.workspace / path).resolve()
        try:
            candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise WorkspaceAccessError(f"path escapes arena workspace: {path}") from exc
        return candidate

    def _display_path(self, path: Path) -> str:
        return path.relative_to(self.workspace).as_posix()
