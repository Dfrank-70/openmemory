from __future__ import annotations

import subprocess
from pathlib import Path

from src.config.settings import get_logger, get_settings


class GitOperations:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = get_logger("git")
        self.repo_root = self.settings.open_memory_home

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.repo_root,
            text=True,
            capture_output=True,
            check=check,
        )

    def ensure_repository(self) -> None:
        if (self.repo_root / ".git").exists():
            return
        self._run("init")

    def _to_relative_path(self, path: Path) -> str:
        resolved_repo_root = self.repo_root.resolve()
        resolved_path = path.expanduser().resolve(strict=False)
        return str(resolved_path.relative_to(resolved_repo_root))

    def commit_paths(self, paths: list[Path], message: str) -> bool:
        self.ensure_repository()
        relative_paths = [self._to_relative_path(path) for path in paths]
        if not relative_paths:
            return False
        try:
            self._run("add", "-A", "--", *relative_paths)
            diff = self._run("diff", "--cached", "--quiet", check=False)
            if diff.returncode == 0:
                return False
            self._run("commit", "-m", message)
            if self.settings.git_auto_push:
                self._run("push", "origin", "main", check=False)
            return True
        except Exception as exc:
            self.logger.warning("git_commit_failed error=%s", exc)
            return False


def get_git_ops() -> GitOperations:
    return GitOperations()
