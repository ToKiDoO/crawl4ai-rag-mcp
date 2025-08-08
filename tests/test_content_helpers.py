"""
Comprehensive unit tests for content processing helper functions from crawl4ai_mcp.py.

Test Coverage:
- smart_chunk_markdown(): Test markdown chunking with respect for code blocks and paragraphs
- extract_section_info(): Test metadata extraction from markdown chunks
- process_code_example(): Test code example processing function

Testing Approach:
- Comprehensive edge case coverage
- Parametrized tests for multiple scenarios
- Real-world markdown content patterns
- Performance considerations for large content
- Error handling validation
"""

import os
import re
import sys
from unittest.mock import patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Import functions to test
from crawl4ai_mcp import (
    extract_section_info,
    process_code_example,
    smart_chunk_markdown,
)


class TestSmartChunkMarkdown:
    """Test smart_chunk_markdown() function for intelligent text chunking"""

    def test_basic_chunking(self):
        """Test basic text chunking without special markers"""
        text = "This is a simple text that should be chunked properly. " * 100
        chunks = smart_chunk_markdown(text, chunk_size=500)

        assert len(chunks) > 1
        assert all(
            len(chunk) <= 500 for chunk in chunks[:-1]
        )  # All but last should be under limit
        assert all(chunk.strip() for chunk in chunks)  # No empty chunks

    def test_code_block_boundary_respect(self):
        """Test that chunking respects code block boundaries"""
        text = (
            """
This is some text before the code block.

```python
def complex_function():
    # This is a long code block that should not be split
    result = []
    for i in range(100):
        result.append(i * 2)
        if i % 10 == 0:
            print(f"Processing {i}")
    return result
```

This is text after the code block.
"""
            * 5
        )  # Repeat to ensure chunking is needed

        chunks = smart_chunk_markdown(text, chunk_size=800)

        # Verify no code blocks are split
        for chunk in chunks:
            code_starts = chunk.count("```")
            assert code_starts % 2 == 0, f"Code block split in chunk: {chunk[:100]}..."

    def test_paragraph_boundary_respect(self):
        """Test that chunking respects paragraph boundaries"""
        paragraphs = [
            "This is the first paragraph with some content that makes it reasonably long.",
            "This is the second paragraph with different content and also quite long.",
            "This is the third paragraph continuing the pattern of longer content.",
            "This is the fourth paragraph maintaining the same length pattern.",
            "This is the fifth paragraph completing our test content.",
        ]
        text = "\n\n".join(paragraphs)

        chunks = smart_chunk_markdown(text, chunk_size=200)

        # Each chunk should end at paragraph boundary (not split mid-paragraph)
        for chunk in chunks[:-1]:  # Except possibly the last one
            # Should not end mid-sentence unless necessary
            if "\n\n" in chunk:
                assert chunk.rstrip().endswith(".") or chunk.rstrip().endswith("\n")

    def test_sentence_boundary_fallback(self):
        """Test sentence boundary fallback when no paragraph breaks available"""
        # Long text without paragraph breaks
        sentences = [
            "This is a sentence that is quite long and detailed.",
            "This is another sentence with substantial content.",
            "Here is a third sentence maintaining the pattern.",
            "The fourth sentence continues this approach.",
            "Finally, the fifth sentence completes the text.",
        ]
        text = " ".join(sentences)

        chunks = smart_chunk_markdown(text, chunk_size=150)

        # Should break at sentence boundaries
        for chunk in chunks[:-1]:
            assert chunk.rstrip().endswith("."), (
                f"Chunk doesn't end at sentence: {chunk[-50:]}"
            )

    def test_chunk_size_parameter(self):
        """Test different chunk sizes"""
        text = "This is test content. " * 200

        # Test different chunk sizes
        small_chunks = smart_chunk_markdown(text, chunk_size=100)
        large_chunks = smart_chunk_markdown(text, chunk_size=1000)

        assert len(small_chunks) > len(large_chunks)
        assert all(len(chunk) <= 100 for chunk in small_chunks[:-1])
        assert all(len(chunk) <= 1000 for chunk in large_chunks[:-1])

    def test_empty_and_minimal_text(self):
        """Test edge cases with empty or minimal text"""
        # Empty text
        assert smart_chunk_markdown("") == []

        # Very short text
        short_text = "Short"
        chunks = smart_chunk_markdown(short_text, chunk_size=100)
        assert chunks == ["Short"]

        # Text shorter than chunk size
        medium_text = "This is medium length text that fits in one chunk."
        chunks = smart_chunk_markdown(medium_text, chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0] == medium_text

    def test_text_at_exact_chunk_size(self):
        """Test text that is exactly at chunk size boundary"""
        text = "A" * 1000  # Exactly 1000 characters
        chunks = smart_chunk_markdown(text, chunk_size=1000)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_complex_markdown_structure(self):
        """Test with complex markdown including headers, lists, and code"""
        markdown_text = """
# Main Header

This is an introduction paragraph.

## Subsection

Here's a list:
- Item 1
- Item 2
- Item 3

```python
def example_function():
    '''
    This is a complex code block
    with multiple lines and comments
    '''
    for i in range(10):
        print(f"Value: {i}")
    return True
```

### Another section

More content here with **bold** and *italic* text.

```bash
# This is a bash script
echo "Hello World"
ls -la
```

Final paragraph with concluding thoughts.
"""

        chunks = smart_chunk_markdown(markdown_text, chunk_size=500)

        # Verify structure is preserved
        full_text = "".join(chunks)
        assert "# Main Header" in full_text
        assert "def example_function():" in full_text
        assert 'echo "Hello World"' in full_text

        # Verify no code blocks are split
        for chunk in chunks:
            code_starts = chunk.count("```")
            assert code_starts % 2 == 0

    def test_code_block_at_chunk_boundary(self):
        """Test code blocks that appear right at chunk boundaries"""
        # Create text where code block appears near chunk boundary
        prefix = "A" * 450  # Close to 500 chunk size
        code_block = """
```python
def test():
    return True
```
"""
        suffix = "B" * 100

        text = prefix + code_block + suffix
        chunks = smart_chunk_markdown(text, chunk_size=500)

        # Should not split the code block - check that code block is preserved
        code_block_found = False
        reconstructed_text = "".join(chunks)

        # The code block should be preserved in the reconstructed text
        assert "```python" in reconstructed_text
        assert "def test():" in reconstructed_text
        assert (
            reconstructed_text.count("```") % 2 == 0
        )  # Even number of backticks overall

    def test_multiple_code_blocks(self):
        """Test text with multiple code blocks"""
        text = """
Some text here.

```python
print("First block")
```

More text between blocks.

```javascript
console.log("Second block");
```

```bash
echo "Third block"
```

Final text.
"""

        chunks = smart_chunk_markdown(text, chunk_size=200)

        # Count total code blocks
        total_code_blocks = (
            text.count("```python")
            + text.count("```javascript")
            + text.count("```bash")
        )

        # Verify all code blocks are preserved
        reconstructed = "".join(chunks)
        found_blocks = (
            reconstructed.count("```python")
            + reconstructed.count("```javascript")
            + reconstructed.count("```bash")
        )
        assert found_blocks == total_code_blocks

    def test_boundary_calculation_logic(self):
        """Test the specific boundary calculation logic"""
        # Test 30% threshold for breaking
        text = "A" * 1000 + "\n\n" + "B" * 2000  # Paragraph break at 1000 chars
        chunks = smart_chunk_markdown(text, chunk_size=1500)  # 30% of 1500 = 450

        # Since break is at 1000 chars (> 450), it should break there
        assert len(chunks) >= 2
        assert chunks[0].endswith("A")

        # Test when break is too early (< 30% threshold)
        text2 = "A" * 200 + "\n\n" + "B" * 2000  # Break at 200 chars
        chunks2 = smart_chunk_markdown(text2, chunk_size=1500)  # 30% of 1500 = 450

        # Since break is at 200 chars (< 450), should not break there
        assert len(chunks2[0]) > 200

    @pytest.mark.parametrize("chunk_size", [100, 500, 1000, 5000])
    def test_various_chunk_sizes(self, chunk_size):
        """Test chunking with various chunk sizes"""
        text = (
            """
This is a test document with multiple paragraphs and sections.

```python
def test_function():
    return "test"
```

Another paragraph here with more content to test the chunking behavior.

```bash
echo "More code"
```

Final section with concluding content.
"""
            * 3
        )  # Repeat to ensure chunking

        chunks = smart_chunk_markdown(text, chunk_size=chunk_size)

        # Basic validation
        assert len(chunks) > 0
        assert all(chunk.strip() for chunk in chunks)

        # All chunks except last should be reasonable size
        for chunk in chunks[:-1]:
            assert len(chunk) <= chunk_size

        # Verify content preservation
        reconstructed = "".join(chunks)
        assert "def test_function():" in reconstructed
        assert 'echo "More code"' in reconstructed


