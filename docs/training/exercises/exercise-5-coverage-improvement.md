# Exercise 5: Coverage Analysis and Improvement

**Duration**: 60 minutes  
**Difficulty**: Intermediate-Advanced  
**Prerequisites**: Completion of Exercises 1-4, understanding of test coverage metrics

## Learning Objectives

After completing this exercise, you will be able to:

- Analyze coverage reports to identify gaps systematically
- Design tests that improve coverage meaningfully (not just numbers)
- Balance coverage goals with test quality and maintainability
- Use coverage data to guide refactoring decisions
- Set up automated coverage monitoring and enforcement
- Implement coverage-driven development practices

## Exercise Overview

You'll work with a realistic codebase that has moderate coverage (~60%) and systematically improve it to reach 80%+ while maintaining test quality. This mirrors the actual Crawl4AI project status.

## Part 1: Coverage Analysis and Gap Identification (20 minutes)

### Task 5.1: Create a realistic module to analyze

Create `exercises/document_processor.py`:

```python
import asyncio
import hashlib
import json
import re
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProcessingConfig:
    """Configuration for document processing"""
    max_content_length: int = 50000
    enable_deduplication: bool = True
    content_types: List[str] = field(default_factory=lambda: ['text/html', 'text/plain'])
    processing_timeout: int = 30
    chunk_size: int = 1000
    overlap_size: int = 200

class DocumentProcessingError(Exception):
    """Custom exception for document processing errors"""
    def __init__(self, message: str, error_code: str = "PROCESSING_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)

class DocumentProcessor:
    """Process and prepare documents for storage and indexing"""
    
    def __init__(self, config: ProcessingConfig = None):
        self.config = config or ProcessingConfig()
        self.processed_count = 0
        self.error_count = 0
        self.cache = {}
        
    def validate_document(self, document: Dict[str, Any]) -> bool:
        """Validate document structure and content"""
        required_fields = ['url', 'content']
        
        # Check required fields
        if not all(field in document for field in required_fields):
            raise DocumentProcessingError("Missing required fields", "INVALID_STRUCTURE")
        
        # Validate URL format
        try:
            parsed_url = urlparse(document['url'])
            if not parsed_url.scheme or not parsed_url.netloc:
                raise DocumentProcessingError("Invalid URL format", "INVALID_URL")
        except Exception as e:
            raise DocumentProcessingError(f"URL parsing failed: {str(e)}", "URL_PARSE_ERROR")
        
        # Check content length
        content = document.get('content', '')
        if len(content) > self.config.max_content_length:
            raise DocumentProcessingError("Content too long", "CONTENT_TOO_LONG")
        
        if len(content.strip()) == 0:
            raise DocumentProcessingError("Empty content", "EMPTY_CONTENT")
        
        return True
    
    def extract_metadata(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from document"""
        metadata = {}
        
        # Extract from URL
        parsed_url = urlparse(document['url'])
        metadata['domain'] = parsed_url.netloc
        metadata['path'] = parsed_url.path
        metadata['scheme'] = parsed_url.scheme
        
        # Extract content statistics
        content = document.get('content', '')
        metadata['content_length'] = len(content)
        metadata['word_count'] = len(content.split())
        
        # Extract title if available
        if 'title' in document:
            metadata['title'] = document['title']
            metadata['title_length'] = len(document['title'])
        
        # Language detection (simplified)
        if self._detect_language(content) == 'en':
            metadata['language'] = 'english'
        else:
            metadata['language'] = 'other'
        
        # Content type analysis
        if self._is_code_content(content):
            metadata['content_type'] = 'code'
        elif self._is_documentation(content):
            metadata['content_type'] = 'documentation'
        else:
            metadata['content_type'] = 'general'
        
        metadata['processing_timestamp'] = time.time()
        
        return metadata
    
    def _detect_language(self, content: str) -> str:
        """Simple language detection"""
        # This is a simplified implementation
        english_words = ['the', 'and', 'a', 'to', 'of', 'in', 'is', 'you', 'that', 'it']
        words = content.lower().split()
        
        if len(words) < 10:
            return 'unknown'
        
        english_count = sum(1 for word in words[:100] if word in english_words)
        return 'en' if english_count > 5 else 'other'
    
    def _is_code_content(self, content: str) -> bool:
        """Detect if content contains code"""
        code_indicators = [
            'def ', 'class ', 'import ', 'function ', 'var ', 'const ',
            '{', '}', ';', '//', '/*', '*/', '===', '!=='
        ]
        
        content_lower = content.lower()
        code_count = sum(1 for indicator in code_indicators if indicator in content_lower)
        
        return code_count > 3
    
    def _is_documentation(self, content: str) -> bool:
        """Detect if content is documentation"""
        doc_indicators = ['api reference', 'documentation', 'tutorial', 'guide', 'how to']
        title_indicators = ['#', '##', '###']  # Markdown headers
        
        content_lower = content.lower()
        
        # Check for documentation keywords
        doc_score = sum(1 for indicator in doc_indicators if indicator in content_lower)
        
        # Check for markdown headers
        header_score = sum(1 for line in content.split('\n')[:20] 
                          if any(line.strip().startswith(h) for h in title_indicators))
        
        return doc_score > 0 or header_score > 2
    
    def generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        # Normalize content for hashing
        normalized = re.sub(r'\s+', ' ', content.strip().lower())
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def check_duplicate(self, content_hash: str) -> bool:
        """Check if content is duplicate"""
        if not self.config.enable_deduplication:
            return False
        
        return content_hash in self.cache
    
    def chunk_content(self, content: str) -> List[Dict[str, Any]]:
        """Split content into chunks for processing"""
        if len(content) <= self.config.chunk_size:
            return [{'text': content, 'chunk_id': 0, 'start_pos': 0, 'end_pos': len(content)}]
        
        chunks = []
        chunk_id = 0
        start = 0
        
        while start < len(content):
            end = min(start + self.config.chunk_size, len(content))
            
            # Try to find a good break point (end of sentence or paragraph)
            if end < len(content):
                # Look for sentence end
                for i in range(end, max(start + self.config.chunk_size - 100, start), -1):
                    if content[i] in '.!?\n':
                        end = i + 1
                        break
            
            chunk_text = content[start:end]
            
            chunks.append({
                'text': chunk_text,
                'chunk_id': chunk_id,
                'start_pos': start,
                'end_pos': end,
                'length': len(chunk_text)
            })
            
            # Calculate next start with overlap
            start = max(start + 1, end - self.config.overlap_size)
            chunk_id += 1
        
        return chunks
    
    async def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document"""
        try:
            # Validate document
            self.validate_document(document)
            
            # Extract content
            content = document['content']
            
            # Generate content hash
            content_hash = self.generate_content_hash(content)
            
            # Check for duplicates
            if self.check_duplicate(content_hash):
                logger.info(f"Duplicate content detected for {document['url']}")
                return {
                    'status': 'duplicate',
                    'url': document['url'],
                    'content_hash': content_hash
                }
            
            # Extract metadata
            metadata = self.extract_metadata(document)
            
            # Chunk content
            chunks = self.chunk_content(content)
            
            # Simulate processing time
            await asyncio.sleep(0.01)
            
            # Store in cache for deduplication
            if self.config.enable_deduplication:
                self.cache[content_hash] = time.time()
            
            # Update counters
            self.processed_count += 1
            
            result = {
                'status': 'success',
                'url': document['url'],
                'content_hash': content_hash,
                'metadata': metadata,
                'chunks': chunks,
                'chunk_count': len(chunks),
                'processing_timestamp': time.time()
            }
            
            return result
            
        except DocumentProcessingError:
            self.error_count += 1
            raise
        except Exception as e:
            self.error_count += 1
            raise DocumentProcessingError(f"Unexpected error: {str(e)}", "UNEXPECTED_ERROR")
    
    async def process_batch(self, documents: List[Dict[str, Any]], 
                          max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """Process multiple documents concurrently"""
        if not documents:
            return []
        
        # Validate max_concurrent parameter
        if max_concurrent < 1:
            max_concurrent = 1
        elif max_concurrent > 20:
            max_concurrent = 20
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(doc):
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        self.process_document(doc), 
                        timeout=self.config.processing_timeout
                    )
                except asyncio.TimeoutError:
                    self.error_count += 1
                    return {
                        'status': 'timeout',
                        'url': doc.get('url', 'unknown'),
                        'error': 'Processing timeout'
                    }
                except DocumentProcessingError as e:
                    return {
                        'status': 'error',
                        'url': doc.get('url', 'unknown'),
                        'error': e.message,
                        'error_code': e.error_code
                    }
                except Exception as e:
                    self.error_count += 1
                    return {
                        'status': 'error',
                        'url': doc.get('url', 'unknown'),
                        'error': str(e),
                        'error_code': 'UNEXPECTED_ERROR'
                    }
        
        # Process all documents
        tasks = [process_with_semaphore(doc) for doc in documents]
        results = await asyncio.gather(*tasks)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        total_processed = self.processed_count + self.error_count
        
        stats = {
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'total_count': total_processed,
            'success_rate': self.processed_count / total_processed if total_processed > 0 else 0,
            'cache_size': len(self.cache),
            'config': {
                'max_content_length': self.config.max_content_length,
                'enable_deduplication': self.config.enable_deduplication,
                'chunk_size': self.config.chunk_size,
                'overlap_size': self.config.overlap_size
            }
        }
        
        return stats
    
    def reset_statistics(self):
        """Reset processing statistics"""
        self.processed_count = 0
        self.error_count = 0
    
    def clear_cache(self):
        """Clear the deduplication cache"""
        self.cache.clear()
    
    def export_cache(self) -> Dict[str, float]:
        """Export cache for persistence"""
        return self.cache.copy()
    
    def import_cache(self, cache_data: Dict[str, float]):
        """Import cache from persistence"""
        if isinstance(cache_data, dict):
            self.cache = cache_data.copy()
        else:
            raise ValueError("Cache data must be a dictionary")
```

