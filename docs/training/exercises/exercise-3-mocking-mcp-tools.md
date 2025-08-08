# Exercise 3: Mocking MCP Tools and Complex Dependencies

**Duration**: 75 minutes  
**Difficulty**: Intermediate-Advanced  
**Prerequisites**: Completion of Exercises 1 & 2, understanding of dependency injection and mocking patterns

## Learning Objectives

After completing this exercise, you will be able to:

- Mock complex dependency chains effectively
- Test MCP tools with realistic external service interactions
- Create stateful mocks for database and AI service operations
- Handle authentication and credential mocking securely
- Test error propagation through multiple layers
- Use advanced mocking patterns like context managers and decorators

## Exercise Overview

You'll build and test a more realistic MCP server that interacts with multiple external services: vector databases, AI APIs, search engines, and caching layers. This mirrors the real Crawl4AI architecture.

## Part 1: Complex Dependency Architecture (20 minutes)

### Task 3.1: Create a realistic MCP server with dependencies

Create `exercises/complex_mcp_server.py`:

```python
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, AsyncContextManager
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
import hashlib

# External service interfaces (would normally be separate packages)
class VectorDatabase:
    """Interface for vector database operations"""
    async def store_embeddings(self, documents: List[Dict]) -> List[str]:
        raise NotImplementedError
    
    async def search_similar(self, query_embedding: List[float], limit: int = 10) -> List[Dict]:
        raise NotImplementedError
    
    async def delete_by_url(self, url: str) -> bool:
        raise NotImplementedError

class AIEmbeddingService:
    """Interface for AI embedding generation"""
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError
    
    async def rerank_results(self, query: str, documents: List[Dict]) -> List[Dict]:
        raise NotImplementedError

class SearchEngine:
    """Interface for web search"""
    async def search(self, query: str, num_results: int = 10) -> List[Dict]:
        raise NotImplementedError

class CacheService:
    """Interface for caching"""
    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        raise NotImplementedError

# Context and server implementation
@dataclass
class ComplexServerContext:
    """Server context with multiple dependencies"""
    vector_db: VectorDatabase
    ai_service: AIEmbeddingService  
    search_engine: SearchEngine
    cache: CacheService
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Connection pools and shared state
    _connection_pool: Optional[Any] = None
    _request_count: int = 0
    
    async def initialize(self):
        """Initialize expensive resources"""
        # Simulate expensive initialization
        await asyncio.sleep(0.1)
        self._connection_pool = "initialized"
    
    async def cleanup(self):
        """Clean up resources"""
        self._connection_pool = None

class ComplexMCPServer:
    """MCP server with realistic dependency patterns"""
    
    def __init__(self, context: ComplexServerContext):
        self.context = context
        self._health_status = "starting"
    
    async def startup(self):
        """Server startup sequence"""
        await self.context.initialize()
        self._health_status = "healthy"
    
    async def shutdown(self):
        """Server shutdown sequence"""
        await self.context.cleanup()
        self._health_status = "stopped"
    
    async def smart_search(self, ctx, query: str, use_ai: bool = True, max_results: int = 10) -> Dict:
        """Intelligent search combining web search with AI reranking"""
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")
        
        # Increment request counter
        self.context._request_count += 1
        
        # Check cache first
        cache_key = f"search:{hashlib.md5(query.encode()).hexdigest()}"
        cached_result = await self.context.cache.get(cache_key)
        if cached_result:
            return {
                'query': query,
                'results': cached_result,
                'source': 'cache',
                'ai_enhanced': False
            }
        
        try:
            # Perform web search
            search_results = await self.context.search_engine.search(query, max_results * 2)
            
            if use_ai and search_results:
                # Generate query embedding
                query_embeddings = await self.context.ai_service.generate_embeddings([query])
                query_embedding = query_embeddings[0]
                
                # Rerank results using AI
                reranked_results = await self.context.ai_service.rerank_results(query, search_results)
                final_results = reranked_results[:max_results]
            else:
                final_results = search_results[:max_results]
            
            # Cache results
            await self.context.cache.set(cache_key, final_results, ttl=1800)
            
            return {
                'query': query,
                'results': final_results,
                'source': 'live',
                'ai_enhanced': use_ai,
                'result_count': len(final_results)
            }
            
        except Exception as e:
            # Log error (in real system) and return fallback
            return {
                'query': query,
                'results': [],
                'source': 'error',
                'error': str(e),
                'ai_enhanced': False
            }
    
    async def store_and_index(self, ctx, documents: List[Dict]) -> Dict:
        """Store documents and create vector embeddings"""
        if not documents:
            return {'stored_count': 0, 'indexed_count': 0}
        
        stored_docs = []
        failed_docs = []
        
        for doc in documents:
            try:
                # Validate document structure
                if not all(key in doc for key in ['url', 'content']):
                    failed_docs.append({'doc': doc, 'error': 'Missing required fields'})
                    continue
                
                # Generate content hash for deduplication
                content_hash = hashlib.md5(doc['content'].encode()).hexdigest()
                doc['content_hash'] = content_hash
                
                stored_docs.append(doc)
                
            except Exception as e:
                failed_docs.append({'doc': doc, 'error': str(e)})
        
        if not stored_docs:
            return {
                'stored_count': 0,
                'indexed_count': 0,
                'failed_count': len(failed_docs),
                'errors': failed_docs
            }
        
        try:
            # Generate embeddings for all content
            content_texts = [doc['content'] for doc in stored_docs]
            embeddings = await self.context.ai_service.generate_embeddings(content_texts)
            
            # Prepare documents for vector storage
            vector_docs = []
            for doc, embedding in zip(stored_docs, embeddings):
                vector_doc = {
                    **doc,
                    'embedding': embedding,
                    'timestamp': time.time()
                }
                vector_docs.append(vector_doc)
            
            # Store in vector database
            doc_ids = await self.context.vector_db.store_embeddings(vector_docs)
            
            return {
                'stored_count': len(stored_docs),
                'indexed_count': len(doc_ids),
                'failed_count': len(failed_docs),
                'document_ids': doc_ids,
                'errors': failed_docs if failed_docs else None
            }
            
        except Exception as e:
            return {
                'stored_count': 0,
                'indexed_count': 0,
                'failed_count': len(documents),
                'error': f"Storage failed: {str(e)}"
            }
    
    async def semantic_search(self, ctx, query: str, limit: int = 10, threshold: float = 0.7) -> Dict:
        """Perform semantic search using vector embeddings"""
        if not query:
            raise ValueError("Query cannot be empty")
        
        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")
        
        try:
            # Generate query embedding
            query_embeddings = await self.context.ai_service.generate_embeddings([query])
            query_embedding = query_embeddings[0]
            
            # Search vector database
            results = await self.context.vector_db.search_similar(query_embedding, limit * 2)
            
            # Filter by threshold and limit
            filtered_results = [
                result for result in results 
                if result.get('score', 0) >= threshold
            ][:limit]
            
            return {
                'query': query,
                'results': filtered_results,
                'total_found': len(results),
                'filtered_count': len(filtered_results),
                'threshold': threshold
            }
            
        except Exception as e:
            raise RuntimeError(f"Semantic search failed: {str(e)}")
    
    async def health_check(self, ctx) -> Dict:
        """Comprehensive health check of all dependencies"""
        health_status = {
            'server': self._health_status,
            'timestamp': time.time(),
            'dependencies': {}
        }
        
        # Check vector database
        try:
            await self.context.vector_db.search_similar([0.1] * 1536, 1)
            health_status['dependencies']['vector_db'] = 'healthy'
        except Exception as e:
            health_status['dependencies']['vector_db'] = f'unhealthy: {str(e)}'
        
        # Check AI service
        try:
            await self.context.ai_service.generate_embeddings(['health check'])
            health_status['dependencies']['ai_service'] = 'healthy'
        except Exception as e:
            health_status['dependencies']['ai_service'] = f'unhealthy: {str(e)}'
        
        # Check search engine
        try:
            await self.context.search_engine.search('test', 1)
            health_status['dependencies']['search_engine'] = 'healthy'
        except Exception as e:
            health_status['dependencies']['search_engine'] = f'unhealthy: {str(e)}'
        
        # Check cache
        try:
            await self.context.cache.set('health_check', 'ok', 60)
            await self.context.cache.get('health_check')
            health_status['dependencies']['cache'] = 'healthy'
        except Exception as e:
            health_status['dependencies']['cache'] = f'unhealthy: {str(e)}'
        
        # Overall health
        unhealthy_deps = [
            dep for dep, status in health_status['dependencies'].items()
            if not status.startswith('healthy')
        ]
        health_status['overall'] = 'healthy' if not unhealthy_deps else 'degraded'
        
        return health_status
```