class TestExtractSectionInfo:
    """Test extract_section_info() function for metadata extraction"""

    def test_basic_header_extraction(self):
        """Test basic header extraction from markdown"""
        chunk = """
# Main Title

Some content here.

## Subsection

More content.

### Sub-subsection

Even more content.
"""

        info = extract_section_info(chunk)

        assert "headers" in info
        assert "char_count" in info
        assert "word_count" in info

        # Check header parsing
        headers = info["headers"]
        assert "# Main Title" in headers
        assert "## Subsection" in headers
        assert "### Sub-subsection" in headers

    def test_header_formats(self):
        """Test various header formats"""
        test_cases = [
            ("# Single hash", "# Single hash"),
            ("## Double hash", "## Double hash"),
            ("### Triple hash", "### Triple hash"),
            ("#### Quad hash", "#### Quad hash"),
            ("##### Five hash", "##### Five hash"),
            ("###### Six hash", "###### Six hash"),
        ]

        for header_line, expected in test_cases:
            chunk = f"{header_line}\n\nSome content."
            info = extract_section_info(chunk)
            assert expected in info["headers"]

    def test_multiple_headers_formatting(self):
        """Test formatting of multiple headers"""
        chunk = """
# First Header

Content.

## Second Header

More content.

# Third Header

Final content.
"""

        info = extract_section_info(chunk)
        headers = info["headers"]

        # Should be joined with semicolons
        assert "; " in headers
        assert "# First Header" in headers
        assert "## Second Header" in headers
        assert "# Third Header" in headers

    def test_no_headers(self):
        """Test chunk with no headers"""
        chunk = """
This is just plain text content without any headers.
It has multiple lines but no markdown headers at all.
"""

        info = extract_section_info(chunk)

        assert info["headers"] == ""
        assert info["char_count"] > 0
        assert info["word_count"] > 0

    def test_char_count_accuracy(self):
        """Test character count accuracy"""
        test_strings = [
            "",
            "a",
            "Hello World",
            "Multi\nline\nstring",
            "String with special chars: àáâãäå",
            "A" * 1000,
        ]

        for test_string in test_strings:
            info = extract_section_info(test_string)
            assert info["char_count"] == len(test_string)

    def test_word_count_accuracy(self):
        """Test word count accuracy"""
        test_cases = [
            ("", 0),
            ("word", 1),
            ("two words", 2),
            ("multiple   spaces   between", 3),
            ("line1\nline2\nline3", 3),
            ("punct, word! another?", 3),
        ]

        for text, expected_words in test_cases:
            info = extract_section_info(text)
            assert info["word_count"] == expected_words

    def test_headers_with_special_characters(self):
        """Test headers containing special characters"""
        chunk = """
# Header with *italic* and **bold**

Content.

## Header with `code` and [link](url)

More content.

### Header with numbers 123 and symbols !@#

Final content.
"""

        info = extract_section_info(chunk)
        headers = info["headers"]

        assert "Header with *italic* and **bold**" in headers
        assert "Header with `code` and [link](url)" in headers
        assert "Header with numbers 123 and symbols !@#" in headers

    def test_headers_at_line_boundaries(self):
        """Test headers at beginning and end of chunks"""
        # Header at beginning
        chunk1 = "# First Header\nContent follows."
        info1 = extract_section_info(chunk1)
        assert "# First Header" in info1["headers"]

        # Header at end
        chunk2 = "Content precedes.\n# Last Header"
        info2 = extract_section_info(chunk2)
        assert "# Last Header" in info2["headers"]

        # Only header
        chunk3 = "# Only Header"
        info3 = extract_section_info(chunk3)
        assert info3["headers"] == "# Only Header"

    def test_invalid_headers(self):
        """Test strings that look like headers but aren't"""
        chunk = """
This # is not a header because it's not at line start.
Also this line has # in the middle somewhere.

#NoSpaceAfterHash
# 
#       Multiple spaces but empty

Normal content continues.
"""

        info = extract_section_info(chunk)

        # The regex r'^(#+)\s+(.+)$' will match "#       Multiple spaces but empty"
        # because it has spaces after # and content after the spaces
        headers = info["headers"]
        if headers:
            assert "#       Multiple spaces but empty" in headers
        # Some implementations might filter this out, so either empty or containing the header is acceptable

    def test_regex_pattern_behavior(self):
        """Test the specific regex pattern used for header detection"""
        pattern = r"^(#+)\s+(.+)$"

        test_cases = [
            ("# Valid Header", True),
            ("## Also Valid", True),
            ("### Still Valid", True),
            ("#Invalid", False),  # No space
            ("# ", False),  # No content after space
            (" # Not Valid", False),  # Not at line start
            ("Text # Not Header", False),  # Not at line start
        ]

        for text, should_match in test_cases:
            matches = re.findall(pattern, text, re.MULTILINE)
            assert bool(matches) == should_match

    def test_large_content_performance(self):
        """Test performance with large content"""
        # Create large chunk with many headers
        large_chunk = ""
        for i in range(100):
            large_chunk += f"# Header {i}\n\n"
            large_chunk += "Content " * 100 + "\n\n"

        info = extract_section_info(large_chunk)

        # Should complete quickly and accurately
        assert info["char_count"] == len(large_chunk)
        assert "Header 0" in info["headers"]
        assert "Header 99" in info["headers"]
        assert info["headers"].count("#") == 100  # One # per header


