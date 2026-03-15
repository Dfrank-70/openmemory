from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.config.settings import get_logger, get_settings, iso_now, iter_markdown_files, slugify
from src.processing.classifier import ClassificationResult, classify_text
from src.storage.chroma_client import get_chroma_client
from src.storage.git_ops import get_git_ops


@dataclass(slots=True)
class IngestedDocument:
    path: Path
    created: bool
    content_hash: str
    classification: ClassificationResult


def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def _extract_content_hash(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    match = re.search(r"^content_hash:\s*([a-f0-9]{64})$", text, flags=re.MULTILINE)
    return match.group(1) if match else None


def find_duplicate_document(content_hash: str) -> Path | None:
    settings = get_settings()
    for path in iter_markdown_files(settings.kb_dir):
        if _extract_content_hash(path) == content_hash:
            return path
    return None


def _known_wikilinks() -> dict[str, str]:
    settings = get_settings()
    mapping: dict[str, str] = {}
    for path in iter_markdown_files(settings.kb_dir):
        mapping[path.stem.lower()] = path.stem
    return mapping


def apply_wiki_links(text: str, entities: list[str]) -> str:
    linked_text = text
    mapping = _known_wikilinks()
    for entity in entities:
        slug = slugify(entity)
        if slug not in mapping:
            continue
        pattern = re.compile(rf"(?<!\[\[){re.escape(entity)}(?!\]\])")
        linked_text = pattern.sub(f"[[{mapping[slug]}]]", linked_text)
    return linked_text


def _target_directory(scope: str, item_type: str, source: str) -> Path:
    settings = get_settings()
    if source == "email":
        return settings.email_dir(scope, item_type)
    return settings.note_dir(scope)


def _render_frontmatter(metadata: dict[str, Any]) -> str:
    return yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True).strip()


def _render_summary_section(classification: ClassificationResult) -> str:
    action_items = classification.action_items or ["nessuno"]
    lines = [
        "## Estratto automatico",
        f"- **Riassunto**: {classification.summary}",
        f"- **Tipo**: {classification.item_type}",
        f"- **Scope**: {classification.scope}",
        f"- **Entità**: {', '.join(classification.entities) if classification.entities else 'nessuna'}",
        f"- **Action item**: {'; '.join(action_items)}",
    ]
    return "\n".join(lines)


def render_markdown_document(
    original_text: str,
    classification: ClassificationResult,
    source: str,
    content_hash: str,
    extra_metadata: dict[str, Any] | None = None,
) -> str:
    body_text = apply_wiki_links(original_text.strip(), classification.entities)
    metadata: dict[str, Any] = {
        "date": iso_now(),
        "type": classification.item_type,
        "scope": classification.scope,
        "tags": classification.tags,
        "entities": classification.entities,
        "source": source,
        "content_hash": content_hash,
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    frontmatter = _render_frontmatter(metadata)
    summary = _render_summary_section(classification)
    return f"---\n{frontmatter}\n---\n\n{body_text}\n\n{summary}\n"


def _build_filename(classification: ClassificationResult, content_hash: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    summary_slug = slugify(classification.summary)[:48]
    return f"{timestamp}-{classification.item_type}-{summary_slug or content_hash[:8]}.md"


def ingest_text_content(
    text: str,
    source: str = "cli",
    prompt_name: str = "classify_note.txt",
    forced_scope: str | None = None,
    forced_type: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> IngestedDocument:
    logger = get_logger("pipeline")
    content_hash = compute_content_hash(text)
    duplicate = find_duplicate_document(content_hash)
    if duplicate:
        classification = classify_text(text, prompt_name=prompt_name, forced_scope=forced_scope, forced_type=forced_type)
        logger.info("duplicate_document path=%s", duplicate)
        return IngestedDocument(path=duplicate, created=False, content_hash=content_hash, classification=classification)

    classification = classify_text(text, prompt_name=prompt_name, forced_scope=forced_scope, forced_type=forced_type)
    target_dir = _target_directory(classification.scope, classification.item_type, source)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / _build_filename(classification, content_hash)
    markdown = render_markdown_document(
        original_text=text,
        classification=classification,
        source=source,
        content_hash=content_hash,
        extra_metadata=extra_metadata,
    )
    path.write_text(markdown, encoding="utf-8")

    metadata = {
        "path": str(path.relative_to(get_settings().open_memory_home)),
        "scope": classification.scope,
        "type": classification.item_type,
        "entities": classification.entities,
        "tags": classification.tags,
        "content_hash": content_hash,
        "source": source,
    }
    get_chroma_client().upsert_document(path=path, text=markdown, metadata=metadata)
    get_git_ops().commit_paths([path], f"ingest {classification.item_type}: {classification.summary[:72]}")
    logger.info("document_ingested path=%s type=%s", path, classification.item_type)
    return IngestedDocument(path=path, created=True, content_hash=content_hash, classification=classification)