### Task 3.2: Create comprehensive test setup

Create `exercises/test_exercise_3.py`:

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from complex_mcp_server import (
    ComplexMCPServer, ComplexServerContext,
    VectorDatabase, AIEmbeddingService, SearchEngine, CacheService
)

class TestComplexMCPServer:
    """Test complex MCP server with multiple dependencies"""
    
    def setup_method(self):
        """Set up comprehensive test fixtures"""
        # TODO: Create mock dependencies
        # TODO: Create server context with mocks
        # TODO: Create server instance
        # TODO: Create test context
        pass
    
    @pytest.mark.asyncio
    async def test_server_startup_shutdown_lifecycle(self):
        """Test server lifecycle management"""
        # TODO:
        # 1. Test server startup sequence
        # 2. Verify context initialization is called
        # 3. Test server shutdown sequence
        # 4. Verify cleanup is called
        # 5. Check health status changes appropriately
        pass
```

**Your Tasks:**

1. Implement the setup_method with proper mock creation
2. Create mock instances for all four service dependencies
3. Configure realistic mock behaviors
4. Implement the lifecycle test

## Part 2: Advanced Mocking Patterns (20 minutes)

### Task 3.3: Mock complex service interactions

Add these test methods:

```python
@pytest.mark.asyncio
async def test_smart_search_with_cache_hit(self):
    """Test smart search when result is cached"""
    query = "python testing best practices"
    cached_results = [
        {"title": "Cached Result", "url": "https://cached.com"},
    ]
    
    # TODO:
    # 1. Configure cache mock to return cached_results for the query
    # 2. Call smart_search
    # 3. Verify cache.get was called with correct cache key
    # 4. Verify search_engine and ai_service were NOT called
    # 5. Verify result indicates cache source
    pass

