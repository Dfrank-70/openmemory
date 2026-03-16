from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_home() -> Path:
    env_value = os.getenv("OPEN_MEMORY_HOME", "").strip()
    if env_value:
        return Path(env_value).expanduser().resolve()
    return ROOT_DIR


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[\s_]+", "-", normalized)
    normalized = re.sub(r"[^a-z0-9\-àèéìòù]", "-", normalized)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "item"


@dataclass(slots=True)
class Settings:
    root_dir: Path = field(default_factory=lambda: ROOT_DIR)
    open_memory_home: Path = field(default_factory=_resolve_home)
    openrouter_api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", "").strip())
    openrouter_model: str = field(default_factory=lambda: os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-haiku").strip())
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large").strip())
    whisper_model: str = field(default_factory=lambda: os.getenv("WHISPER_MODEL", "medium").strip())
    chroma_host: str = field(default_factory=lambda: os.getenv("CHROMA_HOST", "localhost").strip())
    chroma_port: int = field(default_factory=lambda: int(os.getenv("CHROMA_PORT", "8100")))
    chroma_collection: str = field(default_factory=lambda: os.getenv("CHROMA_COLLECTION", "open-memory").strip())
    profile: str = field(default_factory=lambda: os.getenv("OPEN_MEMORY_PROFILE", "full").strip())
    mcp_host: str = field(default_factory=lambda: os.getenv("OPEN_MEMORY_MCP_HOST", "0.0.0.0").strip())
    mcp_port: int = field(default_factory=lambda: int(os.getenv("OPEN_MEMORY_MCP_PORT", "8000")))
    auth_token: str = field(default_factory=lambda: os.getenv("OPEN_MEMORY_AUTH_TOKEN", "").strip())
    git_auto_push: bool = field(default_factory=lambda: _bool_env("GIT_AUTO_PUSH", True))
    git_push_interval: int = field(default_factory=lambda: int(os.getenv("GIT_PUSH_INTERVAL", "900")))
    imap_host: str = field(default_factory=lambda: os.getenv("IMAP_HOST", "imap.gmail.com").strip())
    imap_user: str = field(default_factory=lambda: os.getenv("IMAP_USER", "").strip())
    imap_password: str = field(default_factory=lambda: os.getenv("IMAP_PASSWORD", "").strip())
    imap_poll_interval: int = field(default_factory=lambda: int(os.getenv("IMAP_POLL_INTERVAL", "300")))
    watcher_auto_classify: bool = field(default_factory=lambda: _bool_env("WATCHER_AUTO_CLASSIFY", False))
    kb_dir: Path = field(init=False)
    logs_dir: Path = field(init=False)
    attachments_dir: Path = field(init=False)
    prompts_dir: Path = field(init=False)
    project_templates_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.kb_dir = self.open_memory_home / "kb"
        self.logs_dir = self.open_memory_home / "logs"
        self.attachments_dir = self.kb_dir / "attachments"
        self.prompts_dir = self.root_dir / "src" / "config" / "prompts"
        self.project_templates_dir = self.root_dir / "src" / "config" / "project_templates"

    def ensure_directories(self) -> None:
        directories = [
            self.kb_dir,
            self.kb_dir / "work",
            self.kb_dir / "work" / "projects",
            self.kb_dir / "work" / "notes",
            self.kb_dir / "work" / "emails",
            self.kb_dir / "personal",
            self.kb_dir / "personal" / "notes",
            self.kb_dir / "personal" / "projects",
            self.kb_dir / "personal" / "finance",
            self.kb_dir / "shared",
            self.kb_dir / "shared" / "digests",
            self.attachments_dir,
            self.logs_dir,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def allowed_scope_roots(self) -> list[Path]:
        if self.profile == "work":
            return [self.kb_dir / "work", self.kb_dir / "shared"]
        return [self.kb_dir]

    def is_path_allowed(self, path: Path) -> bool:
        resolved = path.resolve()
        return any(root.resolve() in [resolved, *resolved.parents] for root in self.allowed_scope_roots())

    def project_dir(self, scope: str) -> Path:
        scope_value = "personal" if scope == "personal" else "work"
        return self.kb_dir / scope_value / "projects"

    def note_dir(self, scope: str) -> Path:
        scope_value = "personal" if scope == "personal" else "work"
        return self.kb_dir / scope_value / "notes"

    def email_dir(self, scope: str, item_type: str) -> Path:
        if scope == "personal" and item_type == "finance_update":
            return self.kb_dir / "personal" / "finance"
        if scope == "personal":
            return self.kb_dir / "personal" / "notes"
        return self.kb_dir / "work" / "emails"


def load_prompt(prompt_name: str) -> str:
    settings = get_settings()
    prompt_path = settings.prompts_dir / prompt_name
    return prompt_path.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings


_LOGGERS: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    if name in _LOGGERS:
        return _LOGGERS[name]
    settings = get_settings()
    logger = logging.getLogger(f"open_memory.{name}")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        log_path = settings.logs_dir / f"{name}.log"
        handler = TimedRotatingFileHandler(log_path, when="midnight", backupCount=14, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    _LOGGERS[name] = logger
    return logger


def iter_markdown_files(base_dir: Path) -> Iterable[Path]:
    if not base_dir.exists():
        return []
    return sorted(base_dir.rglob("*.md"))