### Task 5.2: Analyze initial coverage

Create `exercises/test_coverage_baseline.py`:

```python
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from document_processor import DocumentProcessor, ProcessingConfig, DocumentProcessingError

class TestDocumentProcessorBaseline:
    """Baseline tests - represents current coverage level"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = ProcessingConfig()
        self.processor = DocumentProcessor(self.config)
    
    def test_processor_initialization(self):
        """Test processor initialization"""
        assert self.processor.config == self.config
        assert self.processor.processed_count == 0
        assert self.processor.error_count == 0
    
    def test_validate_document_success(self):
        """Test document validation with valid document"""
        document = {
            'url': 'https://example.com/test',
            'content': 'This is test content'
        }
        
        result = self.processor.validate_document(document)
        assert result is True
    
    def test_validate_document_missing_fields(self):
        """Test validation with missing required fields"""
        document = {'url': 'https://example.com/test'}  # Missing content
        
        with pytest.raises(DocumentProcessingError) as exc_info:
            self.processor.validate_document(document)
        
        assert exc_info.value.error_code == "INVALID_STRUCTURE"
    
    @pytest.mark.asyncio
    async def test_process_document_success(self):
        """Test successful document processing"""
        document = {
            'url': 'https://example.com/test',
            'content': 'This is test content for processing',
            'title': 'Test Document'
        }
        
        result = await self.processor.process_document(document)
        
        assert result['status'] == 'success'
        assert result['url'] == document['url']
        assert 'content_hash' in result
        assert 'metadata' in result
        assert 'chunks' in result
    
    @pytest.mark.asyncio
    async def test_process_batch_success(self):
        """Test batch processing"""
        documents = [
            {'url': 'https://example.com/1', 'content': 'Content 1'},
            {'url': 'https://example.com/2', 'content': 'Content 2'}
        ]
        
        results = await self.processor.process_batch(documents)
        
        assert len(results) == 2
        assert all(result['status'] == 'success' for result in results)
```

