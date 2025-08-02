#!/usr/bin/env python3
"""Test OpenAI API key directly"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env.test with override=True to override shell environment
env_test_path = Path(__file__).parent.parent / ".env.test"
load_dotenv(env_test_path, override=True)

api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key loaded: {api_key[:20]}...{api_key[-10:]}")
print(f"API Key length: {len(api_key)}")

# Test with OpenAI
try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    # Simple test
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input="test"
    )
    print("✅ API key is valid! Embedding created successfully.")
    print(f"Embedding dimension: {len(response.data[0].embedding)}")
    
except Exception as e:
    print(f"❌ API key test failed: {e}")