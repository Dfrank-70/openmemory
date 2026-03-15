from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.config.settings import get_logger, get_settings
from src.processing.embedder import embed_query, embed_text


class OpenMemoryChromaClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger = get_logger("chroma")
        self._client = None
        self._collection = None

    def _ensure_collection(self):
        if self._collection is not None:
            return self._collection
        try:
            import chromadb

            self._client = chromadb.HttpClient(host=self.settings.chroma_host, port=self.settings.chroma_port)
            self._collection = self._client.get_or_create_collection(name=self.settings.chroma_collection)
            return self._collection
        except Exception as exc:
            self.logger.warning("chroma_unavailable error=%s", exc)
            return None

    @staticmethod
    def _normalize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                normalized[key] = value
            elif isinstance(value, Path):
                normalized[key] = str(value)
            else:
                normalized[key] = json.dumps(value, ensure_ascii=False)
        return normalized

    def upsert_document(self, path: Path, text: str, metadata: dict[str, Any]) -> bool:
        collection = self._ensure_collection()
        if collection is None:
            return False
        doc_id = hashlib.sha256(f"{path}:{metadata.get('content_hash', '')}".encode("utf-8")).hexdigest()
        embedding = embed_text(text)
        if not embedding:
            self.logger.warning("embedding_unavailable_skip_index path=%s", path)
            return False
        try:
            collection.upsert(
                ids=[doc_id],
                documents=[text],
                metadatas=[self._normalize_metadata(metadata)],
                embeddings=[embedding],
            )
            return True
        except Exception as exc:
            self.logger.warning("chroma_upsert_failed path=%s error=%s", path, exc)
            return False

    def search(self, query: str, scope: str = "all", item_type: str = "all", limit: int = 10) -> list[dict[str, Any]]:
        collection = self._ensure_collection()
        if collection is None:
            return []
        query_embedding = embed_query(query)
        if not query_embedding:
            return []

        where: dict[str, Any] | None = None
        conditions: list[dict[str, Any]] = []
        if scope != "all":
            conditions.append({"scope": scope})
        if item_type != "all":
            conditions.append({"type": item_type})
        if len(conditions) == 1:
            where = conditions[0]
        elif len(conditions) > 1:
            where = {"$and": conditions}

        try:
            result = collection.query(query_embeddings=[query_embedding], n_results=limit, where=where)
        except Exception as exc:
            self.logger.warning("chroma_query_failed error=%s", exc)
            return []

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        ids = result.get("ids", [[]])[0]
        payload: list[dict[str, Any]] = []
        for doc_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            payload.append(
                {
                    "id": doc_id,
                    "document": document,
                    "metadata": metadata or {},
                    "distance": distance,
                }
            )
        return payload


_client: OpenMemoryChromaClient | None = None


def get_chroma_client() -> OpenMemoryChromaClient:
    global _client
    if _client is None:
        _client = OpenMemoryChromaClient()
    return _client
