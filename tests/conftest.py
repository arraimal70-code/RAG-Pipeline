"""
Global pytest fixtures for RAG-Pipeline.
"""

import pytest
from src.pipeline import RAGPipeline


@pytest.fixture
def pipeline():
    """Provides a fresh or standard RAGPipeline instance."""
    return RAGPipeline()
