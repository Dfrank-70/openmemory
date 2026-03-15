from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from src.config.settings import get_logger, load_prompt
from src.processing.openrouter_client import call_openrouter

ALLOWED_TYPES = {
    "thought",
    "decision",
    "idea",
    "task",
    "project_update",
    "finance_update",
    "contact",
    "meeting_note",
}
ALLOWED_SCOPES = {"work", "personal"}


@dataclass(slots=True)
class ClassificationResult:
    item_type: str
    scope: str
    entities: list[str]
    tags: list[str]
    action_items: list[str]
    summary: str

    def to_frontmatter(self) -> dict[str, Any]:
        return {
            "type": self.item_type,
            "scope": self.scope,
            "tags": self.tags,
            "entities": self.entities,
        }


def _default_summary(text: str) -> str:
    compact = " ".join(text.split())
    return compact[:180] if compact else "Contenuto non classificato"


def default_classification(text: str, forced_scope: str | None = None, forced_type: str | None = None) -> ClassificationResult:
    return ClassificationResult(
        item_type=forced_type or "unclassified",
        scope=forced_scope or "work",
        entities=[],
        tags=[],
        action_items=[],
        summary=_default_summary(text),
    )


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", stripped)
        stripped = re.sub(r"\n```$", "", stripped)
    return stripped.strip()


def _extract_json_blob(text: str) -> str:
    stripped = _strip_code_fences(text)
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found")
    return match.group(0)


def _normalize_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items
    return [str(value).strip()]


def _parse_response(response_text: str, text: str, forced_scope: str | None, forced_type: str | None) -> ClassificationResult:
    payload = json.loads(_extract_json_blob(response_text))
    item_type = forced_type or str(payload.get("type", "unclassified")).strip()
    scope = forced_scope or str(payload.get("scope", "work")).strip()
    entities = _normalize_list(payload.get("entities"))
    tags = _normalize_list(payload.get("tags"))[:5]
    action_items = _normalize_list(payload.get("action_items"))
    summary = str(payload.get("summary") or _default_summary(text)).strip()

    if item_type not in ALLOWED_TYPES:
        item_type = forced_type or "unclassified"
    if scope not in ALLOWED_SCOPES:
        scope = forced_scope or "work"

    return ClassificationResult(
        item_type=item_type,
        scope=scope,
        entities=entities,
        tags=tags,
        action_items=action_items,
        summary=summary,
    )


def classify_text(
    text: str,
    prompt_name: str = "classify_note.txt",
    forced_scope: str | None = None,
    forced_type: str | None = None,
) -> ClassificationResult:
    logger = get_logger("classifier")
    prompt = load_prompt(prompt_name).format(input_text=text[:12000])
    response = call_openrouter(prompt)
    if not response:
        logger.warning("classification_fallback reason=no_response")
        return default_classification(text, forced_scope=forced_scope, forced_type=forced_type)

    try:
        return _parse_response(response, text, forced_scope, forced_type)
    except Exception as exc:
        logger.warning("classification_parse_failed error=%s", exc)
        second_try = call_openrouter(prompt)
        if not second_try:
            return default_classification(text, forced_scope=forced_scope, forced_type=forced_type)
        try:
            return _parse_response(second_try, text, forced_scope, forced_type)
        except Exception as retry_exc:
            logger.warning("classification_retry_parse_failed error=%s", retry_exc)
            return default_classification(text, forced_scope=forced_scope, forced_type=forced_type)
