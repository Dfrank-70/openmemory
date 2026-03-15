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
