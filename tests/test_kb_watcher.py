import time

from src.watchers.kb_watcher import KBWatcher


class DummyChroma:
    def __init__(self):
        self.upserts = []
        self.deletes = []

    def upsert_document(self, path, text, metadata):
        self.upserts.append({"path": path, "text": text, "metadata": metadata})
        return True

    def delete_document(self, document_id):
        self.deletes.append(document_id)
        return True


class DummyGit:
    def __init__(self):
        self.commits = []

    def commit_paths(self, paths, message):
        self.commits.append({"paths": paths, "message": message})
        return True


def _logger():
    return type("Logger", (), {"info": lambda *args, **kwargs: None, "warning": lambda *args, **kwargs: None})()


def test_should_ignore_paths(monkeypatch, tmp_path):
    settings = type("Settings", (), {"open_memory_home": tmp_path, "kb_dir": tmp_path / "kb"})()
    monkeypatch.setattr("src.watchers.kb_watcher.get_settings", lambda: settings)
    monkeypatch.setattr("src.watchers.kb_watcher.get_logger", lambda name: _logger())
    watcher = KBWatcher(chroma_client=DummyChroma(), git_ops=DummyGit())
    assert watcher.should_ignore("/tmp/.obsidian/config.md")
    assert watcher.should_ignore("/tmp/kb/attachments/file.md")
    assert watcher.should_ignore("/tmp/file.md.tmp")
    assert not watcher.should_ignore("/tmp/kb/work/notes/note.md")


def test_process_upsert_reads_frontmatter(tmp_path, monkeypatch):
    kb_dir = tmp_path / "kb"
    notes_dir = kb_dir / "work" / "notes"
    notes_dir.mkdir(parents=True)
    note_path = notes_dir / "nota.md"
    note_path.write_text(
        "---\nscope: work\ntype: decision\nentities:\n  - progetto-alfa\ntags:\n  - architettura\nsource: obsidian\n---\n\nContenuto\n",
        encoding="utf-8",
    )

    settings = type("Settings", (), {"open_memory_home": tmp_path, "kb_dir": kb_dir})()
    chroma = DummyChroma()
    git = DummyGit()
    monkeypatch.setattr("src.watchers.kb_watcher.get_settings", lambda: settings)
    monkeypatch.setattr("src.watchers.kb_watcher.get_logger", lambda name: _logger())
    watcher = KBWatcher(chroma_client=chroma, git_ops=git)

    assert watcher.process_upsert(note_path)
    assert chroma.upserts[0]["metadata"]["scope"] == "work"
    assert chroma.upserts[0]["metadata"]["type"] == "decision"
    assert chroma.upserts[0]["metadata"]["entities"] == ["progetto-alfa"]


def test_process_delete_uses_relative_path(tmp_path, monkeypatch):
    kb_dir = tmp_path / "kb"
    notes_dir = kb_dir / "work" / "notes"
    notes_dir.mkdir(parents=True)
    note_path = notes_dir / "nota.md"

    settings = type("Settings", (), {"open_memory_home": tmp_path, "kb_dir": kb_dir})()
    chroma = DummyChroma()
    git = DummyGit()
    monkeypatch.setattr("src.watchers.kb_watcher.get_settings", lambda: settings)
    monkeypatch.setattr("src.watchers.kb_watcher.get_logger", lambda name: _logger())
    watcher = KBWatcher(chroma_client=chroma, git_ops=git)

    assert watcher.process_delete(note_path)
    assert chroma.deletes == ["kb/work/notes/nota.md"]


def test_marker_skips_recent_files(tmp_path, monkeypatch):
    kb_dir = tmp_path / "kb"
    notes_dir = kb_dir / "work" / "notes"
    notes_dir.mkdir(parents=True)
    note_path = notes_dir / "nota.md"
    note_path.write_text("---\nscope: work\ntype: note\n---\n\nContenuto\n", encoding="utf-8")
    marker = note_path.with_name(f"{note_path.name}.processed")
    marker.write_text("", encoding="utf-8")

    settings = type("Settings", (), {"open_memory_home": tmp_path, "kb_dir": kb_dir})()
    chroma = DummyChroma()
    git = DummyGit()
    monkeypatch.setattr("src.watchers.kb_watcher.get_settings", lambda: settings)
    monkeypatch.setattr("src.watchers.kb_watcher.get_logger", lambda name: _logger())
    watcher = KBWatcher(chroma_client=chroma, git_ops=git, marker_window_seconds=10)

    assert not watcher.process_upsert(note_path)
    assert chroma.upserts == []