@pytest.mark.asyncio
async def test_smart_search_with_ai_enhancement(self):
    """Test smart search with AI reranking"""
    query = "machine learning algorithms"
    search_results = [
        {"title": "ML Result 1", "url": "https://ml1.com"},
        {"title": "ML Result 2", "url": "https://ml2.com"},
    ]
    query_embedding = [0.1] * 1536  # OpenAI embedding size
    reranked_results = search_results[::-1]  # Reversed order
    
    # TODO:
    # 1. Configure cache to return None (cache miss)
    # 2. Configure search_engine to return search_results
    # 3. Configure ai_service.generate_embeddings to return [query_embedding]
    # 4. Configure ai_service.rerank_results to return reranked_results
    # 5. Call smart_search with use_ai=True
    # 6. Verify all services were called in correct order
    # 7. Verify result is cached
    # 8. Verify ai_enhanced=True in response
    pass

@pytest.mark.asyncio
async def test_smart_search_without_ai(self):
    """Test smart search without AI enhancement"""
    # TODO:
    # 1. Configure mocks for non-AI search
    # 2. Call smart_search with use_ai=False
    # 3. Verify AI service methods are NOT called
    # 4. Verify search results are returned without reranking
    pass

@pytest.mark.asyncio
async def test_smart_search_error_handling(self):
    """Test error handling in smart search"""
    # TODO:
    # 1. Configure search_engine to raise an exception
    # 2. Call smart_search
    # 3. Verify error response structure
    # 4. Verify error is handled gracefully (no re-raising)
    pass
```

### Task 3.4: Test stateful mock interactions

```python
@pytest.mark.asyncio
async def test_store_and_index_success_path(self):
    """Test successful document storage and indexing"""
    documents = [
        {
            "url": "https://example.com/doc1",
            "content": "This is the first document content",
            "title": "Document 1"
        },
        {
            "url": "https://example.com/doc2", 
            "content": "This is the second document content",
            "title": "Document 2"
        }
    ]
    
    # Mock responses
    embeddings = [[0.1] * 1536, [0.2] * 1536]  # Two embeddings
    doc_ids = ["doc_1", "doc_2"]
    
    # TODO:
    # 1. Configure ai_service.generate_embeddings to return embeddings
    # 2. Configure vector_db.store_embeddings to return doc_ids
    # 3. Call store_and_index with documents
    # 4. Verify ai_service was called with correct content texts
    # 5. Verify vector_db was called with enhanced documents (including embeddings)
    # 6. Verify response shows correct counts and IDs
    pass