**Your Task**: Run coverage analysis on the baseline tests:

```bash
# Run baseline tests with coverage
uv run pytest exercises/test_coverage_baseline.py --cov=exercises/document_processor --cov-report=html --cov-report=term-missing

# View the coverage report
open htmlcov/index.html
```

### Task 5.3: Systematic coverage gap analysis

Create `exercises/coverage_analyzer.py`:

```python
import ast
import inspect
from typing import Dict, List, Set, Any
from document_processor import DocumentProcessor

class CoverageAnalyzer:
    """Analyze code coverage gaps and suggest improvements"""
    
    def __init__(self, target_class):
        self.target_class = target_class
        self.source = inspect.getsource(target_class)
        self.tree = ast.parse(self.source)
    
    def analyze_methods(self) -> Dict[str, Dict[str, Any]]:
        """Analyze all methods in the target class"""
        methods = {}
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef):
                method_info = {
                    'name': node.name,
                    'line_count': node.end_lineno - node.lineno + 1,
                    'complexity': self._calculate_complexity(node),
                    'has_error_handling': self._has_error_handling(node),
                    'has_branches': self._has_branches(node),
                    'parameters': len(node.args.args),
                    'docstring': ast.get_docstring(node) is not None
                }
                methods[node.name] = method_info
        
        return methods
    
    def _calculate_complexity(self, node) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _has_error_handling(self, node) -> bool:
        """Check if method has error handling"""
        for child in ast.walk(node):
            if isinstance(child, (ast.Try, ast.Raise, ast.ExceptHandler)):
                return True
        return False
    
    def _has_branches(self, node) -> bool:
        """Check if method has conditional branches"""
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                return True
        return False
    
    def identify_coverage_gaps(self, covered_lines: Set[int]) -> List[Dict[str, Any]]:
        """Identify specific coverage gaps"""
        gaps = []
        
        # TODO: Implement gap identification logic
        # 1. Find uncovered lines
        # 2. Categorize gaps (error handling, branches, edge cases)
        # 3. Prioritize gaps by importance
        # 4. Suggest test scenarios
        
        return gaps
    
    def suggest_test_scenarios(self, method_name: str) -> List[str]:
        """Suggest test scenarios for a specific method"""
        scenarios = []
        methods = self.analyze_methods()
        
        if method_name not in methods:
            return scenarios
        
        method_info = methods[method_name]
        
        # TODO: Implement test scenario suggestions
        # 1. Success path tests
        # 2. Error condition tests  
        # 3. Edge case tests
        # 4. Branch coverage tests
        
        return scenarios

# Usage example
analyzer = CoverageAnalyzer(DocumentProcessor)
methods = analyzer.analyze_methods()

print("Method Analysis:")
for name, info in methods.items():
    print(f"  {name}: complexity={info['complexity']}, lines={info['line_count']}")
```

