#!/usr/bin/env python3
"""
Simple runner to test the fixed integration tests with .env.test loaded.
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load the test environment file
env_test_path = Path(__file__).parent.parent / '.env.test'
load_dotenv(env_test_path, override=True)

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

# Set test environment
os.environ["VECTOR_DATABASE"] = "qdrant"
os.environ["QDRANT_URL"] = "http://localhost:6333"

async def run_simple_test():
    """Run a simple integration test"""
    print("Running simple Qdrant integration test...")
    print(f"Using OpenAI API key: {os.getenv('OPENAI_API_KEY', 'NOT SET')[:20]}...")
    
    try:
        from database.factory import create_database_client
        from utils_refactored import (
            create_embeddings_batch,
            add_documents_to_database,
            search_documents
        )
        
        # Create database client
        print("Creating Qdrant client...")
        db = create_database_client()
        await db.initialize()
        print("✓ Database initialized")
        
        # Test data
        test_doc = {
            "url": "https://test.com/doc1",
            "content": "This is a test document about Python programming and async operations.",
            "chunk_number": 0,
            "metadata": {"title": "Test Doc", "type": "integration_test"}
        }
        
        # Add document
        print("Adding test document...")
        await add_documents_to_database(
            database=db,
            urls=[test_doc["url"]],
            chunk_numbers=[test_doc["chunk_number"]],
            contents=[test_doc["content"]],
            metadatas=[test_doc["metadata"]],
            url_to_full_document={test_doc["url"]: test_doc["content"]}
        )
        print("✓ Document added")
        
        # Search for document
        print("Searching for document...")
        results = await search_documents(
            database=db,
            query="Python async programming",
            match_count=5
        )
        
        if results:
            print(f"✓ Found {len(results)} results")
            print(f"  First result URL: {results[0].get('url', 'N/A')}")
            print(f"  Score: {results[0].get('score', 'N/A')}")
        else:
            print("✗ No results found")
        
        # Test cleanup
        print("Cleaning up...")
        await db.delete_documents_by_url(test_doc["url"])
        print("✓ Cleanup complete")
        
        print("\n✅ Integration test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Check if Qdrant is running
    import requests
    try:
        response = requests.get("http://localhost:6333/healthz")
        if response.status_code != 200:
            print("⚠️  Qdrant is not healthy. Please start it with:")
            print("   docker compose -f docker-compose.test.yml up -d qdrant")
            sys.exit(1)
    except:
        print("❌ Qdrant is not running. Please start it with:")
        print("   docker compose -f docker-compose.test.yml up -d qdrant")
        sys.exit(1)
    
    # Run the test
    success = asyncio.run(run_simple_test())
    sys.exit(0 if success else 1)