def test_auto_classify_enriches_frontmatter(tmp_path, monkeypatch):
    kb_dir = tmp_path / "kb"
    notes_dir = kb_dir / "work" / "notes"
    notes_dir.mkdir(parents=True)
    note_path = notes_dir / "nota.md"
    note_path.write_text("Ho deciso di usare PostgreSQL per il progetto alfa.\n", encoding="utf-8")

    from dataclasses import dataclass

    @dataclass
    class FakeClassification:
        scope: str = "work"
        item_type: str = "decision"
        tags: list = None
        entities: list = None
        summary: str = "Decisione su database"
        action_items: list = None

        def __post_init__(self):
            if self.tags is None:
                self.tags = ["database"]
            if self.entities is None:
                self.entities = ["progetto-alfa"]
            if self.action_items is None:
                self.action_items = []

    settings = type("Settings", (), {
        "open_memory_home": tmp_path,
        "kb_dir": kb_dir,
        "watcher_auto_classify": True,
        "openrouter_api_key": "sk-test",
    })()
    chroma = DummyChroma()
    git = DummyGit()
    monkeypatch.setattr("src.watchers.kb_watcher.get_settings", lambda: settings)
    monkeypatch.setattr("src.watchers.kb_watcher.get_logger", lambda name: _logger())
    monkeypatch.setattr("src.watchers.kb_watcher.classify_text", lambda text, prompt_name=None: FakeClassification())

    watcher = KBWatcher(chroma_client=chroma, git_ops=git)
    assert watcher.process_upsert(note_path)

    content = note_path.read_text(encoding="utf-8")
    assert "scope: work" in content
    assert "type: decision" in content
    assert "progetto-alfa" in content
    assert chroma.upserts[0]["metadata"]["scope"] == "work"
    assert chroma.upserts[0]["metadata"]["type"] == "decision"


def test_auto_classify_skipped_if_frontmatter_complete(tmp_path, monkeypatch):
    kb_dir = tmp_path / "kb"
    notes_dir = kb_dir / "work" / "notes"
    notes_dir.mkdir(parents=True)
    note_path = notes_dir / "nota.md"
    note_path.write_text(
        "---\nscope: work\ntype: decision\n---\n\nContenuto già classificato.\n",
        encoding="utf-8",
    )

    settings = type("Settings", (), {
        "open_memory_home": tmp_path,
        "kb_dir": kb_dir,
        "watcher_auto_classify": True,
        "openrouter_api_key": "sk-test",
    })()
    chroma = DummyChroma()
    git = DummyGit()
    classify_calls = []
    monkeypatch.setattr("src.watchers.kb_watcher.get_settings", lambda: settings)
    monkeypatch.setattr("src.watchers.kb_watcher.get_logger", lambda name: _logger())
    monkeypatch.setattr("src.watchers.kb_watcher.classify_text", lambda text, prompt_name=None: classify_calls.append(1))

    watcher = KBWatcher(chroma_client=chroma, git_ops=git)
    watcher.process_upsert(note_path)

    assert classify_calls == []


def test_debounce_processes_file_once(tmp_path, monkeypatch):
    kb_dir = tmp_path / "kb"
    notes_dir = kb_dir / "work" / "notes"
    notes_dir.mkdir(parents=True)
    note_path = notes_dir / "nota.md"
    note_path.write_text("---\nscope: work\ntype: note\n---\n\nContenuto\n", encoding="utf-8")

    settings = type("Settings", (), {"open_memory_home": tmp_path, "kb_dir": kb_dir})()
    chroma = DummyChroma()
    git = DummyGit()
    monkeypatch.setattr("src.watchers.kb_watcher.get_settings", lambda: settings)
    monkeypatch.setattr("src.watchers.kb_watcher.get_logger", lambda name: _logger())
    watcher = KBWatcher(chroma_client=chroma, git_ops=git, debounce_seconds=0.1)

    watcher.schedule(note_path, "upsert")
    watcher.schedule(note_path, "upsert")
    watcher.schedule(note_path, "upsert")

    time.sleep(0.5)

    assert len(chroma.upserts) == 1
    assert len(git.commits) == 1
