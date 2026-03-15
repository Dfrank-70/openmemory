from __future__ import annotations

import json
from typing import Any

import requests

from src.config.settings import get_logger, get_settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def call_openrouter(prompt: str, system_prompt: str | None = None, temperature: float = 0.1) -> str | None:
    settings = get_settings()
    logger = get_logger("openrouter")
    if not settings.openrouter_api_key:
        logger.warning("openrouter_api_key_missing")
        return None

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": settings.openrouter_model,
        "messages": messages,
        "temperature": temperature,
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(2):
        try:
            response = requests.post(OPENROUTER_URL, headers=headers, data=json.dumps(payload), timeout=60)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("openrouter_call_failed attempt=%s error=%s", attempt + 1, exc)
    return None
