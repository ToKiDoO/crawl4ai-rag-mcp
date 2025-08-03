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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])