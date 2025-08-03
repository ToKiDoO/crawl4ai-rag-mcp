"""
Unit tests for refactored utility functions.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock, call
import os
import sys
from typing import List, Dict, Any

from utils_refactored import (
    create_embedding,
    create_embeddings_batch,
    generate_contextual_embedding,
    process_chunk_with_context,
    add_documents_to_database,
    search_documents,
    extract_code_blocks,
    generate_code_example_summary,
    add_code_examples_to_database,
    search_code_examples,
    extract_source_summary
)


class TestEmbeddingFunctions:
    """Test embedding generation functions"""
    
    @patch('utils_refactored.openai.embeddings.create')
    def test_create_embedding_success(self, mock_create):
        """Test successful embedding creation"""
        # Mock response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_create.return_value = mock_response
        
        # Test
        result = create_embedding("test text")
        
        # Verify
        assert len(result) == 1536
        assert result[0] == 0.1
        mock_create.assert_called_once_with(
            model="text-embedding-3-small",
            input=["test text"]
        )
    
    @patch('utils_refactored.openai.embeddings.create')
    def test_create_embedding_error(self, mock_create):
        """Test embedding creation with error"""
        # Mock error
        mock_create.side_effect = Exception("API Error")
        
        # Test - should return zero embedding
        result = create_embedding("test text")
        
        # Verify
        assert len(result) == 1536
        assert all(v == 0.0 for v in result)
    
    @patch('utils_refactored.create_embeddings_batch')
    def test_create_embedding_batch_failure(self, mock_batch):
        """Test create_embedding when batch function fails completely"""
        # Mock batch function to fail
        mock_batch.side_effect = Exception("Batch API Error")
        
        # Test - should trigger exception handling path and return zero embedding
        result = create_embedding("test text")
        
        # Verify
        assert len(result) == 1536
        assert all(v == 0.0 for v in result)
        mock_batch.assert_called_once_with(["test text"])
    
    @patch('utils_refactored.create_embeddings_batch')
    def test_create_embedding_empty_batch_response(self, mock_batch):
        """Test create_embedding when batch returns empty response"""
        # Mock batch function to return empty list
        mock_batch.return_value = []
        
        # Test - should return zero embedding when no embeddings returned
        result = create_embedding("test text")
        
        # Verify
        assert len(result) == 1536
        assert all(v == 0.0 for v in result)
    
    @patch('utils_refactored.openai.embeddings.create')
    def test_create_embeddings_batch_success(self, mock_create):
        """Test batch embedding creation"""
        # Mock response
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536)
        ]
        mock_create.return_value = mock_response
        
        # Test
        texts = ["text1", "text2"]
        result = create_embeddings_batch(texts)
        
        # Verify
        assert len(result) == 2
        assert result[0][0] == 0.1
        assert result[1][0] == 0.2
    
    @patch('utils_refactored.openai.embeddings.create')
    def test_create_embeddings_batch_empty(self, mock_create):
        """Test batch embedding with empty input"""
        result = create_embeddings_batch([])
        
        assert result == []
        mock_create.assert_not_called()
    
    @patch('utils_refactored.openai.embeddings.create')
    @patch('utils_refactored.time.sleep')
    def test_create_embeddings_batch_retry(self, mock_sleep, mock_create):
        """Test batch embedding with retries"""
        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_create.side_effect = [Exception("Temporary error"), mock_response]
        
        # Test
        result = create_embeddings_batch(["test"])
        
        # Verify
        assert len(result) == 1
        assert mock_create.call_count == 2
        mock_sleep.assert_called_once_with(1.0)
    
    @patch('utils_refactored.openai.embeddings.create')
    @patch('utils_refactored.time.sleep')
    def test_create_embeddings_batch_max_retries_then_fallback(self, mock_sleep, mock_create):
        """Test batch embedding falls back to individual after max retries"""
        # All batch attempts fail
        mock_create.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"), 
            Exception("Error 3"),
            # Individual attempts - first succeeds, second fails
            MagicMock(data=[MagicMock(embedding=[0.1] * 1536)]),
            Exception("Individual error")
        ]
        
        # Test
        result = create_embeddings_batch(["text1", "text2"])
        
        # Verify
        assert len(result) == 2
        assert result[0][0] == 0.1
        assert result[1][0] == 0.0  # Failed individual gets zero embedding
        assert mock_create.call_count == 5  # 3 batch + 2 individual


class TestContextualEmbedding:
    """Test contextual embedding generation"""
    
    @patch.dict(os.environ, {"MODEL_CHOICE": "gpt-4"})
    @patch('utils_refactored.openai.chat.completions.create')
    def test_generate_contextual_embedding_success(self, mock_create):
        """Test successful contextual embedding generation"""
        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="This chunk discusses testing"))]
        mock_create.return_value = mock_response
        
        # Test
        full_doc = "This is a full document about testing in Python"
        chunk = "Testing is important"
        result, success = generate_contextual_embedding(full_doc, chunk)
        
        # Verify
        assert success is True
        assert "This chunk discusses testing" in result
        assert chunk in result
        mock_create.assert_called_once()
    
    @patch('utils_refactored.openai.chat.completions.create')
    def test_generate_contextual_embedding_error(self, mock_create):
        """Test contextual embedding with error"""
        # Mock error
        mock_create.side_effect = Exception("API Error")
        
        # Test
        chunk = "Test chunk"
        result, success = generate_contextual_embedding("Full doc", chunk)
        
        # Verify
        assert success is False
        assert result == chunk  # Returns original chunk on error
    
    def test_process_chunk_with_context(self):
        """Test chunk processing helper function"""
        with patch('utils_refactored.generate_contextual_embedding') as mock_gen:
            mock_gen.return_value = ("Enhanced chunk", True)
            
            args = ("http://example.com", "chunk content", "full document")
            result = process_chunk_with_context(args)
            
            assert result == ("Enhanced chunk", True)
            mock_gen.assert_called_once_with("full document", "chunk content")


class TestDocumentOperations:
    """Test document database operations"""
    
    @pytest.mark.asyncio
    @patch('utils_refactored.create_embeddings_batch')
    async def test_add_documents_basic(self, mock_embeddings):
        """Test basic document addition"""
        # Setup
        mock_embeddings.return_value = [[0.1] * 1536, [0.2] * 1536]
        mock_db = AsyncMock()
        
        # Test
        await add_documents_to_database(
            database=mock_db,
            urls=["http://example.com/1", "http://example.com/2"],
            chunk_numbers=[0, 1],
            contents=["Content 1", "Content 2"],
            metadatas=[{"meta": "1"}, {"meta": "2"}],
            url_to_full_document={
                "http://example.com/1": "Full doc 1",
                "http://example.com/2": "Full doc 2"
            }
        )
        
        # Verify
        mock_db.add_documents.assert_called_once()
        call_args = mock_db.add_documents.call_args[1]
        assert call_args["urls"] == ["http://example.com/1", "http://example.com/2"]
        assert len(call_args["embeddings"]) == 2
        assert call_args["source_ids"] == ["example.com", "example.com"]
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_CONTEXTUAL_EMBEDDINGS": "true"})
    @patch('utils_refactored.create_embeddings_batch')
    @patch('utils_refactored.process_chunk_with_context')
    async def test_add_documents_with_contextual(self, mock_process, mock_embeddings):
        """Test document addition with contextual embeddings"""
        # Setup
        mock_process.side_effect = [
            ("Enhanced content 1", True),
            ("Enhanced content 2", True)
        ]
        mock_embeddings.return_value = [[0.1] * 1536]
        mock_db = AsyncMock()
        
        # Test
        await add_documents_to_database(
            database=mock_db,
            urls=["http://example.com/1"],
            chunk_numbers=[0],
            contents=["Content 1"],
            metadatas=[{"meta": "1"}],
            url_to_full_document={"http://example.com/1": "Full doc"}
        )
        
        # Verify contextual processing was used
        mock_process.assert_called_once()
        call_args = mock_db.add_documents.call_args[1]
        assert call_args["contents"][0] == "Enhanced content 1"
        assert call_args["metadatas"][0]["contextual_embedding"] is True
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_CONTEXTUAL_EMBEDDINGS": "true"})
    @patch('utils_refactored.create_embeddings_batch')
    @patch('utils_refactored.concurrent.futures.ThreadPoolExecutor')
    async def test_add_documents_contextual_processing_error(self, mock_executor, mock_embeddings):
        """Test document addition with contextual embedding processing error"""
        # Setup mock executor to simulate processing error
        mock_future = MagicMock()
        mock_future.result.side_effect = Exception("Processing error")
        
        mock_executor_instance = MagicMock()
        mock_executor_instance.__enter__.return_value = mock_executor_instance
        mock_executor_instance.submit.return_value = mock_future
        mock_executor_instance.as_completed.return_value = [mock_future]
        mock_executor.return_value = mock_executor_instance
        
        # Mock as_completed to return the futures
        with patch('utils_refactored.concurrent.futures.as_completed') as mock_as_completed:
            mock_as_completed.return_value = [mock_future]
            
            mock_embeddings.return_value = [[0.1] * 1536]
            mock_db = AsyncMock()
            
            # Test
            await add_documents_to_database(
                database=mock_db,
                urls=["http://example.com/1"],
                chunk_numbers=[0],
                contents=["Content 1"],
                metadatas=[{"meta": "1"}],
                url_to_full_document={"http://example.com/1": "Full doc"}
            )
            
            # Verify fallback to original content when processing fails
            call_args = mock_db.add_documents.call_args[1]
            assert "Content 1" in call_args["contents"]
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_CONTEXTUAL_EMBEDDINGS": "true"})
    @patch('utils_refactored.create_embeddings_batch')
    async def test_add_documents_contextual_length_mismatch(self, mock_embeddings):
        """Test document addition with contextual embedding length mismatch"""
        mock_embeddings.return_value = [[0.1] * 1536, [0.2] * 1536]
        mock_db = AsyncMock()
        
        # Mock concurrent.futures to simulate incomplete results
        with patch('utils_refactored.concurrent.futures.ThreadPoolExecutor') as mock_executor, \
             patch('utils_refactored.concurrent.futures.as_completed') as mock_as_completed:
            
            # Create mock futures - one for each content
            mock_future_1 = MagicMock()
            mock_future_1.result.return_value = ("Enhanced content 1", True)
            
            mock_future_2 = MagicMock()
            mock_future_2.result.return_value = ("Enhanced content 2", True)
            
            mock_executor_instance = MagicMock()
            mock_executor_instance.__enter__.return_value = mock_executor_instance
            
            # Set up the future_to_idx mapping correctly
            def mock_submit(func, args):
                if "Content 1" in str(args):
                    return mock_future_1
                else:
                    return mock_future_2
            
            mock_executor_instance.submit.side_effect = mock_submit
            mock_executor.return_value = mock_executor_instance
            
            # Simulate getting only one result (length mismatch)
            mock_as_completed.return_value = [mock_future_1]  # Only return first future
            
            # Test with 2 contents but only 1 future completes
            await add_documents_to_database(
                database=mock_db,
                urls=["http://example.com/1", "http://example.com/2"],
                chunk_numbers=[0, 1],
                contents=["Content 1", "Content 2"],
                metadatas=[{"meta": "1"}, {"meta": "2"}],
                url_to_full_document={
                    "http://example.com/1": "Full doc 1",
                    "http://example.com/2": "Full doc 2"
                }
            )
            
            # The function should detect length mismatch and fallback to original contents
            call_args = mock_db.add_documents.call_args[1]
            # It should fallback to original contents when there's a length mismatch
            assert call_args["contents"] == ["Content 1", "Content 2"]
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {"USE_CONTEXTUAL_EMBEDDINGS": "false"})
    @patch('utils_refactored.create_embeddings_batch')
    async def test_add_documents_without_contextual(self, mock_embeddings):
        """Test document addition without contextual embeddings - covers lines 217-218"""
        # Setup
        mock_embeddings.return_value = [[0.1] * 1536, [0.2] * 1536]
        mock_db = AsyncMock()
        
        # Test
        await add_documents_to_database(
            database=mock_db,
            urls=["http://example.com/1", "http://example.com/2"],
            chunk_numbers=[0, 1],
            contents=["Content 1", "Content 2"],
            metadatas=[{"meta": "1"}, {"meta": "2"}],
            url_to_full_document={
                "http://example.com/1": "Full doc 1",
                "http://example.com/2": "Full doc 2"
            }
        )
        
        # Verify original contents were used (no contextual processing)
        call_args = mock_db.add_documents.call_args[1]
        assert call_args["contents"] == ["Content 1", "Content 2"]
        assert len(call_args["embeddings"]) == 2
    
    @pytest.mark.asyncio
    @patch('utils_refactored.create_embedding')
    async def test_search_documents(self, mock_embedding):
        """Test document search"""
        # Setup
        mock_embedding.return_value = [0.5] * 1536
        mock_db = AsyncMock()
        mock_db.search_documents.return_value = [
            {"id": "1", "content": "Test result", "similarity": 0.9}
        ]
        
        # Test
        results = await search_documents(
            database=mock_db,
            query="test query",
            match_count=10
        )
        
        # Verify
        assert len(results) == 1
        assert results[0]["content"] == "Test result"
        mock_embedding.assert_called_once_with("test query")
        mock_db.search_documents.assert_called_once()


class TestCodeBlockExtraction:
    """Test code block extraction functions"""
    
    def test_extract_code_blocks_basic(self):
        """Test basic code block extraction"""
        markdown = """
