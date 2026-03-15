from pathlib import Path
from types import SimpleNamespace

from src.mcp_server.tools import get_context_tool, get_project_tool, search_tool


class DummyChroma:
    def search(self, query, scope="all", item_type="all", limit=10):
        return [
            {
                "document": "contenuto rilevante",
                "distance": 0.12,
                "metadata": {
                    "path": "kb/work/projects/progetto-alfa.md",
                    "scope": "work",
                    "type": "project",
                },
            }
        ]


class DummySettings(SimpleNamespace):
    def is_path_allowed(self, path: Path) -> bool:
        return True


def test_get_project_and_context_tools(tmp_path, monkeypatch):
    kb_dir = tmp_path / "kb"
    work_projects = kb_dir / "work" / "projects"
    shared = kb_dir / "shared"
    work_projects.mkdir(parents=True)
    shared.mkdir(parents=True)

    project_path = work_projects / "progetto-alfa.md"
    project_path.write_text("# Progetto Alfa", encoding="utf-8")
    index_path = kb_dir / "index.md"
    index_path.write_text("## Progetti attivi\nuno\n\n## Ultime decisioni\ndue\n", encoding="utf-8")

    settings = DummySettings(kb_dir=kb_dir, open_memory_home=tmp_path, profile="full")
    monkeypatch.setattr("src.mcp_server.tools.get_settings", lambda: settings)
    monkeypatch.setattr("src.mcp_server.tools.get_chroma_client", lambda: DummyChroma())

    assert get_project_tool("progetto-alfa") == "# Progetto Alfa"
    context = get_context_tool("work")
    assert "## Progetti attivi" in context
    results = search_tool("progetto alfa")
    assert results[0]["path"] == "kb/work/projects/progetto-alfa.md"
