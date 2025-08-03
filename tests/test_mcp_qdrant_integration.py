"""
End-to-end integration test for MCP server with Qdrant.
Tests the complete flow from scraping to RAG queries.
"""
import pytest
import asyncio
import os
import sys
import json
from typing import Dict, Any
from unittest.mock import patch, AsyncMock, MagicMock

from .mcp_test_utils import (
    create_test_context,
    generate_test_urls,
    generate_test_markdown,
    generate_test_embedding
)


@pytest.mark.integration
class TestMCPQdrantIntegration:
    """Test MCP server integration with Qdrant"""
    
    @pytest.fixture
    async def setup_environment(self):
        """Set up test environment"""
        # Set Qdrant as vector database
        os.environ['VECTOR_DATABASE'] = 'qdrant'
        os.environ['QDRANT_URL'] = 'http://localhost:6333'
        os.environ['OPENAI_API_KEY'] = 'test-key'
        
        yield
        
        # Cleanup
        os.environ.pop('VECTOR_DATABASE', None)
        os.environ.pop('QDRANT_URL', None)
    
    @pytest.fixture
    async def mock_dependencies(self):
        """Mock external dependencies"""
        with patch('crawl4ai_mcp.AsyncWebCrawler') as mock_crawler_class, \
             patch('utils_refactored.create_embeddings_batch') as mock_embeddings, \
             patch('crawl4ai_mcp.CrossEncoder') as mock_crossencoder_class:
            
            # Mock crawler
            mock_crawler = AsyncMock()
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            # Mock crawl result
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.markdown = generate_test_markdown("medium")
            mock_result.cleaned_html = "<html><body>Test content</body></html>"
            mock_result.media = {"images": [], "videos": [], "audios": []}
            mock_result.links = {"internal": [], "external": []}
            mock_result.metadata = {}
            mock_result.screenshot = None
            mock_result.pdf = None
            mock_result.extracted_content = None
            mock_result.error_message = None
            mock_crawler.arun.return_value = mock_result
            
            # Mock embeddings
            mock_embeddings.return_value = [generate_test_embedding()]
            
            # Mock reranking model
            mock_reranker = MagicMock()
            mock_reranker.predict.return_value = [[0.9, 0.8, 0.7]]
            mock_crossencoder_class.return_value = mock_reranker
            
            yield {
                'crawler': mock_crawler,
                'crawler_class': mock_crawler_class,
                'embeddings': mock_embeddings,
                'reranker': mock_reranker
            }
    
    @pytest.mark.asyncio
    async def test_complete_flow(self, setup_environment, mock_dependencies):
        """Test complete flow: scrape -> store -> search -> RAG query"""
        from crawl4ai_mcp import (
            scrape_urls,
            get_available_sources,
            perform_rag_query,
            search_code_examples
        )
        from database.factory import create_and_initialize_database
        
        # Create test context with mocked database
        mock_db = AsyncMock()
        mock_db.add_documents = AsyncMock()
        mock_db.update_source_info = AsyncMock()
        mock_db.get_sources = AsyncMock(return_value=[])
        mock_db.search_documents = AsyncMock(return_value=[
            {
                "id": "test-1",
                "url": "https://example.com",
                "content": "Test content about Python",
                "similarity": 0.9,
                "chunk_number": 0,
                "metadata": {}
            }
        ])
        
        # Patch database creation
        with patch('crawl4ai_mcp.create_and_initialize_database', return_value=mock_db):
            ctx = create_test_context(
                crawler=mock_dependencies['crawler'],
                database_client=mock_db,
                reranking_model=mock_dependencies['reranker']
            )
            
            # Step 1: Scrape URLs
            test_url = "https://example.com/test"
            result = await scrape_urls(ctx, url=test_url)
            
            # Verify scraping
            assert "Successfully scraped 1 URL" in result
            mock_dependencies['crawler'].arun.assert_called_once()
            mock_db.add_documents.assert_called_once()
            
            # Verify document storage call
            add_docs_call = mock_db.add_documents.call_args
            assert add_docs_call is not None
            args = add_docs_call[0]
            assert len(args[0]) > 0  # urls
            assert len(args[2]) > 0  # contents
            assert len(args[4]) > 0  # embeddings
            
            # Step 2: Get available sources
            sources_result = await get_available_sources(ctx)
            mock_db.get_sources.assert_called_once()
            
            # Step 3: Perform RAG query
            query = "Python programming"
            rag_result = await perform_rag_query(ctx, query=query, match_count=3)
            
            # Verify RAG query
            assert "Found 1 relevant" in rag_result
            mock_db.search_documents.assert_called()
            
            # Verify search was called with embedding
            search_call = mock_db.search_documents.call_args
            assert search_call is not None
            assert len(search_call[0][0]) == 1536  # embedding vector
            
            # Step 4: Search code examples (should return no results)
            mock_db.search_code_examples = AsyncMock(return_value=[])
            code_result = await search_code_examples(ctx, query="Python function")
            assert "No code examples found" in code_result
    
    @pytest.mark.asyncio
    async def test_error_handling(self, setup_environment):
        """Test error handling in integration"""
        from crawl4ai_mcp import scrape_urls
        
        # Mock crawler that fails
        mock_crawler = AsyncMock()
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Connection timeout"
        mock_crawler.arun.return_value = mock_result
        
        # Mock database
        mock_db = AsyncMock()
        
        ctx = create_test_context(
            crawler=mock_crawler,
            database_client=mock_db
        )
        
        # Test scraping failure
        with patch('crawl4ai_mcp.AsyncWebCrawler') as mock_crawler_class:
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
            
            result = await scrape_urls(ctx, url="https://example.com/fail")
            
            # Should handle error gracefully
            assert "error" in result or "false" in result
            # Should not try to store documents
            mock_db.add_documents.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_batch_processing(self, setup_environment, mock_dependencies):
        """Test batch URL processing"""
        from crawl4ai_mcp import scrape_urls
        
        # Create multiple test URLs
        test_urls = generate_test_urls(5)
        
        # Mock database
        mock_db = AsyncMock()
        mock_db.add_documents = AsyncMock()
        mock_db.update_source_info = AsyncMock()
        
        ctx = create_test_context(
            crawler=mock_dependencies['crawler'],
            database_client=mock_db
        )
        
        with patch('crawl4ai_mcp.create_and_initialize_database', return_value=mock_db):
            # Scrape multiple URLs
            result = await scrape_urls(ctx, url=test_urls, max_concurrent=3)
            
            # Verify batch processing
            assert "Successfully scraped 5 URLs" in result
            assert mock_dependencies['crawler'].arun.call_count == 5
            
            # Verify documents were added
            assert mock_db.add_documents.call_count > 0
    
    @pytest.mark.asyncio
    async def test_qdrant_specific_features(self, setup_environment):
        """Test Qdrant-specific features"""
        from database.qdrant_adapter import QdrantAdapter
        
        # Create adapter
        adapter = QdrantAdapter(url="http://localhost:6333")
        
        # Mock Qdrant client
        mock_client = AsyncMock()
        mock_client.get_collection = MagicMock(side_effect=Exception("Not found"))
        mock_client.create_collection = MagicMock()
        adapter.client = mock_client
        
        # Test initialization
        await adapter.initialize()
        
        # Should create collections
        assert mock_client.create_collection.call_count == 3  # crawled_pages, code_examples, sources
        
        # Test search with filters
        mock_client.search = AsyncMock(return_value=[])
        await adapter.search_documents(
            query_embedding=generate_test_embedding(),
            match_count=5,
            source_filter="example.com"
        )
        
        # Verify search was called with filter
        search_call = mock_client.search.call_args
        assert search_call is not None
        assert search_call[1]['query_filter'] is not None
    
    @pytest.mark.asyncio
    async def test_reranking_integration(self, setup_environment, mock_dependencies):
        """Test reranking functionality"""
        from crawl4ai_mcp import perform_rag_query
        
        # Mock database with multiple results
        mock_db = AsyncMock()
        mock_db.search_documents = AsyncMock(return_value=[
            {
                "id": f"test-{i}",
                "url": f"https://example.com/page{i}",
                "content": f"Test content {i}",
                "similarity": 0.7 + i * 0.05,
                "chunk_number": 0,
                "metadata": {}
            }
            for i in range(5)
        ])
        
        ctx = create_test_context(
            database_client=mock_db,
            reranking_model=mock_dependencies['reranker']
        )
        
        # Enable reranking
        with patch.dict(os.environ, {'USE_RERANKING': 'true'}):
            result = await perform_rag_query(ctx, query="test query", match_count=3)
            
            # Verify reranking was used
            mock_dependencies['reranker'].predict.assert_called_once()
            
            # Results should be reordered based on reranking scores
            assert "relevant documents" in result


@pytest.mark.integration
class TestMCPServerStartup:
    """Test MCP server startup with Qdrant"""
    
    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test that MCP server initializes correctly with Qdrant"""
        with patch.dict(os.environ, {
            'VECTOR_DATABASE': 'qdrant',
            'QDRANT_URL': 'http://localhost:6333',
            'OPENAI_API_KEY': 'test-key'
        }):
            # Import should succeed
            from crawl4ai_mcp import mcp
            
            # Server should be initialized
            assert mcp is not None
            
            # Tools should be registered
            tools = mcp._tool_manager._tools
            assert len(tools) > 0
            
            # Check critical tools exist
            assert 'scrape_urls' in tools
            assert 'perform_rag_query' in tools
            assert 'search_code_examples' in tools


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])