**Your Task**: Complete the CoverageAnalyzer implementation and analyze the coverage gaps.

## Part 2: Strategic Test Design for Coverage (20 minutes)

### Task 5.4: Design tests for uncovered branches

Create `exercises/test_coverage_improvement.py`:

```python
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from document_processor import DocumentProcessor, ProcessingConfig, DocumentProcessingError

class TestDocumentProcessorCoverageImprovement:
    """Tests designed specifically to improve coverage"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.processor = DocumentProcessor()
    
    # Branch Coverage Tests
    def test_validate_document_invalid_url_scheme(self):
        """Test URL validation with invalid scheme"""
        # TODO: Test documents with various invalid URL formats
        # - No scheme: "example.com/path"
        # - Invalid scheme: "ftp://example.com"
        # - Malformed URL: "http://"
        pass
    
    def test_validate_document_content_too_long(self):
        """Test validation with content exceeding max length"""
        # TODO: Test with content longer than max_content_length
        # Verify DocumentProcessingError with correct error code
        pass
    
    def test_validate_document_empty_content(self):
        """Test validation with empty or whitespace-only content"""
        # TODO: Test with:
        # - Empty string content
        # - Whitespace-only content
        # - None content
        pass
    
    # Metadata Extraction Coverage
    def test_extract_metadata_language_detection(self):
        """Test language detection branch coverage"""
        # TODO: Test with:
        # - English content (should detect 'en')
        # - Non-English content (should detect 'other')
        # - Short content (should detect 'unknown')
        pass
    
    def test_extract_metadata_content_type_detection(self):
        """Test content type detection branches"""
        # TODO: Create test content for each type:
        # - Code content (with function definitions, brackets, etc.)
        # - Documentation content (with API reference, tutorials)
        # - General content (regular text)
        pass
    
    def test_extract_metadata_without_title(self):
        """Test metadata extraction when title is missing"""
        # TODO: Test document without 'title' field
        # Verify metadata doesn't include title-related fields
        pass
    
    # Chunking Algorithm Coverage
    def test_chunk_content_small_content(self):
        """Test chunking with content smaller than chunk size"""
        # TODO: Test with content length < chunk_size
        # Should return single chunk
        pass
    
    def test_chunk_content_exact_chunk_size(self):
        """Test chunking with content exactly chunk size"""
        # TODO: Test edge case where content is exactly chunk_size
        pass
    
    def test_chunk_content_with_good_break_points(self):
        """Test chunking algorithm finding sentence boundaries"""
        # TODO: Create content with clear sentence breaks
        # Verify chunks break at sentence boundaries when possible
        pass
    
    def test_chunk_content_no_good_break_points(self):
        """Test chunking when no good break points exist"""
        # TODO: Create content without sentence breaks
        # Verify fallback chunking behavior
        pass
    
    # Error Handling Coverage
    @pytest.mark.asyncio
    async def test_process_document_url_parsing_error(self):
        """Test handling of URL parsing errors"""
        # TODO: Create document with URL that causes parsing exception
        # Use mock to simulate urlparse raising exception
        pass
    
    @pytest.mark.asyncio
    async def test_process_document_unexpected_error(self):
        """Test handling of unexpected errors during processing"""
        # TODO: Mock a method to raise unexpected exception
        # Verify it's wrapped in DocumentProcessingError with UNEXPECTED_ERROR code
        pass
    
    # Deduplication Coverage
    def test_check_duplicate_with_deduplication_disabled(self):
        """Test duplicate checking when deduplication is disabled"""
        # TODO: Create processor with enable_deduplication=False
        # Verify check_duplicate always returns False
        pass
    
    def test_check_duplicate_with_existing_hash(self):
        """Test duplicate detection with existing content hash"""
        # TODO: Add hash to cache, then check for duplicate
        # Should return True
        pass
    
    def test_generate_content_hash_normalization(self):
        """Test content hash generation with normalization"""
        # TODO: Test that different whitespace/case produces same hash
        # "Hello  World" and "hello world" should have same hash
        pass
    
    # Batch Processing Coverage
    @pytest.mark.asyncio
    async def test_process_batch_empty_list(self):
        """Test batch processing with empty document list"""
        # TODO: Pass empty list to process_batch
        # Should return empty list without error
        pass
    
    @pytest.mark.asyncio
    async def test_process_batch_concurrency_limits(self):
        """Test batch processing concurrency parameter validation"""
        # TODO: Test with:
        # - max_concurrent < 1 (should default to 1)
        # - max_concurrent > 20 (should cap at 20)
        pass
    
    @pytest.mark.asyncio
    async def test_process_batch_timeout_handling(self):
        """Test timeout handling in batch processing"""
        # TODO: Mock process_document to take longer than timeout
        # Verify timeout results are returned correctly
        pass
    
    @pytest.mark.asyncio
    async def test_process_batch_mixed_results(self):
        """Test batch processing with mix of success/error/timeout results"""
        # TODO: Create batch with documents that will:
        # - Succeed normally
        # - Raise DocumentProcessingError
        # - Raise unexpected exception
        # - Timeout
        pass
    
    # Statistics and Cache Management Coverage
    def test_get_statistics_with_no_processing(self):
        """Test statistics when no documents have been processed"""
        # TODO: Call get_statistics on fresh processor
        # Verify all counts are 0, success_rate handles division by zero
        pass
    
    def test_get_statistics_after_processing(self):
        """Test statistics after processing some documents"""
        # TODO: Process some documents (success and failures)
        # Verify statistics are calculated correctly
        pass
    
    def test_reset_statistics(self):
        """Test statistics reset functionality"""
        # TODO: Process documents, verify non-zero stats, reset, verify zero stats
        pass
    
    def test_cache_import_export(self):
        """Test cache import/export functionality"""
        # TODO: Export cache, modify processor cache, import, verify restoration
        pass
    
    def test_import_cache_invalid_data(self):
        """Test cache import with invalid data"""
        # TODO: Try importing non-dict data
        # Should raise ValueError
        pass
    
    # Configuration Coverage
    def test_processor_with_custom_config(self):
        """Test processor initialization with custom configuration"""
        # TODO: Create custom config and verify it's used correctly
        pass
    
    def test_processor_with_no_config(self):
        """Test processor initialization with default configuration"""
        # TODO: Create processor without config parameter
        # Verify default config is created
        pass
```