@pytest.mark.asyncio
async def test_store_and_index_partial_failures(self):
    """Test document storage with some invalid documents"""
    documents = [
        {"url": "https://good.com", "content": "Good content"},  # Valid
        {"url": "https://bad.com"},  # Missing content - invalid
        {"content": "No URL content"},  # Missing URL - invalid  
        {"url": "https://good2.com", "content": "More good content"},  # Valid
    ]
    
    # TODO:
    # 1. Configure mocks for successful processing of valid docs only
    # 2. Call store_and_index
    # 3. Verify only valid documents were processed
    # 4. Verify failed_count and errors are reported correctly
    # 5. Verify stored_count matches valid document count
    pass

@pytest.mark.asyncio
async def test_store_and_index_ai_service_failure(self):
    """Test handling of AI service failures"""
    documents = [{"url": "https://test.com", "content": "Test content"}]
    
    # TODO:
    # 1. Configure ai_service.generate_embeddings to raise exception
    # 2. Call store_and_index  
    # 3. Verify error response structure
    # 4. Verify no documents were stored due to embedding failure
    pass
```

## Part 3: Complex Dependency Chains (15 minutes)

### Task 3.5: Test semantic search with dependency chain

```python
@pytest.mark.asyncio
async def test_semantic_search_success(self):
    """Test successful semantic search"""
    query = "artificial intelligence"
    query_embedding = [0.5] * 1536
    search_results = [
        {"id": "doc1", "score": 0.95, "content": "AI content 1"},
        {"id": "doc2", "score": 0.85, "content": "AI content 2"},
        {"id": "doc3", "score": 0.65, "content": "AI content 3"},  # Below threshold
    ]
    
    # TODO:
    # 1. Configure ai_service to return query_embedding
    # 2. Configure vector_db to return search_results  
    # 3. Call semantic_search with threshold=0.7
    # 4. Verify only results above threshold are returned
    # 5. Verify response structure includes all expected fields
    pass

@pytest.mark.asyncio
async def test_semantic_search_parameter_validation(self):
    """Test parameter validation in semantic search"""
    # TODO: Test with various invalid parameters:
    # - Empty query (should raise ValueError)
    # - Invalid limit values (0, -1, 101)
    # - Each should raise ValueError with appropriate message
    pass

@pytest.mark.asyncio
async def test_semantic_search_embedding_failure(self):
    """Test handling of embedding generation failure"""
    # TODO:
    # 1. Configure ai_service.generate_embeddings to raise exception
    # 2. Call semantic_search
    # 3. Verify RuntimeError is raised with appropriate message
    pass

@pytest.mark.asyncio
async def test_semantic_search_database_failure(self):
    """Test handling of vector database failure"""
    # TODO:
    # 1. Configure vector_db.search_similar to raise exception
    # 2. Call semantic_search
    # 3. Verify RuntimeError is raised with appropriate message
    pass
```

## Part 4: Service Health and Monitoring (10 minutes)

### Task 3.6: Test comprehensive health checking

```python
@pytest.mark.asyncio
async def test_health_check_all_services_healthy(self):
    """Test health check when all services are healthy"""
    # TODO:
    # 1. Configure all service mocks to succeed
    # 2. Call health_check
    # 3. Verify all dependencies show 'healthy' status
    # 4. Verify overall status is 'healthy'
    # 5. Verify timestamp is included
    pass

@pytest.mark.asyncio
async def test_health_check_some_services_unhealthy(self):
    """Test health check with some service failures"""
    # TODO:
    # 1. Configure vector_db and search_engine to raise exceptions
    # 2. Configure ai_service and cache to succeed
    # 3. Call health_check
    # 4. Verify failed services show 'unhealthy' with error messages
    # 5. Verify healthy services show 'healthy'
    # 6. Verify overall status is 'degraded'
    pass

@pytest.mark.asyncio
async def test_health_check_exception_handling(self):
    """Test that health check handles individual service exceptions"""
    # TODO:
    # 1. Configure each service to raise different types of exceptions
    # 2. Call health_check
    # 3. Verify health check completes without raising exceptions
    # 4. Verify all exception messages are captured in response
    pass
