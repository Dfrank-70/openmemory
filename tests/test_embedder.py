from src.processing.embedder import embed_query, embed_text


class DummyVector:
    def __init__(self, values):
        self._values = values

    def tolist(self):
        return self._values


class DummyModel:
    def __init__(self):
        self.calls = []

    def encode(self, value):
        self.calls.append(value)
        return DummyVector([0.1, 0.2, 0.3])


def test_embed_text_uses_passage_prefix(monkeypatch):
    model = DummyModel()
    monkeypatch.setattr("src.processing.embedder._load_model", lambda: model)
    vector = embed_text("ciao mondo")
    assert vector == [0.1, 0.2, 0.3]
    assert model.calls == ["passage: ciao mondo"]


def test_embed_query_uses_query_prefix(monkeypatch):
    model = DummyModel()
    monkeypatch.setattr("src.processing.embedder._load_model", lambda: model)
    vector = embed_query("trova progetto alfa")
    assert vector == [0.1, 0.2, 0.3]
    assert model.calls == ["query: trova progetto alfa"]
