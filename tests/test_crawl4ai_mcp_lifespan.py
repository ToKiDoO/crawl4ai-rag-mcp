"""Tests for crawl4ai_mcp lifespan and initialization."""
import pytest
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestLifespan:
    """Test the lifespan and initialization functions."""
    
    @pytest.mark.asyncio
    @patch('src.crawl4ai_mcp.AsyncWebCrawler')
    @patch('src.crawl4ai_mcp.create_and_initialize_database')
    @patch('src.crawl4ai_mcp.CrossEncoder')
    async def test_crawl4ai_lifespan_basic(self, mock_cross_encoder, mock_create_db, mock_crawler_class):
        """Test basic lifespan initialization."""
        from src.crawl4ai_mcp import crawl4ai_lifespan
        from fastmcp import FastMCP
        
        # Mock crawler
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value = mock_crawler
        
        # Mock database
        mock_db = AsyncMock()
        mock_create_db.return_value = mock_db
        
        # Mock server
        mock_server = Mock(spec=FastMCP)
        
        # Test lifespan
        async with crawl4ai_lifespan(mock_server) as context:
            assert context.crawler == mock_crawler
            assert context.database_client == mock_db
            assert context.reranking_model is None  # Default is disabled
            assert context.knowledge_validator is None
            assert context.repo_extractor is None
            
        # Verify cleanup
        mock_crawler.__aexit__.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.crawl4ai_mcp.AsyncWebCrawler')
    @patch('src.crawl4ai_mcp.create_and_initialize_database')
    @patch('src.crawl4ai_mcp.CrossEncoder')
    async def test_crawl4ai_lifespan_with_reranking(self, mock_cross_encoder, mock_create_db, mock_crawler_class):
        """Test lifespan with reranking enabled."""
        from src.crawl4ai_mcp import crawl4ai_lifespan
        from fastmcp import FastMCP
        
        # Mock components
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value = mock_crawler
        mock_db = AsyncMock()
        mock_create_db.return_value = mock_db
        mock_reranker = Mock()
        mock_cross_encoder.return_value = mock_reranker
        mock_server = Mock(spec=FastMCP)
        
        # Enable reranking
        with patch.dict('os.environ', {'USE_RERANKING': 'true'}):
            async with crawl4ai_lifespan(mock_server) as context:
                assert context.reranking_model == mock_reranker
                mock_cross_encoder.assert_called_once_with("cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    @pytest.mark.asyncio
    @patch('src.crawl4ai_mcp.AsyncWebCrawler')
    @patch('src.crawl4ai_mcp.create_and_initialize_database')
    @patch('src.crawl4ai_mcp.KnowledgeGraphValidator')
    @patch('src.crawl4ai_mcp.DirectNeo4jExtractor')
    async def test_crawl4ai_lifespan_with_knowledge_graph(self, mock_extractor_class, mock_validator_class, mock_create_db, mock_crawler_class):
        """Test lifespan with knowledge graph enabled."""
        from src.crawl4ai_mcp import crawl4ai_lifespan
        from fastmcp import FastMCP
        
        # Mock components
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value = mock_crawler
        mock_db = AsyncMock()
        mock_create_db.return_value = mock_db
        
        mock_validator = AsyncMock()
        mock_validator_class.return_value = mock_validator
        mock_extractor = AsyncMock()
        mock_extractor_class.return_value = mock_extractor
        
        mock_server = Mock(spec=FastMCP)
        
        # Enable knowledge graph
        with patch.dict('os.environ', {
            'USE_KNOWLEDGE_GRAPH': 'true',
            'NEO4J_URI': 'bolt://localhost:7687',
            'NEO4J_USER': 'neo4j',
            'NEO4J_PASSWORD': 'password'
        }):
            async with crawl4ai_lifespan(mock_server) as context:
                assert context.knowledge_validator == mock_validator
                assert context.repo_extractor == mock_extractor
                
                # Verify initialization
                mock_validator.initialize.assert_called_once()
                mock_extractor.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.crawl4ai_mcp.AsyncWebCrawler')
    @patch('src.crawl4ai_mcp.create_and_initialize_database')
    async def test_crawl4ai_lifespan_knowledge_graph_failure(self, mock_create_db, mock_crawler_class):
        """Test lifespan when knowledge graph initialization fails."""
        from src.crawl4ai_mcp import crawl4ai_lifespan
        from fastmcp import FastMCP
        
        # Mock components
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value = mock_crawler
        mock_db = AsyncMock()
        mock_create_db.return_value = mock_db
        mock_server = Mock(spec=FastMCP)
        
        # Enable knowledge graph but with missing credentials
        with patch.dict('os.environ', {
            'USE_KNOWLEDGE_GRAPH': 'true',
            # Missing NEO4J credentials
        }):
            async with crawl4ai_lifespan(mock_server) as context:
                # Should still work but without knowledge graph
                assert context.crawler == mock_crawler
                assert context.database_client == mock_db
                assert context.knowledge_validator is None
                assert context.repo_extractor is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])