**Your Tasks**:

1. Complete all the TODO test methods
2. Focus on branch coverage and error conditions
3. Use parametrized tests where appropriate
4. Ensure tests are meaningful, not just coverage-driven

### Task 5.5: Error condition and edge case testing

Add these comprehensive error tests:

```python
class TestErrorConditionsAndEdgeCases:
    """Comprehensive error condition and edge case testing"""
    
    def setup_method(self):
        self.processor = DocumentProcessor()
    
    @pytest.mark.parametrize("invalid_document", [
        {},  # Empty document
        {'url': 'https://example.com'},  # Missing content
        {'content': 'test content'},  # Missing URL
        {'url': '', 'content': 'test'},  # Empty URL
        {'url': 'https://example.com', 'content': ''},  # Empty content
        {'url': 'https://example.com', 'content': '   '},  # Whitespace content
        None,  # None document
    ])
    def test_validate_document_comprehensive_invalid_inputs(self, invalid_document):
        """Test validation with comprehensive invalid inputs"""
        # TODO: Test all invalid document formats
        # Should raise DocumentProcessingError with appropriate codes
        pass
    
    @pytest.mark.parametrize("invalid_url", [
        "not-a-url",
        "http://",
        "https://",
        "://example.com",
        "example.com",
        "ftp://example.com",
        "mailto:test@example.com",
    ])
    def test_validate_document_invalid_urls(self, invalid_url):
        """Test URL validation with various invalid formats"""
        # TODO: Test comprehensive invalid URL formats
        pass
    
    @pytest.mark.parametrize("content_length", [
        0,  # Exactly at minimum
        1,  # Just above minimum
        49999,  # Just under limit
        50000,  # Exactly at limit
        50001,  # Just over limit
        100000,  # Way over limit
    ])
    def test_content_length_boundaries(self, content_length):
        """Test content length boundary conditions"""
        # TODO: Test various content lengths around boundaries
        # Some should pass, some should fail
        pass
    
    @pytest.mark.asyncio
    async def test_process_batch_error_propagation(self):
        """Test that errors in batch processing don't crash the whole batch"""
        # TODO: Create batch with various error conditions
        # Verify errors are captured, not propagated
        pass
    
    # Add more edge case tests...
```

