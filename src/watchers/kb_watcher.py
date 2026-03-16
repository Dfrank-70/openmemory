from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path
from typing import Any

import yaml

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers.polling import PollingObserver as Observer
except ImportError:
    class FileSystemEvent:  # type: ignore[no-redef]
        def __init__(self, src_path: str = "", is_directory: bool = False):
            self.src_path = src_path
            self.is_directory = is_directory

    class FileSystemEventHandler:  # type: ignore[no-redef]
        pass

    Observer = None  # type: ignore[assignment,misc]

from src.config.settings import get_logger, get_settings
from src.processing.classifier import classify_text
from src.processing.pipeline import compute_content_hash, extract_frontmatter, has_recent_processed_marker, touch_processed_marker
from src.storage.chroma_client import OpenMemoryChromaClient, get_chroma_client
from src.storage.git_ops import GitOperations, get_git_ops

IGNORE_PATTERNS = [
    ".obsidian/",
    ".git/",
    "kb/attachments/",
    ".tmp",
    ".swp",
    "~",
    ".DS_Store",
]


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


class KBWatcher:
    def __init__(
        self,
        chroma_client: OpenMemoryChromaClient | None = None,
        git_ops: GitOperations | None = None,
        debounce_seconds: int = 5,
        marker_window_seconds: int = 10,
    ) -> None:
        self.settings = get_settings()
        self.logger = get_logger("kb_watcher")
        self.chroma_client = chroma_client or get_chroma_client()
        self.git_ops = git_ops or get_git_ops()
        self.debounce_seconds = debounce_seconds
        self.marker_window_seconds = marker_window_seconds
        self.pending: dict[Path, str] = {}
        self.lock = threading.Lock()
        self.timer: threading.Timer | None = None
        self.observer: Any = None

    def should_ignore(self, path: str | Path) -> bool:
        candidate = str(path)
        if not candidate.endswith(".md"):
            return True
        return any(pattern in candidate for pattern in IGNORE_PATTERNS)

    def schedule(self, path: str | Path, action: str) -> None:
        candidate = Path(path).expanduser().resolve(strict=False)
        if self.should_ignore(candidate):
            return
        with self.lock:
            self.pending[candidate] = action
            if self.timer is not None:
                self.timer.cancel()
            self.timer = threading.Timer(self.debounce_seconds, self.flush_pending)
            self.timer.daemon = True
            self.timer.start()

    def flush_pending(self) -> None:
        with self.lock:
            batch = dict(self.pending)
            self.pending.clear()
            self.timer = None
        if not batch:
            return
        changed_paths: list[Path] = []
        action_counts: dict[str, int] = {"upsert": 0, "delete": 0}
        for path, action in batch.items():
            if self.process_path(path, action):
                changed_paths.append(path)
                action_counts[action] = action_counts.get(action, 0) + 1
        if not changed_paths:
            return
        message = f"watcher sync: {action_counts.get('upsert', 0)} upsert, {action_counts.get('delete', 0)} delete"
        self.git_ops.commit_paths(changed_paths, message)

    def process_path(self, path: Path, action: str) -> bool:
        if action == "delete":
            return self.process_delete(path)
        return self.process_upsert(path)

    def _relative_to_home(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.settings.open_memory_home))
        except Exception:
            return str(path)

    def process_upsert(self, path: Path) -> bool:
        if self.should_ignore(path):
            return False
        if has_recent_processed_marker(path, max_age_seconds=self.marker_window_seconds):
            self.logger.info("watcher_skip_recent_marker path=%s", path)
            return False
        if not path.exists():
            return False
        try:
            markdown = path.read_text(encoding="utf-8")
        except Exception as exc:
            self.logger.warning("watcher_read_failed path=%s error=%s", path, exc)
            return False
        frontmatter, body = extract_frontmatter(markdown)
        frontmatter_complete = bool(frontmatter.get("scope") and frontmatter.get("type"))
        if not frontmatter_complete and self.settings.watcher_auto_classify and self.settings.openrouter_api_key:
            try:
                classification = classify_text(markdown, prompt_name="classify_note.txt")
                enriched = {
                    "scope": classification.scope,
                    "type": classification.item_type,
                    "tags": classification.tags,
                    "entities": classification.entities,
                    "summary": classification.summary,
                }
                if classification.action_items:
                    enriched["action_items"] = classification.action_items
                frontmatter = {**enriched, **frontmatter}
                fm_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
                markdown = f"---\n{fm_text}\n---\n\n{body}"
                path.write_text(markdown, encoding="utf-8")
                touch_processed_marker(path)
                self.logger.info("watcher_classified path=%s scope=%s type=%s", path, frontmatter["scope"], frontmatter["type"])
            except Exception as exc:
                self.logger.warning("watcher_classify_failed path=%s error=%s", path, exc)
        metadata = {
            "path": self._relative_to_home(path),
            "scope": str(frontmatter.get("scope", "all")),
            "type": str(frontmatter.get("type", "note")),
            "entities": _string_list(frontmatter.get("entities")),
            "tags": _string_list(frontmatter.get("tags")),
            "content_hash": str(frontmatter.get("content_hash") or compute_content_hash(markdown)),
            "source": str(frontmatter.get("source", "watcher")),
        }
        success = self.chroma_client.upsert_document(path=path, text=markdown, metadata=metadata)
        if success:
            self.logger.info("watcher_upsert path=%s", path)
        return success

    def process_delete(self, path: Path) -> bool:
        if self.should_ignore(path):
            return False
        document_id = self._relative_to_home(path)
        success = self.chroma_client.delete_document(document_id)
        if success:
            self.logger.info("watcher_delete path=%s", path)
        return success

    def start(self) -> None:
        if Observer is None:
            raise RuntimeError("watchdog is required to run the watcher")
        handler = KBEventHandler(self)
        observer = Observer(timeout=10.0)  # 10 second polling - efficient for Obsidian use case
        observer.schedule(handler, str(self.settings.kb_dir), recursive=True)
        observer.start()
        self.observer = observer
        self.logger.info("watcher_started kb_dir=%s", self.settings.kb_dir)

    def stop(self) -> None:
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None

    def run_forever(self) -> None:
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()


class KBEventHandler(FileSystemEventHandler):
    def __init__(self, watcher: KBWatcher) -> None:
        self.watcher = watcher

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self.watcher.schedule(event.src_path, "upsert")

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self.watcher.schedule(event.src_path, "upsert")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self.watcher.schedule(event.src_path, "delete")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Watch kb markdown files and sync them to ChromaDB and git")
    parser.add_argument("--debounce-seconds", type=int, default=5)
    parser.add_argument("--marker-window-seconds", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    watcher = KBWatcher(
        debounce_seconds=args.debounce_seconds,
        marker_window_seconds=args.marker_window_seconds,
    )
    watcher.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