Some text here

```python
def hello():
    return "world"
```

More text

```javascript
console.log("test");
```
"""
        
        # Test with small min_length
        blocks = extract_code_blocks(markdown, min_length=10)
        
        assert len(blocks) == 2
        assert blocks[0]["language"] == "python"
        assert "def hello():" in blocks[0]["code"]
        assert blocks[1]["language"] == "javascript"
        assert "console.log" in blocks[1]["code"]
    
    def test_extract_code_blocks_min_length(self):
        """Test code block extraction with minimum length filter"""
        markdown = """
```python
x = 1
```

```python
def complex_function():
    # This is a longer code block
    result = []
    for i in range(100):
        result.append(i * 2)
    return result
```
"""
        
        # Test with larger min_length
        blocks = extract_code_blocks(markdown, min_length=50)
        
        assert len(blocks) == 1
        assert "complex_function" in blocks[0]["code"]
    
    def test_extract_code_blocks_edge_cases(self):
        """Test edge cases for code block extraction"""
        # Empty markdown
        assert extract_code_blocks("") == []
        
        # No code blocks
        assert extract_code_blocks("Just plain text") == []
        
        # Code block at start
        markdown = """```python
code here
```"""
        blocks = extract_code_blocks(markdown, min_length=1)
        assert len(blocks) == 1
    
    def test_extract_code_blocks_language_parsing_edge_cases(self):
        """Test edge cases for language parsing in code blocks"""
        # Code block without language specifier
        markdown1 = """```
def hello():
    return "world"
```"""
        blocks1 = extract_code_blocks(markdown1, min_length=1)
        assert len(blocks1) == 1
        assert blocks1[0]["language"] == ""
        assert "def hello():" in blocks1[0]["code"]
        
        # Code block with first line containing spaces (not a language)
        markdown2 = """```
This is some code text
def hello():
    return "world"
```"""
        blocks2 = extract_code_blocks(markdown2, min_length=1)
        assert len(blocks2) == 1
        assert blocks2[0]["language"] == ""
        assert "This is some code text" in blocks2[0]["code"]
        
        # Code block with very long first line (not a language)
        markdown3 = """```
this_is_a_very_long_language_name_that_exceeds_twenty_characters
def hello():
    return "world"
```"""
        blocks3 = extract_code_blocks(markdown3, min_length=1)
        assert len(blocks3) == 1
        assert blocks3[0]["language"] == ""
        
        # Code block with only first line (language specifier)
        markdown4 = """```python
```"""
        blocks4 = extract_code_blocks(markdown4, min_length=0)  # Use min_length=0 for empty code
        assert len(blocks4) == 1
        assert blocks4[0]["language"] == "python"
        assert blocks4[0]["code"] == ""
        
        # Code block with single line content after language
        markdown5 = """```javascript
console.log("test");
```"""
        blocks5 = extract_code_blocks(markdown5, min_length=1)
        assert len(blocks5) == 1
        assert blocks5[0]["language"] == "javascript"
        assert blocks5[0]["code"] == 'console.log("test");\n'
        
        # Test code block with no line split (lines < 2) - triggers line 322-324
        markdown6 = """```
single line without newline```"""
        blocks6 = extract_code_blocks(markdown6, min_length=1)
        assert len(blocks6) == 1
        assert blocks6[0]["language"] == ""
        assert blocks6[0]["code"] == "\nsingle line without newline"
        
        # Test code block with NO newlines at all - triggers lines 323-324 (else block)
        markdown7 = """```code without any newlines```"""
        blocks7 = extract_code_blocks(markdown7, min_length=1)
        assert len(blocks7) == 1
        assert blocks7[0]["language"] == ""
        assert blocks7[0]["code"] == "code without any newlines"
    
    def test_extract_code_blocks_context(self):
        """Test code block context extraction"""
        markdown = """