## Part 3: Quality-Focused Coverage Improvement (15 minutes)

### Task 5.6: Implement meaningful coverage improvements

Focus on writing tests that improve coverage AND provide real value:

```python
class TestQualityFocusedCoverage:
    """Coverage improvements that also provide real testing value"""
    
    @pytest.mark.asyncio
    async def test_concurrent_processing_thread_safety(self):
        """Test that concurrent processing is thread-safe"""
        # This test improves coverage AND tests important functionality
        processor = DocumentProcessor()
        
        documents = [
            {'url': f'https://example.com/{i}', 'content': f'Content {i}'}
            for i in range(20)
        ]
        
        # TODO: Process same documents concurrently multiple times
        # Verify no race conditions in cache or counters
        pass
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_large_batches(self):
        """Test memory behavior with large document batches"""
        # This test improves coverage AND verifies performance characteristics
        import psutil
        import os
        
        processor = DocumentProcessor()
        process = psutil.Process(os.getpid())
        
        # TODO: Process increasingly large batches
        # Monitor memory usage and verify it doesn't grow unboundedly
        pass
    
    def test_cache_behavior_over_time(self):
        """Test cache behavior with time-based scenarios"""
        # This improves coverage while testing realistic usage patterns
        processor = DocumentProcessor()
        
        # TODO: Test cache behavior over multiple processing sessions
        # Verify deduplication works correctly over time
        pass
    
    @pytest.mark.asyncio
    async def test_error_recovery_patterns(self):
        """Test system recovery after various error conditions"""
        # This improves coverage while testing resilience
        processor = DocumentProcessor()
        
        # TODO: Cause various errors, then verify system continues working
        # Test that error counts are accurate and system recovers
        pass
    
    def test_configuration_impacts_on_behavior(self):
        """Test how different configurations affect processing behavior"""
        # This improves coverage while testing configuration handling
        
        configs = [
            ProcessingConfig(chunk_size=500, overlap_size=50),
            ProcessingConfig(enable_deduplication=False),
            ProcessingConfig(max_content_length=1000),
        ]
        
        # TODO: Test same documents with different configs
        # Verify configs actually change behavior as expected
        pass
```

### Task 5.7: Coverage-driven refactoring

Sometimes improving coverage reveals design issues:

```python
def test_method_complexity_analysis(self):
    """Analyze method complexity and suggest refactoring"""
    from coverage_analyzer import CoverageAnalyzer
    
    analyzer = CoverageAnalyzer(DocumentProcessor)
    methods = analyzer.analyze_methods()
    
    # TODO: Identify methods with high complexity
    # Suggest which methods might benefit from refactoring
    # This test documents current complexity for future reference
    
    high_complexity_methods = [
        name for name, info in methods.items() 
        if info['complexity'] > 10
    ]
    
    # Document current state
    assert len(high_complexity_methods) <= 2, \
        f"Too many complex methods: {high_complexity_methods}"
```

## Part 4: Coverage Monitoring and Automation (10 minutes)

### Task 5.8: Set up automated coverage monitoring

