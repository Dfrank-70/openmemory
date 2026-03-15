from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from src.config.settings import get_logger, get_settings, iso_now, slugify
from src.processing.pipeline import compute_content_hash, touch_processed_marker
from src.storage.chroma_client import get_chroma_client
from src.storage.git_ops import get_git_ops


def _run_git(repo_path: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo_path, capture_output=True, text=True, check=False)
    return result.stdout.strip()


def _first_existing(repo_path: Path, candidates: list[str]) -> Path | None:
    for candidate in candidates:
        path = repo_path / candidate
        if path.exists():
            return path
    return None


def _read_description(repo_path: Path) -> str:
    readme = _first_existing(repo_path, ["README.md", "readme.md", "README.txt"])
    if not readme:
        return "Da completare"
    text = readme.read_text(encoding="utf-8", errors="ignore")
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    return paragraphs[0][:400] if paragraphs else "Da completare"


def _detect_stack(repo_path: Path) -> list[str]:
    stack: list[str] = []
    if (repo_path / "requirements.txt").exists() or (repo_path / "pyproject.toml").exists():
        stack.append("Python")
    if (repo_path / "package.json").exists():
        stack.append("Node.js")
    if (repo_path / "Cargo.toml").exists():
        stack.append("Rust")
    if (repo_path / "go.mod").exists():
        stack.append("Go")
    if (repo_path / "docker-compose.yml").exists() or (repo_path / "Dockerfile").exists():
        stack.append("Docker")
    return stack or ["Da completare"]


def _directory_tree(repo_path: Path) -> str:
    lines: list[str] = []
    for item in sorted(repo_path.iterdir(), key=lambda value: value.name.lower()):
        if item.name.startswith("."):
            continue
        lines.append(item.name + ("/" if item.is_dir() else ""))
        if item.is_dir():
            for child in sorted(item.iterdir(), key=lambda value: value.name.lower())[:20]:
                if child.name.startswith("."):
                    continue
                lines.append(f"  - {child.name}" + ("/" if child.is_dir() else ""))
    return "\n".join(lines[:120])


def _project_markdown(name: str, repo_path: Path, scope: str) -> str:
    branch = _run_git(repo_path, "branch", "--show-current") or "unknown"
    last_commit_hash = _run_git(repo_path, "log", "-1", "--format=%h") or "unknown"
    last_commit_date = _run_git(repo_path, "log", "-1", "--format=%cs") or iso_now()[:10]
    last_commit_message = _run_git(repo_path, "log", "-1", "--format=%s") or "Nessun commit disponibile"
    tags = _run_git(repo_path, "tag", "-l").splitlines()
    commits = _run_git(repo_path, "log", "--oneline", "-20").splitlines()
    stack = _detect_stack(repo_path)
    description = _read_description(repo_path)
    changelog = "\n".join(f"### {line.split(' ', 1)[0]}\n{line.split(' ', 1)[1] if ' ' in line else line}" for line in commits[:20])
    restore_points = "\n".join(f"- **{tag}**" for tag in tags) if tags else "- Nessun tag disponibile"
    stack_markdown = "\n".join(f"- {item}" for item in stack)
    return "\n".join(
        [
            "---",
            f"name: {name}",
            f"scope: {scope}",
            "status: active",
            f"stack: {json.dumps(stack, ensure_ascii=False)}",
            f"repo: {repo_path}",
            f"registered: {iso_now()[:10]}",
            f"last_commit: {last_commit_date}",
            f"description: {json.dumps(description, ensure_ascii=False)}",
            f"content_hash: {compute_content_hash(str(repo_path) + last_commit_hash)}",
            "---",
            "",
            "## Stato attuale",
            f"Branch attivo: `{branch}`.",
            f"Ultimo commit: `{last_commit_hash}` — {last_commit_message}",
            "",
            "## Stack",
            stack_markdown,
            "",
            "## Change Log",
            changelog or "### Nessuna cronologia disponibile",
            "",
            "## Punti di ripristino",
            restore_points,
            "",
            "## Decisioni architetturali",
            "- Da derivare dai commit futuri",
            "",
            "## Struttura repository",
            "```text",
            _directory_tree(repo_path),
            "```",
            "",
        ]
    )


def install_hook(repo_path: Path) -> None:
    settings = get_settings()
    hook_target = repo_path / ".git" / "hooks" / "post-commit"
    hook_target.write_text(
        "\n".join(
            [
                "#!/bin/bash",
                "set -euo pipefail",
                f"export OPEN_MEMORY_HOME=\"{settings.open_memory_home}\"",
                f"export PYTHONPATH=\"{settings.root_dir}\"",
                "python3 -m src.ingestors.git_hook",
                "",
            ]
        ),
        encoding="utf-8",
    )
    hook_target.chmod(0o755)


def register_project(name: str, repo_path: str, scope: str = "work") -> Path:
    logger = get_logger("register_project")
    settings = get_settings()
    repo = Path(repo_path).expanduser().resolve()
    target_dir = settings.project_dir(scope)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{slugify(name)}.md"
    markdown = _project_markdown(name=name, repo_path=repo, scope=scope)
    target_path.write_text(markdown, encoding="utf-8")
    touch_processed_marker(target_path)
    install_hook(repo)
    get_chroma_client().upsert_document(
        path=target_path,
        text=markdown,
        metadata={"path": str(target_path.relative_to(settings.open_memory_home)), "scope": scope, "type": "project", "content_hash": compute_content_hash(markdown)},
    )
    get_git_ops().commit_paths([target_path], f"register project: {name}")
    logger.info("project_registered name=%s repo=%s", name, repo)
    return target_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Register a project in Open Memory")
    parser.add_argument("name")
    parser.add_argument("path")
    parser.add_argument("--scope", choices=["work", "personal"], default="work")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = register_project(name=args.name, repo_path=args.path, scope=args.scope)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
