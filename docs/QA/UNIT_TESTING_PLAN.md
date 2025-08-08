# Unit Testing Plan for Refactored Crawl4AI MCP Server

## Executive Summary

This document outlines a comprehensive unit testing strategy for the refactored Crawl4AI MCP Server modules. Following the successful refactoring from a monolithic 3,000-line file into a modular structure, unit test coverage must be dramatically improved from the current ~20% to achieve the target of 80%+ coverage.

**Current State**: Critical business logic modules have minimal to no unit test coverage
**Target State**: 80%+ unit test coverage with all critical paths tested
**Timeline**: 12-15 hours of focused development across 3 phases
**Priority**: CRITICAL - Core business logic must be tested immediately

## Current Coverage Assessment

### Coverage by Module

| Module | Current | Target | Priority | Risk Level |
|--------|---------|--------|----------|------------|
| **services/** | ~5% | 85% | CRITICAL | HIGH |
| **tools.py** | ~10% | 80% | CRITICAL | HIGH |
| **knowledge_graph/** | ~5% | 75% | HIGH | MEDIUM |
| **core/** | ~15% | 80% | HIGH | MEDIUM |
| **utils/** | ~20% | 85% | MEDIUM | LOW |
| **config/** | ~30% | 70% | LOW | LOW |
| **database/** | ~60% | 85% | MEDIUM | MEDIUM |
| **main.py** | ~15% | 70% | MEDIUM | MEDIUM |

## Testing Philosophy

### Core Principles

1. **Isolation**: Each unit test should test a single unit of functionality
2. **Independence**: Tests should not depend on external services or other tests
3. **Repeatability**: Tests must produce consistent results
4. **Performance**: Unit tests should complete in milliseconds
5. **Clarity**: Test names should clearly describe what is being tested

### Mock Strategy

All external dependencies must be mocked to ensure true unit testing:

- **External Services**: crawl4ai, OpenAI, SearXNG
- **Databases**: Qdrant, Supabase, Neo4j
- **Network Calls**: HTTP requests, API calls
- **File System**: Use temporary directories or mock file operations
- **Environment Variables**: Mock or patch as needed

## Phase 1: Critical Business Logic (Priority: CRITICAL)

### Timeline: 6-8 hours

### 1.1 Services Module Testing

#### test_services_crawling.py

```python
"""Unit tests for crawling service module."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from services.crawling import (
    crawl_with_config,
    crawl_batch,
    extract_markdown_content
)

class TestCrawlingService:
    """Test crawling service functions."""
    
    @pytest.mark.asyncio
    @patch('services.crawling.AsyncWebCrawler')
    async def test_crawl_with_config_success(self, mock_crawler):
        """Test successful crawl with configuration."""
        # Arrange
        mock_instance = AsyncMock()
        mock_crawler.return_value.__aenter__.return_value = mock_instance
        mock_instance.arun.return_value.markdown_v2.content = "Test content"
        
        # Act
        result = await crawl_with_config("https://example.com", {})
        
        # Assert
        assert result == "Test content"
        mock_instance.arun.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('services.crawling.AsyncWebCrawler')
    async def test_crawl_batch_multiple_urls(self, mock_crawler):
        """Test batch crawling of multiple URLs."""
        # Test implementation
        pass
    
    def test_extract_markdown_content(self):
        """Test markdown content extraction."""
        # Test implementation
        pass
```

#### test_services_search.py

```python
"""Unit tests for search service module."""
import pytest
from unittest.mock import Mock, patch
from services.search import search_web, parse_search_results

class TestSearchService:
    """Test search service functions."""
    
    @pytest.mark.asyncio
    @patch('services.search.httpx.AsyncClient')
    async def test_search_web_success(self, mock_client):
        """Test successful web search."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [{"url": "https://example.com", "title": "Test"}]
        }
        mock_client.return_value.get.return_value = mock_response
        
        # Act
        results = await search_web("test query")
        
        # Assert
        assert len(results) == 1
        assert results[0]["url"] == "https://example.com"
    
    def test_parse_search_results(self):
        """Test search results parsing."""
        # Test implementation
        pass
```

#### test_services_smart_crawl.py

```python
"""Unit tests for smart crawl service module."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from services.smart_crawl import smart_crawl_analysis

class TestSmartCrawlService:
    """Test smart crawl service functions."""
    
    @pytest.mark.asyncio
    @patch('services.smart_crawl.crawl_with_config')
    @patch('services.smart_crawl.openai_client')
    async def test_smart_crawl_analysis(self, mock_openai, mock_crawl):
        """Test smart crawl with AI analysis."""
        # Arrange
        mock_crawl.return_value = "Page content"
        mock_openai.chat.completions.create.return_value = Mock(
            choices=[Mock(message=Mock(content="Analysis result"))]
        )
        
        # Act
        result = await smart_crawl_analysis("https://example.com", "analyze")
        
        # Assert
        assert "Analysis result" in result
        mock_crawl.assert_called_once()
```

### 1.2 Tools Module Testing

#### test_tools_comprehensive.py

```python
"""Comprehensive unit tests for MCP tools."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from tools import register_tools

class TestMCPTools:
    """Test MCP tool definitions and registration."""
    
    def test_register_tools(self):
        """Test tool registration with MCP server."""
        mock_mcp = Mock()
        register_tools(mock_mcp)
        
        # Verify all tools are registered
        assert mock_mcp.tool.called
        # Count should match number of tools
        assert mock_mcp.tool.call_count >= 10
    
    @pytest.mark.asyncio
    @patch('tools.search_web')
    async def test_search_tool(self, mock_search):
        """Test search tool implementation."""
        # Mock the underlying service
        mock_search.return_value = [{"url": "test"}]
        
        # Import after mocking
        from tools import search
        
        # Test tool execution
        result = await search("test query")
        assert "url" in result[0]
    
    @pytest.mark.asyncio
    @patch('tools.crawl_with_config')
    async def test_scrape_tool(self, mock_crawl):
        """Test scrape tool implementation."""
        # Test implementation
        pass
```

## Phase 2: Infrastructure & Support (Priority: HIGH)

### Timeline: 4-5 hours

### 2.1 Core Module Testing

#### test_core_decorators.py

```python
"""Unit tests for core decorators."""
import pytest
from unittest.mock import Mock, patch
from core.decorators import track_request, retry_on_error

class TestDecorators:
    """Test decorator implementations."""
    
    @pytest.mark.asyncio
    async def test_track_request_decorator(self):
        """Test request tracking decorator."""
        mock_func = AsyncMock(return_value="result")
        decorated = track_request(mock_func)
        
        result = await decorated("arg1", kwarg="value")
        
        assert result == "result"
        mock_func.assert_called_once_with("arg1", kwarg="value")
    
    @pytest.mark.asyncio
    async def test_retry_on_error_decorator(self):
        """Test retry logic decorator."""
        # Test implementation
        pass
```

#### test_core_stdout_utils.py

```python
"""Unit tests for stdout utilities."""
import pytest
from unittest.mock import patch
from core.stdout_utils import SuppressStdout

class TestStdoutUtils:
    """Test stdout suppression utilities."""
    
    def test_suppress_stdout_context_manager(self):
        """Test stdout suppression."""
        with patch('sys.stdout') as mock_stdout:
            with SuppressStdout():
                print("This should be suppressed")
            
            # Verify stdout was redirected
            assert mock_stdout.write.called is False
```

#### test_core_context.py

```python
"""Unit tests for context management."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from core.context import crawl4ai_lifespan, ApplicationContext

class TestContext:
    """Test application context management."""
    
    @pytest.mark.asyncio
    async def test_lifespan_initialization(self):
        """Test lifespan context initialization."""
        mock_ctx = Mock()
        
        async for _ in crawl4ai_lifespan(mock_ctx):
            # Verify required attributes
            assert hasattr(mock_ctx, 'crawl4ai')
            assert hasattr(mock_ctx, 'openai')
            break
    
    def test_application_context_creation(self):
        """Test application context creation."""
        # Test implementation
        pass
```

### 2.2 Knowledge Graph Module Testing

#### test_knowledge_graph_handlers.py

```python
"""Unit tests for knowledge graph handlers."""
import pytest
from unittest.mock import Mock, patch
from knowledge_graph.handlers import (
    parse_repository,
    validate_script,
    detect_hallucinations
)

class TestKnowledgeGraphHandlers:
    """Test knowledge graph command handlers."""
    
    @patch('knowledge_graph.handlers.neo4j_client')
    def test_parse_repository(self, mock_neo4j):
        """Test repository parsing."""
        mock_neo4j.execute_query.return_value = ([], None, None)
        
        result = parse_repository("https://github.com/user/repo")
        
        assert result is not None
        mock_neo4j.execute_query.assert_called()
    
    @patch('knowledge_graph.handlers.validate_against_graph')
    def test_validate_script(self, mock_validate):
        """Test script validation."""
        mock_validate.return_value = {"valid": True}
        
        result = validate_script("print('hello')", "test.py")
        
        assert result["valid"] is True
```

#### test_knowledge_graph_queries.py

```python
"""Unit tests for knowledge graph queries."""
import pytest
from unittest.mock import Mock, patch
from knowledge_graph.queries import (
    find_similar_code,
    get_dependencies,
    analyze_patterns
)

class TestKnowledgeGraphQueries:
    """Test graph query functions."""
    
    @patch('knowledge_graph.queries.neo4j_client')
    def test_find_similar_code(self, mock_neo4j):
        """Test finding similar code patterns."""
        # Test implementation
        pass
```

### 2.3 Enhanced Utils Module Testing

#### test_utils_comprehensive.py

```python
"""Comprehensive unit tests for utility functions."""
import pytest
from utils.validation import (
    validate_url,
    validate_github_url,
    validate_script_path,
    sanitize_input
)
from utils.text_processing import (
    smart_chunk_markdown,
    extract_code_blocks,
    clean_text
)
from utils.url_helpers import (
    normalize_url,
    extract_domain,
    is_valid_url
)

class TestValidation:
    """Test validation utilities."""
    
    def test_validate_url(self):
        """Test URL validation."""
        assert validate_url("https://example.com") is None
        assert validate_url("invalid") is not None
    
    def test_sanitize_input(self):
        """Test input sanitization."""
        assert sanitize_input("<script>alert()</script>") == ""
        assert sanitize_input("valid text") == "valid text"

class TestTextProcessing:
    """Test text processing utilities."""
    
    def test_smart_chunk_markdown(self):
        """Test markdown chunking."""
        text = "# Header\n\n" + "word " * 500
        chunks = smart_chunk_markdown(text, chunk_size=1000)
        
        assert len(chunks) > 1
        assert all(len(chunk) <= 1500 for chunk in chunks)
    
    def test_extract_code_blocks(self):
        """Test code block extraction."""
        markdown = "```python\nprint('hello')\n```"
        blocks = extract_code_blocks(markdown)
        
        assert len(blocks) == 1
        assert blocks[0]["language"] == "python"
```

## Phase 3: Completeness & Quality (Priority: MEDIUM)

### Timeline: 2-3 hours

### 3.1 Config Module Testing

#### test_config_settings.py

```python
"""Unit tests for configuration management."""
import pytest
from unittest.mock import patch
from config.settings import Settings, get_settings

class TestSettings:
    """Test configuration settings."""
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_settings_initialization(self):
        """Test settings initialization from environment."""
        settings = Settings()
        
        assert settings.openai_api_key == 'test-key'
        assert settings.host == '0.0.0.0'  # default
        assert settings.port == 3000  # default
    
    def test_get_settings_singleton(self):
        """Test settings singleton pattern."""
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
```

### 3.2 Main Application Testing

#### test_main_application.py

```python
"""Unit tests for main application entry point."""
import pytest
from unittest.mock import Mock, patch
from main import create_app, start_server

class TestMainApplication:
    """Test main application functionality."""
    
    @patch('main.FastMCP')
    def test_create_app(self, mock_fastmcp):
        """Test application creation."""
        app = create_app()
        
        assert app is not None
        mock_fastmcp.assert_called_once()
    
    @patch('main.uvicorn.run')
    def test_start_server(self, mock_uvicorn):
        """Test server startup."""
        start_server()
        
        mock_uvicorn.assert_called_once()
```

### 3.3 Database Module Enhancement

#### test_database_operations.py

```python
"""Enhanced unit tests for database operations."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from database.rag_queries import (
    store_embeddings,
    search_similar,
    update_metadata
)

class TestRAGQueries:
    """Test RAG query operations."""
    
    @pytest.mark.asyncio
    @patch('database.rag_queries.qdrant_client')
    async def test_store_embeddings(self, mock_qdrant):
        """Test embedding storage."""
        mock_qdrant.upsert.return_value = True
        
        result = await store_embeddings("test", [0.1, 0.2])
        
        assert result is True
        mock_qdrant.upsert.assert_called_once()
```

## Testing Patterns & Best Practices

### 1. Async Testing Pattern

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async functionality."""
    # Use AsyncMock for async dependencies
    mock_dep = AsyncMock(return_value="result")
    
    # Test async function
    result = await function_under_test(mock_dep)
    
    # Assert
    assert result == "expected"
    mock_dep.assert_awaited_once()
```

### 2. Exception Testing Pattern

```python
def test_error_handling():
    """Test error handling."""
    with pytest.raises(MCPToolError) as exc_info:
        function_that_raises()
    
    assert "expected message" in str(exc_info.value)
```

### 3. Mock External Service Pattern

```python
@patch('module.external_service')
def test_with_mocked_service(mock_service):
    """Test with mocked external service."""
    # Configure mock
    mock_service.call.return_value = {"status": "success"}
    
    # Test
    result = function_using_service()
    
    # Verify
    assert result["status"] == "success"
    mock_service.call.assert_called_with(expected_args)
```

### 4. Parametrized Testing Pattern

```python
@pytest.mark.parametrize("input,expected", [
    ("https://example.com", True),
    ("invalid", False),
    ("http://test.org", True),
])
def test_url_validation(input, expected):
    """Test URL validation with multiple inputs."""
    assert is_valid_url(input) == expected
```

## Mock Strategy Guidelines

### External Service Mocks

#### OpenAI Mock

```python
@patch('openai.AsyncOpenAI')
def mock_openai(mock_client):
    mock_instance = Mock()
    mock_client.return_value = mock_instance
    mock_instance.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="AI response"))]
    )
    return mock_instance
```

#### Crawl4AI Mock

```python
@patch('crawl4ai.AsyncWebCrawler')
def mock_crawler(mock_class):
    mock_instance = AsyncMock()
    mock_class.return_value.__aenter__.return_value = mock_instance
    mock_instance.arun.return_value.markdown_v2.content = "Content"
    return mock_instance
```

#### Database Mock

```python
@patch('qdrant_client.QdrantClient')
def mock_qdrant(mock_client):
    mock_instance = Mock()
    mock_client.return_value = mock_instance
    mock_instance.search.return_value = [Mock(score=0.9)]
    return mock_instance
```

## Quality Metrics & Success Criteria

### Coverage Targets

| Metric | Current | Target | Required |
|--------|---------|--------|----------|
| Overall Line Coverage | ~20% | 80% | Yes |
| Branch Coverage | ~15% | 70% | Yes |
| Critical Path Coverage | ~10% | 100% | Yes |
| Error Handling Coverage | ~5% | 90% | Yes |

### Quality Gates

1. **Pre-Commit Checks**
   - All unit tests must pass
   - No decrease in coverage
   - Test execution time < 30 seconds

2. **CI/CD Requirements**
   - Coverage report generation
   - Failure on coverage decrease
   - Performance regression detection

3. **Code Review Criteria**
   - New code must have tests
   - Mock strategy must be followed
   - Test naming conventions enforced

### Performance Requirements

- Unit test suite execution: < 30 seconds
- Individual test execution: < 100ms
- Memory usage: < 500MB for full suite
- Parallel execution support

## Implementation Timeline

### Week 1: Critical Business Logic

- **Day 1-2**: Services module (crawling, search, smart_crawl)
- **Day 3**: Tools module comprehensive testing
- **Deliverable**: 60% coverage for critical modules

### Week 2: Infrastructure

- **Day 4**: Core module (decorators, context, stdout)
- **Day 5**: Knowledge graph module
- **Day 6**: Utils and config enhancement
- **Deliverable**: 75% overall coverage

### Week 3: Polish & Integration

- **Day 7**: Database module enhancement
- **Day 8**: Main application and integration points
- **Day 9-10**: Gap analysis and completion
- **Deliverable**: 80%+ coverage achieved

## Test File Naming Convention

```
tests/
├── unit/                          # Pure unit tests
│   ├── test_core_*.py            # Core module tests
│   ├── test_services_*.py        # Services module tests
│   ├── test_utils_*.py           # Utils module tests
│   ├── test_knowledge_graph_*.py # Knowledge graph tests
│   ├── test_database_*.py        # Database module tests
│   ├── test_config_*.py          # Config module tests
│   └── test_tools_*.py           # Tools module tests
├── integration/                   # Integration tests (separate plan)
└── fixtures/                      # Shared test fixtures
```

## Continuous Improvement

### Monthly Review

- Coverage trend analysis
- Test execution time optimization
- Flaky test identification and fixes
- Mock strategy refinement

### Quarterly Goals

- Q1: Achieve 80% coverage
- Q2: Implement mutation testing
- Q3: Add property-based testing
- Q4: Achieve 90% coverage

## Conclusion

This unit testing plan provides a clear path to achieving comprehensive test coverage for the refactored Crawl4AI MCP Server. By following the phased approach and utilizing the provided patterns and mock strategies, the team can systematically improve code quality and reliability while maintaining development velocity.

**Next Steps**:

1. Review and approve this plan
2. Create test file structure
3. Begin Phase 1 implementation
4. Set up coverage reporting in CI/CD
5. Schedule weekly progress reviews

For integration testing strategy, see: `tests/plans/INTEGRATION_TESTING_PLAN.md` (to be created)