```

## Part 5: Advanced Mock Verification (15 minutes)

### Task 3.7: Test complex mock call patterns

```python
@pytest.mark.asyncio
async def test_mock_call_verification_detailed(self):
    """Test detailed verification of mock calls"""
    query = "test query"
    documents = [{"url": "https://test.com", "content": "content"}]
    
    # TODO:
    # 1. Perform a complete workflow:
    #    - Store documents
    #    - Perform semantic search
    #    - Perform smart search
    # 2. Verify exact call patterns:
    #    - ai_service.generate_embeddings called correct number of times
    #    - vector_db methods called in correct order
    #    - cache operations called appropriately
    # 3. Verify call arguments match expectations
    pass

@pytest.mark.asyncio
async def test_mock_side_effects_and_return_values(self):
    """Test complex mock side effects and return value patterns"""
    
    # Create a stateful mock that changes behavior over time
    call_count = 0
    
    async def stateful_embedding_generation(texts):
        nonlocal call_count
        call_count += 1
        
        if call_count == 1:
            # First call returns normal embeddings
            return [[0.1] * 1536 for _ in texts]
        elif call_count == 2:
            # Second call has slower response (simulate load)
            await asyncio.sleep(0.2)
            return [[0.2] * 1536 for _ in texts]
        else:
            # Third call fails
            raise Exception("Service overloaded")
    
    self.mock_ai_service.generate_embeddings.side_effect = stateful_embedding_generation
    
    # TODO:
    # 1. Make three different calls that trigger embedding generation
    # 2. Verify first call succeeds with expected results
    # 3. Verify second call succeeds but takes longer
    # 4. Verify third call fails appropriately
    pass

@pytest.mark.asyncio
async def test_mock_context_managers_and_async_resources(self):
    """Test mocking of context managers and async resource handling"""
    
    # Mock an async context manager for database transactions
    mock_transaction = AsyncMock()
    mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
    mock_transaction.__aexit__ = AsyncMock(return_value=None)
    
    # TODO:
    # 1. Add a method to ComplexMCPServer that uses async context manager
    # 2. Configure mock to simulate transaction behavior
    # 3. Test that context manager is properly entered and exited
    # 4. Test both success and failure scenarios
    pass
```

### Task 3.8: Test concurrent mock interactions

```python
@pytest.mark.asyncio
async def test_concurrent_service_calls(self):
    """Test handling of concurrent service calls"""
    
    # Configure services with different response times
    async def slow_search(query, num_results):
        await asyncio.sleep(0.3)
        return [{"title": f"Result for {query}", "url": "https://slow.com"}]
    
    async def fast_embedding(texts):
        await asyncio.sleep(0.1)
        return [[0.1] * 1536 for _ in texts]
    
    self.mock_search_engine.search.side_effect = slow_search
    self.mock_ai_service.generate_embeddings.side_effect = fast_embedding
    
    # TODO:
    # 1. Start multiple concurrent operations
    # 2. Verify they complete in expected order
    # 3. Verify total time is appropriate for concurrent execution
    # 4. Verify all mocks were called correct number of times
    pass

@pytest.mark.asyncio
async def test_request_counting_and_state_tracking(self):
    """Test server state tracking across multiple requests"""
    # TODO:
    # 1. Make multiple requests to different endpoints
    # 2. Verify request counter increments correctly
    # 3. Verify server state is maintained across requests
    # 4. Test that server state doesn't interfere between test methods
    pass
```

## Part 6: Integration Patterns (10 minutes)

### Task 3.9: Test realistic integration scenarios

```python
@pytest.mark.asyncio
async def test_end_to_end_document_workflow(self):
    """Test complete document processing workflow"""
    # TODO:
    # 1. Store documents with store_and_index
    # 2. Perform semantic search to find them
    # 3. Perform smart search with same query
    # 4. Verify results are consistent and cached appropriately
    # 5. Verify all services were called in logical sequence
    pass

@pytest.mark.asyncio
async def test_error_recovery_and_fallback_patterns(self):
    """Test error recovery across multiple service calls"""
    # TODO:
    # 1. Configure some services to fail intermittently
    # 2. Make requests that should trigger fallback behavior
    # 3. Verify system continues to function with degraded performance
    # 4. Verify errors are logged/tracked appropriately
    pass

