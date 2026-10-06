from __future__ import annotations

from typing import Any

from backend.app.config import settings

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings, OllamaEmbeddings
except Exception:  # pragma: no cover - graceful fallback for minimal environments
    HuggingFaceEmbeddings = None  # type: ignore[assignment]
    OllamaEmbeddings = None  # type: ignore[assignment]


class FallbackEmbeddingProvider:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)) / 10.0, float(sum(ord(ch) for ch in text) % 100), 0.0] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)) / 10.0, float(sum(ord(ch) for ch in text) % 100), 0.0]


class EmbeddingProvider:
    def __init__(self) -> None:
        self.provider = settings.default_provider.lower()
        self.model_name = settings.embedding_model
        self.embedder = self._build_embedder()

    def _build_embedder(self) -> Any:
        if OllamaEmbeddings is not None and self.provider == "ollama":
            return OllamaEmbeddings(model=self.model_name, base_url=settings.ollama_base_url)
        if HuggingFaceEmbeddings is not None:
            return HuggingFaceEmbeddings(model_name=self.model_name)
        return FallbackEmbeddingProvider()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embedder.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.embedder.embed_query(text)


embedding_provider = EmbeddingProvider()
