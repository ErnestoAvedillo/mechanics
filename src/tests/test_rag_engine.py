"""Test code to verify RAG engine functionality."""

from django.test import TestCase
from specs.rag_engine import get_rag_engine

class RAGEngineTestCase(TestCase):
    def test_rag_engine_initialization(self):
        """Test that the RAG engine initializes correctly for a user."""
        user_id = 1  # Simulate a user ID
        try:
            rag_engine = get_rag_engine(user_id)
            self.assertIsNotNone(rag_engine, "RAG engine should be initialized")
            print("RAG engine initialized successfully.")
        except Exception as e:
            self.fail(f"RAG engine initialization failed with error: {e}")
    
    def test_rag_engine_query(self):
        """Test that the RAG engine can process a query."""
        user_id = 1  # Simulate a user ID
        query_text = "¿Cuál es la tolerancia para el muelle XYZ?"
        try:
            rag_engine = get_rag_engine(user_id)
            response = rag_engine.query(query_text)
            self.assertIsNotNone(response, "RAG engine should return a response")
            print(f"RAG engine query response: {response}")
        except Exception as e:
            self.fail(f"RAG engine query failed with error: {e}")
    
    def test_rag_engine_response_format(self):
        """Test that the RAG engine response includes source nodes."""
        user_id = 1  # Simulate a user ID
        query_text = "¿Cuál es la tolerancia para el muelle XYZ?"
        try:
            rag_engine = get_rag_engine(user_id)
            response = rag_engine.query(query_text)
            self.assertTrue(hasattr(response, 'source_nodes'), "RAG response should include source nodes")
            print(f"RAG engine response includes {len(response.source_nodes)} source nodes.")
        except Exception as e:
            self.fail(f"RAG engine response format test failed with error: {e}")


if __name__ == '__main__':
    import unittest
    unittest.main()
    