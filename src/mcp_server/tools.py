from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.config.settings import get_settings
from src.storage.chroma_client import get_chroma_client


def search_tool(query: str, scope: str = "all", item_type: str = "all", limit: int = 10) -> list[dict[str, Any]]:
    settings = get_settings()
    effective_scope = "work" if settings.profile == "work" and scope == "all" else scope
    results = get_chroma_client().search(query=query, scope=effective_scope, item_type=item_type, limit=limit)
    filtered: list[dict[str, Any]] = []
    for result in results:
        metadata = result.get("metadata", {})
        result_path = settings.open_memory_home / metadata.get("path", "")
        if result_path and result_path.exists() and settings.is_path_allowed(result_path):
            filtered.append(
                {
                    "path": metadata.get("path"),
                    "scope": metadata.get("scope"),
                    "type": metadata.get("type"),
                    "distance": result.get("distance"),
                    "content": result.get("document", "")[:2000],
                }
            )
    return filtered


def get_project_tool(name: str) -> str:
    settings = get_settings()
    candidate_names = [name, name.strip(), name.strip().lower().replace(" ", "-")]
    for candidate in candidate_names:
        for base_dir in [settings.kb_dir / "work" / "projects", settings.kb_dir / "personal" / "projects"]:
            path = base_dir / f"{candidate}.md"
            if path.exists() and settings.is_path_allowed(path):
                return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Project not found: {name}")


def _extract_section(markdown: str, heading: str) -> str | None:
    pattern = rf"(^##\s+{re.escape(heading)}\s*$)(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, markdown, flags=re.MULTILINE | re.DOTALL)
    if not match:
        return None
    return f"## {heading}\n{match.group(2).strip()}\n"


def get_context_tool(scope: str = "all") -> str:
    settings = get_settings()
    index_path = settings.kb_dir / "index.md"
    content = index_path.read_text(encoding="utf-8")
    if scope == "all":
        return content
    if scope == "work":
        sections = [
            _extract_section(content, "Progetti attivi"),
            _extract_section(content, "Ultime decisioni"),
            _extract_section(content, "Action items aperti"),
        ]
        return "\n\n".join(section for section in sections if section)
    if scope == "personal":
        sections = [
            _extract_section(content, "Action items aperti"),
            _extract_section(content, "Ultimi documenti"),
        ]
        return "\n\n".join(section for section in sections if section)
    return content