@pytest.mark.asyncio
async def test_performance_with_realistic_load(self):
    """Test system behavior under realistic load patterns"""
    # TODO:
    # 1. Configure services with realistic response times
    # 2. Make multiple concurrent requests
    # 3. Verify system handles load appropriately  
    # 4. Verify resource usage patterns (request counting, etc.)
    pass
```

## Testing and Verification

### Running Your Tests

```bash
# Run all Exercise 3 tests
uv run pytest exercises/test_exercise_3.py -v

# Run with detailed output
uv run pytest exercises/test_exercise_3.py -v -s

# Run specific test categories
uv run pytest exercises/test_exercise_3.py -v -k "health"
uv run pytest exercises/test_exercise_3.py -v -k "mock"
uv run pytest exercises/test_exercise_3.py -v -k "search"

# Run with coverage
uv run pytest exercises/test_exercise_3.py --cov=exercises --cov-report=html

# Debug specific test
uv run pytest exercises/test_exercise_3.py::TestComplexMCPServer::test_smart_search_with_ai_enhancement -v -s
```

### Mock Verification Patterns

Your tests should demonstrate these verification patterns:

```python
# Verify call counts
mock_service.method.assert_called_once()
assert mock_service.method.call_count == 3

# Verify call arguments
mock_service.method.assert_called_with(expected_arg1, expected_arg2)

# Verify call order
expected_calls = [
    call('first_arg'),
    call('second_arg'),
]
mock_service.method.assert_has_calls(expected_calls)

# Verify no unexpected calls
mock_service.unexpected_method.assert_not_called()

# Complex argument verification
args, kwargs = mock_service.method.call_args
assert args[0] == expected_value
assert 'key' in kwargs
```

## Assessment Criteria

Your implementation will be evaluated on:

1. **Mock Design Quality**: Realistic, maintainable mock configurations
2. **Dependency Injection**: Proper separation of concerns and testability
3. **Error Scenario Coverage**: Comprehensive testing of failure modes
4. **Mock Verification**: Proper verification of service interactions
5. **Test Organization**: Clean, readable test structure and naming
6. **Async Patterns**: Correct handling of async operations and timing

## Common Challenges and Solutions

### Challenge: Complex Mock Setup

```python
# Problem: Lots of repetitive mock configuration
# Solution: Use fixtures and helper methods

@pytest.fixture
def configured_mocks(self):
    """Pre-configured mocks for common scenarios"""
    mocks = {
        'ai_service': AsyncMock(),
        'vector_db': AsyncMock(),
        'search_engine': AsyncMock(),
        'cache': AsyncMock()
    }
    
    # Configure common responses
    mocks['ai_service'].generate_embeddings.return_value = [[0.1] * 1536]
    mocks['cache'].get.return_value = None  # Cache miss by default
    
    return mocks
```

### Challenge: Async Mock Timing

```python
# Problem: Tests are flaky due to timing
# Solution: Use deterministic delays and proper async patterns

# Instead of real delays
await asyncio.sleep(0.1)

# Use mock delays that are predictable
self.mock_service.method.side_effect = lambda: asyncio.sleep(0.001)
```

### Challenge: Stateful Mock Behavior

```python
# Problem: Mocks need to change behavior based on state
# Solution: Use classes or closures for stateful mocks

class StatefulVectorDB:
    def __init__(self):
        self.stored_docs = []
    
    async def store_embeddings(self, docs):
        self.stored_docs.extend(docs)
        return [f"id_{i}" for i in range(len(docs))]
    
    async def search_similar(self, embedding, limit):
        # Return stored docs that match some criteria
        return self.stored_docs[:limit]

# Use in test
self.mock_vector_db = StatefulVectorDB()
```

## Next Steps

After completing this exercise:

1. Review the solution for alternative mocking approaches
2. Experiment with different mock patterns
3. Try adding new services and testing their interactions
4. Move on to Exercise 4 for integration testing with real services

## Reflection Questions

1. What are the trade-offs between realistic mocks and simple mocks?
2. How do you balance mock complexity with test maintainability?
3. When should you use stateful mocks vs stateless mocks?
4. How do you verify that your mocks accurately represent real service behavior?
5. What patterns help prevent mock configuration from becoming unmanageable?
