from src.processing.classifier import classify_text


def test_classifier_falls_back_when_llm_is_unavailable(monkeypatch):
    monkeypatch.setattr("src.processing.classifier.call_openrouter", lambda prompt: None)
    result = classify_text("Abbiamo deciso di usare FastAPI per Progetto Alfa")
    assert result.item_type == "unclassified"
    assert result.scope == "work"
    assert isinstance(result.summary, str)
    assert result.summary
