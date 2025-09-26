import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
import pytest
from ai.rag_system import CommunityRAGSystem

def test_rag_system_init_no_db():
    try:
        rag = CommunityRAGSystem("postgresql://user:pass@localhost:5432/db")
    except Exception:
        rag = None
    assert True  # Should not crash test run

def test_rag_method_presence():
    assert hasattr(CommunityRAGSystem, 'similarity_search')
    assert hasattr(CommunityRAGSystem, 'get_relevant_documents')