This is context before the code block.

```python
def test():
    pass
```

This is context after the code block.
"""
        
        blocks = extract_code_blocks(markdown, min_length=1)
        
        assert len(blocks) == 1
        assert "context before" in blocks[0]["context_before"]
        assert "context after" in blocks[0]["context_after"]
    
    @patch('utils_refactored.openai.chat.completions.create')
    def test_generate_code_example_summary_success(self, mock_create):
        """Test code example summary generation"""
        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="A test function example"))]
        mock_create.return_value = mock_response
        
        # Test
        summary = generate_code_example_summary(
            code="def test(): pass",
            context_before="Before",
            context_after="After"
        )
        
        assert summary == "A test function example"
    
    @patch('utils_refactored.openai.chat.completions.create')
    def test_generate_code_example_summary_error(self, mock_create):
        """Test code example summary with error"""
        # Mock error
        mock_create.side_effect = Exception("API Error")
        
        # Test
        summary = generate_code_example_summary("code", "before", "after")
        
        assert summary == "Code example for demonstration purposes."


class TestCodeExampleOperations:
    """Test code example database operations"""
    
    @pytest.mark.asyncio
    @patch('utils_refactored.create_embeddings_batch')
    async def test_add_code_examples(self, mock_embeddings):
        """Test adding code examples"""
        # Setup
        mock_embeddings.return_value = [[0.1] * 1536]
        mock_db = AsyncMock()
        
        # Test
        await add_code_examples_to_database(
            database=mock_db,
            urls=["http://example.com"],
            chunk_numbers=[0],
            code_examples=["def test(): pass"],
            summaries=["Test function"],
            metadatas=[{"lang": "python"}]
        )
        
        # Verify
        mock_db.add_code_examples.assert_called_once()
        call_args = mock_db.add_code_examples.call_args[1]
        assert call_args["urls"] == ["http://example.com"]
        assert len(call_args["embeddings"]) == 1
    
    @pytest.mark.asyncio
    async def test_add_code_examples_empty_urls(self):
        """Test adding code examples with empty URLs list"""
        mock_db = AsyncMock()
        
        # Test with empty URLs - should return early
        await add_code_examples_to_database(
            database=mock_db,
            urls=[],
            chunk_numbers=[],
            code_examples=[],
            summaries=[],
            metadatas=[]
        )
        
        # Verify no database operations were called
        mock_db.add_code_examples.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('utils_refactored.create_embedding')
    async def test_search_code_examples(self, mock_embedding):
        """Test searching code examples"""
        # Setup
        mock_embedding.return_value = [0.5] * 1536
        mock_db = AsyncMock()
        mock_db.search_code_examples.return_value = [
            {"id": "1", "content": "def test(): pass", "summary": "Test", "similarity": 0.9}
        ]
        
        # Test
        results = await search_code_examples(
            database=mock_db,
            query="test function",
            match_count=5
        )
        
        # Verify
        assert len(results) == 1
        assert results[0]["summary"] == "Test"
        # Check enhanced query was used
        mock_embedding.assert_called_once()
        assert "Code example for" in mock_embedding.call_args[0][0]


class TestSourceSummary:
    """Test source summary extraction"""
    
    @patch.dict(os.environ, {"MODEL_CHOICE": "gpt-4"})
    @patch('utils_refactored.openai.chat.completions.create')
    def test_extract_source_summary_success(self, mock_create):
        """Test successful source summary extraction"""
        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="This is a testing library"))]
        mock_create.return_value = mock_response
        
        # Test
        summary = extract_source_summary("pytest.org", "Content about pytest testing framework")
        
        assert summary == "This is a testing library"
    
    def test_extract_source_summary_empty_content(self):
        """Test source summary with empty content"""
        summary = extract_source_summary("example.com", "")
        assert summary == "Content from example.com"
    
    @patch('utils_refactored.openai.chat.completions.create')
    def test_extract_source_summary_error(self, mock_create):
        """Test source summary with API error"""
        # Mock error
        mock_create.side_effect = Exception("API Error")
        
        # Test
        summary = extract_source_summary("example.com", "Some content")
        
        assert summary == "Content from example.com"
    
    @patch('utils_refactored.openai.chat.completions.create')
    def test_extract_source_summary_max_length(self, mock_create):
        """Test source summary respects max length"""
        # Mock very long response
        long_summary = "A" * 600
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=long_summary))]
        mock_create.return_value = mock_response
        
        # Test
        summary = extract_source_summary("example.com", "content", max_length=500)
        
        assert len(summary) == 503  # 500 + "..."
        assert summary.endswith("...")


class TestBatchProcessingAndEdgeCases:
    """Test batch processing and additional edge cases"""
    
    @pytest.mark.asyncio
    @patch('utils_refactored.create_embeddings_batch')
    async def test_add_documents_large_batch_processing(self, mock_embeddings):
        """Test document addition with large batches"""
        # Setup - simulate processing 50 documents with batch size 20
        mock_embeddings.side_effect = [
            [[0.1] * 1536] * 20,  # First batch
            [[0.2] * 1536] * 20,  # Second batch  
            [[0.3] * 1536] * 10   # Final batch
        ]
        mock_db = AsyncMock()
        
        # Create 50 documents
        urls = [f"http://example.com/{i}" for i in range(50)]
        chunk_numbers = list(range(50))
        contents = [f"Content {i}" for i in range(50)]
        metadatas = [{"chunk": i} for i in range(50)]
        url_to_full_document = {url: f"Full document {i}" for i, url in enumerate(urls)}
        
        # Test
        await add_documents_to_database(
            database=mock_db,
            urls=urls,
            chunk_numbers=chunk_numbers,
            contents=contents,
            metadatas=metadatas,
            url_to_full_document=url_to_full_document,
            batch_size=20
        )
        
        # Verify batched embedding creation
        assert mock_embeddings.call_count == 3
        
        # Verify all documents were added
        call_args = mock_db.add_documents.call_args[1]
        assert len(call_args["urls"]) == 50
        assert len(call_args["embeddings"]) == 50
    
    @pytest.mark.asyncio
    @patch('utils_refactored.create_embeddings_batch')
    async def test_add_code_examples_large_batch_processing(self, mock_embeddings):
        """Test code example addition with large batches"""
        # Setup - simulate processing 50 code examples with batch size 20
        mock_embeddings.side_effect = [
            [[0.1] * 1536] * 20,  # First batch
            [[0.2] * 1536] * 20,  # Second batch
            [[0.3] * 1536] * 10   # Final batch
        ]
        mock_db = AsyncMock()
        
        # Create 50 code examples
        urls = [f"http://example.com/{i}" for i in range(50)]
        chunk_numbers = list(range(50))
        code_examples = [f"def function_{i}(): pass" for i in range(50)]
        summaries = [f"Function {i} description" for i in range(50)]
        metadatas = [{"lang": "python", "chunk": i} for i in range(50)]
        
        # Test
        await add_code_examples_to_database(
            database=mock_db,
            urls=urls,
            chunk_numbers=chunk_numbers,
            code_examples=code_examples,
            summaries=summaries,
            metadatas=metadatas,
            batch_size=20
        )
        
        # Verify batched embedding creation
        assert mock_embeddings.call_count == 3
        
        # Verify all code examples were added
        call_args = mock_db.add_code_examples.call_args[1]
        assert len(call_args["urls"]) == 50
        assert len(call_args["embeddings"]) == 50
    
    def test_url_parsing_edge_cases(self):
        """Test URL parsing for source ID extraction"""
        from urllib.parse import urlparse
        
        # Test various URL formats that should produce source IDs
        test_cases = [
            ("http://example.com/path", "example.com"),
            ("https://docs.python.org/3/library/os.html", "docs.python.org"),
            ("file:///local/path/file.txt", "/local/path/file.txt"),
            ("relative/path/file.txt", "relative/path/file.txt"),
            ("", ""),
        ]
        
        for url, expected_source_id in test_cases:
            parsed_url = urlparse(url)
            source_id = parsed_url.netloc or parsed_url.path
            assert source_id == expected_source_id
    
    @patch('utils_refactored.openai.chat.completions.create')
    def test_generate_contextual_embedding_token_limit(self, mock_create):
        """Test contextual embedding generation with very long documents"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Context for chunk"))]
        mock_create.return_value = mock_response
        
        # Test with very long document (should be truncated to 25000 chars)
        very_long_document = "A" * 30000
        chunk = "This is a test chunk"
        
        result, success = generate_contextual_embedding(very_long_document, chunk)
        
        # Verify the document was truncated in the prompt
        assert success is True
        call_args = mock_create.call_args[1]  # Use keyword arguments
        prompt_content = call_args["messages"][1]["content"]
        # Check that document section is within the 25000 character limit
        document_section = prompt_content.split("</document>")[0].split("<document>")[1].strip()
        assert len(document_section) == 25000
    
    @patch('utils_refactored.openai.chat.completions.create')
    def test_generate_code_example_summary_truncation(self, mock_create):
        """Test code example summary generation with truncation"""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Summary of code"))]
        mock_create.return_value = mock_response
        
        # Test with very long inputs that should be truncated
        long_code = "def function():\n" + "    # comment\n" * 1000  # Very long code
        long_context_before = "B" * 1000  # Long context
        long_context_after = "A" * 1000   # Long context
        
        summary = generate_code_example_summary(long_code, long_context_before, long_context_after)
        
        assert summary == "Summary of code"
        
        # Verify truncation was applied in the prompt
        call_args = mock_create.call_args[1]  # Use keyword arguments
        prompt_content = call_args["messages"][1]["content"]
        
        # Check that code was truncated to 1500 chars
        code_section = prompt_content.split("</code_example>")[0].split("<code_example>")[1].strip()
        assert len(code_section) <= 1500
        
        # Check that context sections were truncated to 500 chars
        context_before_section = prompt_content.split("</context_before>")[0].split("<context_before>")[1].strip()
        assert len(context_before_section) <= 500
        
        context_after_section = prompt_content.split("</context_after>")[0].split("<context_after>")[1].strip()
        assert len(context_after_section) <= 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])