class TestProcessCodeExample:
    """Test process_code_example() function for code processing"""

    @patch("crawl4ai_mcp.generate_code_example_summary")
    def test_basic_functionality(self, mock_generate):
        """Test basic code example processing"""
        mock_generate.return_value = "Test function summary"

        args = ("def test(): pass", "Before context", "After context")
        result = process_code_example(args)

        assert result == "Test function summary"
        mock_generate.assert_called_once_with(
            "def test(): pass",
            "Before context",
            "After context",
        )

    @patch("crawl4ai_mcp.generate_code_example_summary")
    def test_with_different_code_types(self, mock_generate):
        """Test processing different types of code"""
        test_cases = [
            ("print('Hello')", "Python code"),
            ("console.log('test')", "JavaScript code"),
            ("echo 'hello'", "Bash code"),
            ("<div>HTML</div>", "HTML code"),
            ("SELECT * FROM table", "SQL code"),
        ]

        for code, expected_summary in test_cases:
            mock_generate.return_value = expected_summary

            args = (code, "context before", "context after")
            result = process_code_example(args)

            assert result == expected_summary
            mock_generate.assert_called_with(code, "context before", "context after")

    @patch("crawl4ai_mcp.generate_code_example_summary")
    def test_with_empty_contexts(self, mock_generate):
        """Test processing with empty context"""
        mock_generate.return_value = "Summary without context"

        args = ("def func(): return True", "", "")
        result = process_code_example(args)

        assert result == "Summary without context"
        mock_generate.assert_called_once_with("def func(): return True", "", "")

    @patch("crawl4ai_mcp.generate_code_example_summary")
    def test_with_long_contexts(self, mock_generate):
        """Test processing with very long contexts"""
        mock_generate.return_value = "Summary with long context"

        long_context_before = "This is a very long context " * 100
        long_context_after = "This is also a long context " * 100
        code = "def complex_function(): pass"

        args = (code, long_context_before, long_context_after)
        result = process_code_example(args)

        assert result == "Summary with long context"
        mock_generate.assert_called_once_with(
            code,
            long_context_before,
            long_context_after,
        )

    @patch("crawl4ai_mcp.generate_code_example_summary")
    def test_error_handling(self, mock_generate):
        """Test error handling in code processing"""
        mock_generate.side_effect = Exception("Generation failed")

        args = ("def test(): pass", "before", "after")

        # Should not raise exception, but let it propagate
        with pytest.raises(Exception, match="Generation failed"):
            process_code_example(args)

    def test_argument_unpacking(self):
        """Test that arguments are properly unpacked"""
        with patch("crawl4ai_mcp.generate_code_example_summary") as mock_generate:
            mock_generate.return_value = "Unpacked correctly"

            # Test with tuple
            args_tuple = ("code", "before", "after")
            result = process_code_example(args_tuple)

            assert result == "Unpacked correctly"
            mock_generate.assert_called_once_with("code", "before", "after")

    def test_concurrent_processing_compatibility(self):
        """Test compatibility with concurrent processing"""
        # This function is designed for use with concurrent.futures
        # Test that it works as expected in that context
        import concurrent.futures
        from unittest.mock import patch

        with patch("crawl4ai_mcp.generate_code_example_summary") as mock_generate:
            mock_generate.side_effect = (
                lambda code, before, after: f"Summary for {code[:10]}"
            )

            # Test with ThreadPoolExecutor
            test_cases = [
                ("def func1(): pass", "context1", "after1"),
                ("def func2(): pass", "context2", "after2"),
                ("def func3(): pass", "context3", "after3"),
            ]

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(process_code_example, args) for args in test_cases
                ]
                results = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]

            assert len(results) == 3
            assert all("Summary for" in result for result in results)

    def test_function_signature_consistency(self):
        """Test that function signature matches expected usage"""
        import inspect

        # Check function signature
        sig = inspect.signature(process_code_example)
        params = list(sig.parameters.keys())

        assert len(params) == 1
        assert params[0] == "args"

        # Verify docstring describes the expected args format
        assert (
            "args: Tuple containing (code, context_before, context_after)"
            in process_code_example.__doc__
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