Create `exercises/coverage_monitor.py`:

```python
import json
import subprocess
import sys
from typing import Dict, List, Any
from pathlib import Path

class CoverageMonitor:
    """Monitor and enforce coverage standards"""
    
    def __init__(self, target_coverage: float = 80.0):
        self.target_coverage = target_coverage
        self.coverage_file = Path("coverage.json")
    
    def run_coverage(self, test_paths: List[str]) -> Dict[str, Any]:
        """Run coverage analysis and return results"""
        # TODO: Run pytest with coverage
        # Parse coverage results
        # Return structured coverage data
        pass
    
    def analyze_coverage_trend(self, historical_data: List[Dict]) -> Dict[str, Any]:
        """Analyze coverage trends over time"""
        # TODO: Compare current coverage with historical data
        # Identify improving/declining areas
        # Return trend analysis
        pass
    
    def generate_coverage_report(self, coverage_data: Dict) -> str:
        """Generate human-readable coverage report"""
        # TODO: Create formatted report with:
        # - Overall coverage percentage
        # - Per-module breakdown
        # - Uncovered lines
        # - Recommendations
        pass
    
    def check_coverage_gates(self, coverage_data: Dict) -> bool:
        """Check if coverage meets quality gates"""
        # TODO: Implement coverage quality gates:
        # - Overall coverage >= target
        # - No module below minimum threshold
        # - Critical modules have higher requirements
        pass
    
    def suggest_improvements(self, coverage_data: Dict) -> List[str]:
        """Suggest specific coverage improvements"""
        # TODO: Analyze uncovered lines and suggest specific tests
        pass

# Usage in CI/CD
def main():
    monitor = CoverageMonitor(target_coverage=80.0)
    
    # Run coverage analysis
    coverage_data = monitor.run_coverage([
        "exercises/test_coverage_baseline.py",
        "exercises/test_coverage_improvement.py"
    ])
    
    # Check quality gates
    if not monitor.check_coverage_gates(coverage_data):
        print("Coverage quality gates failed!")
        print(monitor.generate_coverage_report(coverage_data))
        sys.exit(1)
    
    print("Coverage quality gates passed!")
    print(f"Overall coverage: {coverage_data['overall_coverage']:.1f}%")

if __name__ == "__main__":
    main()
```

### Task 5.9: Create coverage enforcement script

Create `exercises/enforce_coverage.sh`:

```bash
#!/bin/bash

set -e

echo "Running coverage analysis..."

# Set coverage thresholds
OVERALL_THRESHOLD=80
MODULE_THRESHOLD=70
CRITICAL_MODULE_THRESHOLD=90

# Run tests with coverage
uv run pytest exercises/ \
    --cov=exercises/document_processor \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=json \
    --cov-fail-under=$OVERALL_THRESHOLD

# Extract coverage data
OVERALL_COVERAGE=$(python -c "
import json
with open('coverage.json') as f:
    data = json.load(f)
    print(data['totals']['percent_covered'])
")

echo "Overall coverage: ${OVERALL_COVERAGE}%"

# Check module-specific coverage
python -c "
import json
import sys

with open('coverage.json') as f:
    data = json.load(f)

failed = False
for filename, file_data in data['files'].items():
    coverage = file_data['summary']['percent_covered']
    
    # Critical modules need higher coverage
    if 'document_processor' in filename:
        threshold = $CRITICAL_MODULE_THRESHOLD
    else:
        threshold = $MODULE_THRESHOLD
    
    if coverage < threshold:
        print(f'FAIL: {filename} coverage {coverage:.1f}% < {threshold}%')
        failed = True
    else:
        print(f'PASS: {filename} coverage {coverage:.1f}%')

if failed:
    sys.exit(1)
"

echo "All coverage thresholds met!"
```

## Part 5: Coverage Analysis and Reporting (10 minutes)

### Task 5.10: Comprehensive coverage analysis

Run comprehensive coverage analysis:

```bash
# Run all tests with detailed coverage
uv run pytest exercises/ \
    --cov=exercises/document_processor \
    --cov-report=html:coverage_html \
    --cov-report=term-missing \
    --cov-report=json:coverage.json \
    --cov-branch

# Generate coverage badge
coverage-badge -o coverage.svg

# Run mutation testing (if available)
# pip install mutmut
# mutmut run --paths-to-mutate=exercises/document_processor.py
```

### Task 5.11: Create final coverage assessment

Create `exercises/coverage_assessment.py`:

