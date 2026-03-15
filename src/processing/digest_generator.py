from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from src.config.settings import get_logger, get_settings, iso_now, iter_markdown_files, load_prompt, slugify
from src.processing.openrouter_client import call_openrouter
from src.processing.pipeline import touch_processed_marker
from src.storage.chroma_client import get_chroma_client
from src.storage.git_ops import get_git_ops


def _git_recent_files() -> list[Path]:
    settings = get_settings()
    try:
        result = subprocess.run(
            ["git", "log", "--since=24 hours ago", "--name-only", "--pretty=format:"],
            cwd=settings.open_memory_home,
            capture_output=True,
            text=True,
            check=True,
        )
        files = []
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if stripped.endswith(".md"):
                candidate = settings.open_memory_home / stripped
                if candidate.exists() and settings.kb_dir in candidate.parents:
                    files.append(candidate)
        unique_files = sorted({path.resolve() for path in files})
        return [Path(path) for path in unique_files]
    except Exception:
        return []


def _collect_digest_input(paths: list[Path]) -> str:
    chunks: list[str] = []
    for path in paths:
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        chunks.append(f"# FILE: {path.relative_to(get_settings().open_memory_home)}\n{content[:4000]}")
    return "\n\n".join(chunks)


def _extract_action_items(content: str) -> list[str]:
    return [line.strip() for line in content.splitlines() if line.strip().startswith("- [ ]")]


def regenerate_index() -> Path:
    settings = get_settings()
    projects = sorted((settings.kb_dir / "work" / "projects").glob("*.md")) + sorted((settings.kb_dir / "personal" / "projects").glob("*.md"))
    digests = sorted((settings.kb_dir / "shared" / "digests").glob("*.md"))
    project_rows: list[str] = []
    decisions: list[str] = []
    action_items: list[str] = []
    recent_documents: list[str] = []

    for project in projects:
        content = project.read_text(encoding="utf-8")
        project_rows.append(f"| [[{project.stem}]] | attivo | sconosciuto | {project.stem} |")
        for line in content.splitlines():
            if line.strip().startswith("- [["):
                decisions.append(line.strip())

    for digest in digests[-5:]:
        content = digest.read_text(encoding="utf-8")
        action_items.extend(_extract_action_items(content))
        recent_documents.append(f"- {digest.stem} ({digest.name})")

    if not project_rows:
        project_rows.append("| - | - | - | - |")

    index_content = "\n".join(
        [
            "---",
            f"last_updated: {iso_now()}",
            "---",
            "",
            "# Open Memory — Stato corrente",
            "",
            "## Progetti attivi",
            "| Progetto | Stato | Ultimo aggiornamento | Note |",
            "|----------|-------|---------------------|------|",
            *project_rows,
            "",
            "## Ultime decisioni",
            *(decisions[-10:] or ["- Nessuna decisione recente"]),
            "",
            "## Action items aperti",
            *(action_items[-10:] or ["- [ ] Nessun action item aperto"]),
            "",
            "## Ultimi documenti",
            *(recent_documents[-10:] or ["- Nessun documento recente"]),
            "",
        ]
    )
    index_path = settings.kb_dir / "index.md"
    index_path.write_text(index_content, encoding="utf-8")
    touch_processed_marker(index_path)
    get_chroma_client().upsert_document(
        path=index_path,
        text=index_content,
        metadata={"path": "kb/index.md", "scope": "all", "type": "index", "content_hash": slugify(index_content[:120])},
    )
    return index_path


def generate_daily_digest(target_date: datetime | None = None) -> Path | None:
    logger = get_logger("digest")
    settings = get_settings()
    current_date = target_date or datetime.now(timezone.utc)
    changed_files = _git_recent_files()
    if not changed_files:
        changed_files = [path for path in iter_markdown_files(settings.kb_dir) if path.name != "index.md"][-20:]
    if not changed_files:
        logger.info("digest_skipped_no_files")
        return None
    llm_input = _collect_digest_input(changed_files)
    prompt = load_prompt("generate_digest.txt").format(input_text=llm_input[:20000])
    summary = call_openrouter(prompt) or "## Riassunto giornaliero\n\nNessun riassunto LLM disponibile."
    digest_path = settings.kb_dir / "shared" / "digests" / f"{current_date.date().isoformat()}.md"
    frontmatter = "\n".join(
        [
            "---",
            f"date: {current_date.date().isoformat()}",
            "type: digest",
            f"projects_touched: []",
            f"notes_count: 0",
            f"emails_count: 0",
            "---",
            "",
        ]
    )
    digest_path.write_text(frontmatter + summary.strip() + "\n", encoding="utf-8")
    touch_processed_marker(digest_path)
    get_chroma_client().upsert_document(
        path=digest_path,
        text=digest_path.read_text(encoding="utf-8"),
        metadata={"path": str(digest_path.relative_to(settings.open_memory_home)), "scope": "all", "type": "digest", "content_hash": digest_path.stem},
    )
    index_path = regenerate_index()
    get_git_ops().commit_paths([digest_path, index_path], f"digest: {digest_path.stem}")
    return digest_path


if __name__ == "__main__":
    generate_daily_digest()
