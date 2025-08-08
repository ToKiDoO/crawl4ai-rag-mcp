"""
Mock OpenAI helper to speed up tests by avoiding real API calls
"""

import os
from unittest.mock import Mock, patch

# Default embedding vector
DEFAULT_EMBEDDING = [0.1] * 1536


class MockOpenAIEmbeddings:
    """Mock OpenAI embeddings response"""

    def __init__(self):
        self.data = [Mock(embedding=DEFAULT_EMBEDDING)]


def mock_create_embeddings(**kwargs):
    """Mock function for OpenAI embeddings.create"""
    return MockOpenAIEmbeddings()


def patch_openai_embeddings():
    """Patch OpenAI to use mock embeddings"""
    # Set fake API key to avoid validation errors
    os.environ["OPENAI_API_KEY"] = "test-mock-key-fast"

    # Create patches
    patches = [
        patch("openai.embeddings.create", side_effect=mock_create_embeddings),
        patch(
            "openai.OpenAI",
            return_value=Mock(
                embeddings=Mock(create=Mock(side_effect=mock_create_embeddings)),
            ),
        ),
    ]

    return patches
