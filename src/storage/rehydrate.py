from __future__ import annotations

from pathlib import Path

from src.config.settings import get_logger, get_settings, iter_markdown_files
from src.processing.pipeline import compute_content_hash
from src.storage.chroma_client import get_chroma_client


def _infer_scope(path: Path) -> str:
    if "personal" in path.parts:
        return "personal"
    if "work" in path.parts:
        return "work"
    return "all"


def _infer_type(path: Path) -> str:
    if "digests" in path.parts:
        return "digest"
    if "projects" in path.parts:
        return "project"
    if "emails" in path.parts:
        return "email"
    if "finance" in path.parts:
        return "finance_update"
    if path.name == "index.md":
        return "index"
    return "note"


def rehydrate_index() -> int:
    settings = get_settings()
    logger = get_logger("rehydrate")
    count = 0
    client = get_chroma_client()
    for path in iter_markdown_files(settings.kb_dir):
        content = path.read_text(encoding="utf-8")
        success = client.upsert_document(
            path=path,
            text=content,
            metadata={
                "path": str(path.relative_to(settings.open_memory_home)),
                "scope": _infer_scope(path),
                "type": _infer_type(path),
                "content_hash": compute_content_hash(content),
            },
        )
        if success:
            count += 1
    logger.info("rehydrate_completed count=%s", count)
    return count


if __name__ == "__main__":
    print(rehydrate_index())
