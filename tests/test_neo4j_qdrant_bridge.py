#!/usr/bin/env python3
"""
Test script for the Neo4j-Qdrant bridge integration.

This script tests the complete workflow:
1. Parse a repository into Neo4j knowledge graph
2. Extract code examples from Neo4j
3. Generate embeddings and index in Qdrant
4. Perform searches on the indexed code
5. Validate the bridge functionality
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_neo4j_qdrant_bridge():
    """Test the complete Neo4j-Qdrant bridge functionality."""

    print("🧪 Testing Neo4j-Qdrant Bridge Integration")
    print("=" * 50)

    # Check environment variables
    required_env_vars = [
        "NEO4J_URI",
        "NEO4J_PASSWORD",
        "QDRANT_URL",
        "OPENAI_API_KEY",
    ]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        return False

    try:
        # Import components
        from database.factory import create_database_client
        from knowledge_graph.code_extractor import extract_repository_code
        from knowledge_graphs.parse_repo_into_neo4j import RepositoryExtractor
        from utils import create_embeddings_batch

        print("✅ Successfully imported all required modules")

        # Initialize Neo4j repository extractor
        print("\n1. 🗄️ Initializing Neo4j Repository Extractor...")
        repo_extractor = RepositoryExtractor()
        await repo_extractor.initialize()
        print("✅ Neo4j connection established")

        # Initialize Qdrant database client
        print("\n2. 🔍 Initializing Qdrant Database Client...")
        database_client = create_database_client()
        await database_client.initialize()
        print("✅ Qdrant connection established")

        # Check for existing repositories in Neo4j
        print("\n3. 📚 Checking for repositories in Neo4j...")
        async with repo_extractor.driver.session() as session:
            result = await session.run(
                "MATCH (r:Repository) RETURN r.name as name LIMIT 5"
            )
            repos = []
            async for record in result:
                repos.append(record["name"])

        if not repos:
            print(
                "⚠️ No repositories found in Neo4j. You need to parse a repository first."
            )
            print(
                "   Example: Parse a repository using the MCP tool or the parse_repo_into_neo4j.py script"
            )
            return False

        print(f"✅ Found {len(repos)} repositories: {', '.join(repos)}")

        # Test with the first repository
        test_repo = repos[0]
        print(f"\n4. 🔧 Testing code extraction from repository: {test_repo}")

        # Extract code examples from Neo4j
        extraction_result = await extract_repository_code(repo_extractor, test_repo)

        if not extraction_result["success"]:
            print(f"❌ Code extraction failed: {extraction_result.get('error')}")
            return False

        code_examples = extraction_result["code_examples"]
        print(f"✅ Extracted {len(code_examples)} code examples")
        print(f"   - Classes: {extraction_result['extraction_summary']['classes']}")
        print(f"   - Methods: {extraction_result['extraction_summary']['methods']}")
        print(f"   - Functions: {extraction_result['extraction_summary']['functions']}")

        if not code_examples:
            print(
                "⚠️ No code examples extracted. Repository may be empty or have no public classes/methods."
            )
            return False

        # Test a subset for efficiency (first 5 examples)
        test_examples = code_examples[:5]

        print(
            f"\n5. 🧠 Generating embeddings for {len(test_examples)} code examples..."
        )
        embedding_texts = [example["embedding_text"] for example in test_examples]
        embeddings = create_embeddings_batch(embedding_texts)

        if len(embeddings) != len(test_examples):
            print(
                f"❌ Embedding count mismatch: got {len(embeddings)}, expected {len(test_examples)}"
            )
            return False

        print("✅ Embeddings generated successfully")

        # Clean up any existing code examples for this repository
        print(f"\n6. 🧹 Cleaning up existing code examples for {test_repo}...")
        try:
            await database_client.delete_repository_code_examples(test_repo)
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

        # Store code examples in Qdrant
        print(f"\n7. 💾 Storing {len(test_examples)} code examples in Qdrant...")

        # Prepare data for Qdrant storage
        urls = []
        chunk_numbers = []
        code_texts = []
        summaries = []
        metadatas = []
        source_ids = []

        for i, example in enumerate(test_examples):
            pseudo_url = f"neo4j://repository/{test_repo}/{example['code_type']}/{example['name']}"
            urls.append(pseudo_url)
            chunk_numbers.append(i)
            code_texts.append(example["code_text"])
            summaries.append(f"{example['code_type'].title()}: {example['full_name']}")
            metadatas.append(example["metadata"])
            source_ids.append(test_repo)

        # Store in Qdrant
        await database_client.add_code_examples(
            urls=urls,
            chunk_numbers=chunk_numbers,
            code_examples=code_texts,
            summaries=summaries,
            metadatas=metadatas,
            embeddings=embeddings,
            source_ids=source_ids,
        )

        print("✅ Code examples stored in Qdrant successfully")

        # Test semantic search
        print("\n8. 🔍 Testing semantic search on indexed code...")

        # Generate a search query from the first example
        first_example = test_examples[0]
        search_query = f"{first_example['code_type']} {first_example['name']}"

        print(f"   Search query: '{search_query}'")

        # Generate embedding for search query
        search_embeddings = create_embeddings_batch([search_query])
        search_embedding = search_embeddings[0]

        # Search in Qdrant
        search_results = await database_client.search_code_examples(
            query_embedding=search_embedding,
            match_count=3,
            filter_metadata={"repository_name": test_repo},
        )

        if not search_results:
            print("❌ No search results found")
            return False

        print(f"✅ Found {len(search_results)} search results")
        for i, result in enumerate(search_results):
            print(
                f"   {i + 1}. {result.get('metadata', {}).get('code_type', 'unknown')}: "
                f"{result.get('metadata', {}).get('name', 'unknown')} "
                f"(similarity: {result.get('similarity', 0):.3f})"
            )

        # Test repository-specific queries
        print("\n9. 📊 Testing repository-specific queries...")

        # Get all code examples for the repository
        repo_examples = await database_client.get_repository_code_examples(
            repo_name=test_repo,
            match_count=10,
        )

        print(f"✅ Found {len(repo_examples)} total code examples in repository")

        # Test search by signature
        if test_examples:
            first_method = next(
                (ex for ex in test_examples if ex["code_type"] == "method"), None
            )
            if first_method:
                print("\n10. 🎯 Testing signature-based search...")
                signature_results = await database_client.search_code_by_signature(
                    method_name=first_method["name"],
                    repo_filter=test_repo,
                )
                print(
                    f"✅ Found {len(signature_results)} results for method '{first_method['name']}'"
                )

        # Update source information
        print("\n11. 📈 Updating source information...")
        await database_client.update_source_info(
            source_id=test_repo,
            summary=f"Test repository with {extraction_result['extraction_summary']['classes']} classes, "
            f"{extraction_result['extraction_summary']['methods']} methods, "
            f"{extraction_result['extraction_summary']['functions']} functions",
            word_count=sum(
                len(example["code_text"].split()) for example in test_examples
            ),
        )
        print("✅ Source information updated")

        # Final validation
        print("\n12. ✅ Final Validation...")

        # Check that we can retrieve the stored examples
        validation_search = await database_client.search_code_examples(
            query_embedding=search_embedding,
            match_count=1,
            filter_metadata={"repository_name": test_repo},
        )

        if not validation_search:
            print("❌ Validation failed: Cannot retrieve stored examples")
            return False

        print("✅ Bridge validation successful!")

        # Summary
        print(f"\n{'=' * 50}")
        print("🎉 Neo4j-Qdrant Bridge Test Results")
        print(f"{'=' * 50}")
        print(f"✅ Repository tested: {test_repo}")
        print(f"✅ Code examples extracted: {len(code_examples)}")
        print(f"✅ Examples indexed: {len(test_examples)}")
        print(f"✅ Embeddings generated: {len(embeddings)}")
        print(f"✅ Search results: {len(search_results)}")
        print(f"✅ Repository queries: {len(repo_examples)}")
        print("\n🚀 Neo4j-Qdrant bridge is working correctly!")

        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logger.exception("Test error details:")
        return False


async def main():
    """Main test function."""
    try:
        success = await test_neo4j_qdrant_bridge()
        if success:
            print(
                "\n🎉 All tests passed! The Neo4j-Qdrant bridge is working correctly."
            )
            sys.exit(0)
        else:
            print("\n❌ Tests failed. Please check the error messages above.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        logger.exception("Unexpected error details:")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
