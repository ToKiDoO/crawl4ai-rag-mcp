"""Test setup to ensure environment is configured before imports."""

import os

# Set test environment variables BEFORE any other imports
os.environ["OPENAI_API_KEY"] = "test-key-for-mocks"
os.environ["VECTOR_DATABASE"] = "qdrant"
os.environ["QDRANT_URL"] = "http://localhost:6333"
os.environ["MODEL_CHOICE"] = "gpt-4"
os.environ["SEARXNG_URL"] = "http://localhost:8081"
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "testpassword123"

# This ensures openai module gets the API key when imported
print("Test environment configured with mock API key")
