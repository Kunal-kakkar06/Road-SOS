"""
tests/ai/test_rag_retriever.py
Tests for RAGRetriever stub — verifies it returns correct not_configured status.
"""
from ai.rag.retriever import RAGRetriever, RAGResult


class TestRAGRetriever:
    def setup_method(self):
        self.retriever = RAGRetriever()

    def test_retrieve_returns_rag_result(self):
        result = self.retriever.retrieve("chest pain symptoms")
        assert isinstance(result, RAGResult)

    def test_retrieve_returns_not_configured_by_default(self):
        result = self.retriever.retrieve("query")
        assert result.status == "not_configured"

    def test_retrieve_returns_empty_documents_when_not_configured(self):
        result = self.retriever.retrieve("query")
        assert result.documents == []

    def test_retrieve_echoes_query(self):
        result = self.retriever.retrieve("my test query")
        assert result.query_used == "my test query"

    def test_is_available_returns_false_when_not_configured(self):
        result = self.retriever.retrieve("query")
        assert result.is_available() is False

    def test_retrieve_with_top_k(self):
        """top_k parameter must be accepted without error."""
        result = self.retriever.retrieve("query", top_k=5)
        assert result.status == "not_configured"

    def test_health_check_returns_dict(self):
        health = self.retriever.health_check()
        assert "status" in health
        assert health["status"] == "not_configured"

    def test_health_check_has_detail(self):
        health = self.retriever.health_check()
        assert "detail" in health

    def test_no_fake_documents_invented(self):
        """CRITICAL: RAG must never invent fake medical documents."""
        result = self.retriever.retrieve("heart attack treatment protocol")
        assert len(result.documents) == 0
