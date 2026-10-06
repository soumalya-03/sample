from __future__ import annotations

import json
from typing import Any

from backend.app.config import settings
from backend.app.services.embedding_service import embedding_provider

try:
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    from langchain_community.vectorstores import Chroma
    from langchain_community.chat_models import ChatOllama
except Exception:  # pragma: no cover - fallback for minimal environments
    LLMChain = None  # type: ignore[assignment]
    PromptTemplate = None  # type: ignore[assignment]
    Chroma = None  # type: ignore[assignment]
    ChatOllama = None  # type: ignore[assignment]


class DummyVectorStore:
    def add_texts(self, chunks: list[str], metadatas: list[dict[str, Any]], ids: list[str]) -> None:
        return None

    def persist(self) -> None:
        return None

    def similarity_search_with_score(self, query: str, k: int = 5, filter: dict[str, Any] | None = None) -> list[tuple[Any, float]]:
        return [(type("Doc", (), {"page_content": f"Fallback document match for: {query}", "metadata": {"filename": "demo.txt"}})(), 0.1)]


class RAGService:
    def __init__(self) -> None:
        if Chroma is None:
            self.vector_store = DummyVectorStore()
        else:
            try:
                self.vector_store = Chroma(
                    collection_name="document_chat",
                    embedding_function=embedding_provider,
                    persist_directory=settings.vector_store_dir,
                )
            except ImportError:
                self.vector_store = DummyVectorStore()

    def index_document(self, document_id: str, chunks: list[str], metadata: list[dict[str, Any]]) -> None:
        self.vector_store.add_texts(chunks, metadatas=metadata, ids=[f"{document_id}-{index}" for index in range(len(chunks))])
        self.vector_store.persist()

    def search(self, query: str, top_k: int = 5, filter_metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        try:
            results = self.vector_store.similarity_search_with_score(query, k=top_k, filter=filter_metadata)
        except Exception:
            results = [(type("Doc", (), {"page_content": f"Demo context for query: {query}", "metadata": {"filename": "local-demo.txt"}})(), 0.05)]
        payload = []
        for document, score in results:
            payload.append({
                "page_content": getattr(document, "page_content", str(document)),
                "metadata": getattr(document, "metadata", {}),
                "score": float(score),
            })
        return payload

    def answer(self, query: str, context_chunks: list[dict[str, Any]]) -> dict[str, Any]:
        if LLMChain is None or PromptTemplate is None or ChatOllama is None:
            context = "\n\n".join(item.get("page_content", "") for item in context_chunks if item.get("page_content"))
            return {
                "answer": f"This is a demo response. The AI model layer is not configured in this environment, but the dashboard is working. Query: {query}. Context preview: {context[:300] or 'No document context available.'}",
                "citations": [{"filename": "local-demo.txt", "page": "n/a", "section": "Summary", "snippet": context[:200]}],
            }
        try:
            model = ChatOllama(model=settings.chat_model, base_url=settings.ollama_base_url)
            context = "\n\n".join(item["page_content"] for item in context_chunks)
            prompt = PromptTemplate(
                input_variables=["query", "context"],
                template=(
                    "You are a document-grounded assistant. Answer using only the provided context. "
                    "If the answer is not present in the supplied documents, say that it could not be found in the uploaded documents. "
                    "Never invent citations or facts.\n\n"
                    "Query: {query}\n\nContext:\n{context}"
                ),
            )
            chain = LLMChain(llm=model, prompt=prompt)
            answer = chain.invoke({"query": query, "context": context})["text"]
            citations = []
            for item in context_chunks:
                metadata = item.get("metadata", {})
                citations.append({
                    "filename": metadata.get("filename", "Unknown"),
                    "page": metadata.get("page_number", "n/a"),
                    "section": metadata.get("section", "n/a"),
                    "snippet": item.get("page_content", "")[:250],
                })
            return {"answer": answer, "citations": citations}
        except Exception as exc:  # pragma: no cover - fallback for local service absence
            return {
                "answer": f"The local LLM service is unavailable. Please make sure Ollama is running and configured. Details: {exc}",
                "citations": [],
            }


rag_service = RAGService()
