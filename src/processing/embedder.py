from __future__ import annotations

from functools import lru_cache

from src.config.settings import get_logger, get_settings


@lru_cache(maxsize=1)
def _load_model():
    logger = get_logger("embedder")
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        logger.warning("sentence_transformers_import_failed error=%s", exc)
        return None

    settings = get_settings()
    try:
        return SentenceTransformer(settings.embedding_model)
    except Exception as exc:
        logger.warning("embedding_model_load_failed model=%s error=%s", settings.embedding_model, exc)
        return None


def embed_text(text: str) -> list[float]:
    model = _load_model()
    if model is None:
        return []
    return model.encode(f"passage: {text}").tolist()


def embed_query(query: str) -> list[float]:
    model = _load_model()
    if model is None:
        return []
    return model.encode(f"query: {query}").tolist()
