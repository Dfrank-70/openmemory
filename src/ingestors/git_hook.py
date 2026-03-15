from __future__ import annotations

import os
import subprocess
from pathlib import Path

from src.config.settings import get_logger, get_settings, slugify
from src.processing.openrouter_client import call_openrouter
from src.storage.chroma_client import get_chroma_client
from src.storage.git_ops import get_git_ops


def _run(repo_path: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo_path, capture_output=True, text=True, check=False)
    return result.stdout.strip()


def _locate_project_file(repo_path: Path) -> Path | None:
    settings = get_settings()
    for base in [settings.kb_dir / "work" / "projects", settings.kb_dir / "personal" / "projects"]:
        for path in base.glob("*.md"):
            if f"repo: {repo_path}" in path.read_text(encoding="utf-8", errors="ignore"):
                return path
    return None


def summarize_commit(repo_path: Path) -> str:
    prompt = "\n\n".join(
        [
            _run(repo_path, "log", "-1", "--format=%H %s"),
            _run(repo_path, "diff", "HEAD~1", "--stat"),
            _run(repo_path, "diff", "HEAD~1")[:12000],
        ]
    )
    summary = call_openrouter(prompt)
    return summary or _run(repo_path, "log", "-1", "--format=%s")


def append_commit_summary(repo_path: str | Path) -> Path | None:
    logger = get_logger("git_hook")
    repo = Path(repo_path).expanduser().resolve()
    project_file = _locate_project_file(repo)
    if project_file is None:
        logger.warning("project_file_not_found repo=%s", repo)
        return None
    commit_hash = _run(repo, "log", "-1", "--format=%h")
    commit_date = _run(repo, "log", "-1", "--format=%cs")
    summary = summarize_commit(repo)
    addition = f"\n### {commit_date} — {commit_hash}\n{summary}\n"
    content = project_file.read_text(encoding="utf-8")
    if "## Change Log" in content:
        content = content.replace("## Change Log\n", f"## Change Log\n{addition}\n", 1)
    else:
        content += f"\n## Change Log\n{addition}\n"
    project_file.write_text(content, encoding="utf-8")
    get_chroma_client().upsert_document(
        path=project_file,
        text=content,
        metadata={"path": str(project_file.relative_to(get_settings().open_memory_home)), "scope": "work", "type": "project", "content_hash": slugify(content[:120])},
    )
    get_git_ops().commit_paths([project_file], f"project update: {project_file.stem} {commit_hash}")
    return project_file


def main() -> int:
    repo_path = Path(os.getcwd())
    append_commit_summary(repo_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