```python
import json
from pathlib import Path
from typing import Dict, List

def analyze_final_coverage():
    """Analyze final coverage results and provide assessment"""
    
    # Load coverage data
    with open('coverage.json') as f:
        coverage_data = json.load(f)
    
    # Overall metrics
    overall_coverage = coverage_data['totals']['percent_covered']
    missing_lines = coverage_data['totals']['missing_lines']
    
    print(f"=== FINAL COVERAGE ASSESSMENT ===")
    print(f"Overall Coverage: {overall_coverage:.1f}%")
    print(f"Missing Lines: {missing_lines}")
    
    # File-by-file analysis
    print(f"\n=== FILE ANALYSIS ===")
    for filename, file_data in coverage_data['files'].items():
        file_coverage = file_data['summary']['percent_covered']
        file_missing = len(file_data['missing_lines'])
        
        status = "✅" if file_coverage >= 80 else "❌"
        print(f"{status} {filename}: {file_coverage:.1f}% ({file_missing} missing)")
        
        if file_missing > 0:
            print(f"   Missing lines: {file_data['missing_lines']}")
    
    # Quality assessment
    print(f"\n=== QUALITY ASSESSMENT ===")
    
    if overall_coverage >= 90:
        grade = "A"
        assessment = "Excellent coverage"
    elif overall_coverage >= 80:
        grade = "B"
        assessment = "Good coverage"
    elif overall_coverage >= 70:
        grade = "C"
        assessment = "Adequate coverage"
    elif overall_coverage >= 60:
        grade = "D"
        assessment = "Poor coverage"
    else:
        grade = "F"
        assessment = "Insufficient coverage"
    
    print(f"Grade: {grade}")
    print(f"Assessment: {assessment}")
    
    # Recommendations
    print(f"\n=== RECOMMENDATIONS ===")
    
    if overall_coverage < 80:
        print("- Focus on testing error conditions and edge cases")
        print("- Add tests for branch conditions (if/else statements)")
        print("- Test exception handling paths")
    
    if missing_lines > 20:
        print("- Consider refactoring complex methods")
        print("- Break down large functions into smaller, testable units")
    
    print("- Review test quality, not just coverage numbers")
    print("- Consider mutation testing to verify test effectiveness")
    
    return {
        'overall_coverage': overall_coverage,
        'grade': grade,
        'missing_lines': missing_lines
    }

if __name__ == "__main__":
    analyze_final_coverage()
```

## Running and Verification

### Complete Test Suite Execution

```bash
# Run baseline tests
uv run pytest exercises/test_coverage_baseline.py -v

# Run improvement tests  
uv run pytest exercises/test_coverage_improvement.py -v

# Run complete coverage analysis
./exercises/enforce_coverage.sh

# Generate final assessment
python exercises/coverage_assessment.py
```

### Expected Results

Your final coverage should show:

- Overall coverage: 80%+
- No module below 70% coverage
- Critical modules (document_processor): 85%+
- Meaningful tests that provide real value

## Assessment Criteria

Your coverage improvement will be evaluated on:

1. **Coverage Achievement**: Reaching 80%+ overall coverage
2. **Test Quality**: Tests provide real value, not just coverage
3. **Strategic Focus**: Prioritizing important code paths
4. **Error Coverage**: Comprehensive testing of error conditions
5. **Maintainability**: Tests are clear, maintainable, and well-organized
6. **Automation**: Proper setup of coverage monitoring and enforcement

## Common Pitfalls to Avoid

1. **Coverage for Coverage's Sake**: Don't write meaningless tests just to hit lines
2. **Ignoring Test Quality**: High coverage with poor tests is worse than lower coverage with good tests
3. **Missing Error Paths**: Error handling often represents important but uncovered code
4. **Over-Mocking**: Too much mocking can make tests brittle and less valuable
5. **Configuration Neglect**: Don't forget to test different configuration scenarios

## Next Steps

After completing this exercise:

1. Apply these techniques to the real Crawl4AI codebase
2. Set up automated coverage monitoring in CI/CD
3. Establish team standards for coverage and test quality
4. Use coverage data to guide refactoring decisions

## Reflection Questions

1. How do you balance coverage goals with test quality and maintainability?
2. What types of code are most important to have high coverage for?
3. How can coverage data help identify code that needs refactoring?
4. What are the limitations of coverage metrics in assessing test suite quality?
5. How would you handle coverage requirements in a team setting?
