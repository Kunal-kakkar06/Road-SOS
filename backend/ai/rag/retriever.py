"""
ai/rag/retriever.py
====================
RAG (Retrieval-Augmented Generation) interface — STUB.

This module defines the interface that a future RAG implementation must
satisfy.  Currently it returns an explicit "not configured" result so
the rest of the pipeline can handle the absence of RAG cleanly without
special-casing.

DO NOT invent or hard-code fake medical documents here.

When RAG is implemented:
  1. A vector store (e.g. ChromaDB, Pinecone, pgvector) will be configured.
  2. Medical guidelines (WHO, ACEP, Indian emergency protocols) will be
     embedded and stored.
  3. The retrieve() method will perform a semantic similarity search.
  4. The orchestrator will pass retrieved chunks to the LLM explainer.

Nothing else in the pipeline changes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger("roadsos.ai.rag")


@dataclass
class RetrievedDocument:
    """A single document/chunk returned by the RAG retriever."""
    source_id: str
    title: Optional[str]
    content: str
    relevance_score: Optional[float] = None
    source_type: Optional[str] = None  # "medical_guideline" | "protocol" | "case_study"


@dataclass
class RAGResult:
    """Result envelope from the RAG retriever."""
    status: str                                   # "ok" | "not_configured" | "error"
    documents: List[RetrievedDocument] = field(default_factory=list)
    query_used: Optional[str] = None
    error: Optional[str] = None

    def is_available(self) -> bool:
        return self.status == "ok" and bool(self.documents)


class RAGRetriever:
    """
    Interface for semantic document retrieval.

    Current state: STUB — returns not_configured result.
    Future state: connects to a vector store and performs semantic search.
    """

    def __init__(self, config=None):
        self._config = config
        self._is_configured = False
        # Future: self._vector_store = None

    def retrieve(self, query: str, top_k: int = 3) -> RAGResult:
        """
        Retrieve the top_k most relevant documents for the given query.

        Args:
            query:  The search query (e.g. symptom description or triage context).
            top_k:  Maximum number of documents to return.

        Returns:
            RAGResult with status="not_configured" until the vector store
            is connected.  The orchestrator treats this as non-fatal and
            continues without retrieved context.
        """
        if not self._is_configured:
            logger.debug("[RAGRetriever] Not configured — returning empty result.")
            return RAGResult(
                status="not_configured",
                documents=[],
                query_used=query,
                error=None,
            )

        # ── Future implementation placeholder ──────────────────
        # try:
        #     results = self._vector_store.similarity_search(query, k=top_k)
        #     documents = [RetrievedDocument(...) for r in results]
        #     return RAGResult(status="ok", documents=documents, query_used=query)
        # except Exception as exc:
        #     logger.error("[RAGRetriever] retrieval failed: %s", exc)
        #     return RAGResult(status="error", error=str(exc), query_used=query)

        return RAGResult(status="not_configured", query_used=query)

    def health_check(self) -> dict:
        """Return health status for /api/ai/health."""
        return {
            "status": "not_configured",
            "detail": "RAG vector store not yet configured. Set AI_ENABLE_RAG=true to activate.",
        }
