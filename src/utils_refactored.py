"""
Refactored utility functions that work with the database abstraction layer.
These functions are database-agnostic and work with any VectorDatabase implementation.
"""
import os
import sys
import concurrent.futures
from typing import List, Dict, Any, Optional, Tuple
import json
from urllib.parse import urlparse
import openai
import re
import time
from database.base import VectorDatabase

# Load OpenAI API key for embeddings
openai.api_key = os.getenv("OPENAI_API_KEY")


def create_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Create embeddings for multiple texts in a single API call.
    
    Args:
        texts: List of texts to create embeddings for
        
    Returns:
        List of embeddings (each embedding is a list of floats)
    """
    if not texts:
        return []
    
    max_retries = 3
    retry_delay = 1.0  # Start with 1 second delay
    
    for retry in range(max_retries):
        try:
            response = openai.embeddings.create(
                model="text-embedding-3-small", # Hardcoding embedding model for now, will change this later to be more dynamic
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            if retry < max_retries - 1:
                print(f"Error creating batch embeddings (attempt {retry + 1}/{max_retries}, file=sys.stderr): {e}")
                print(f"Retrying in {retry_delay} seconds...", file=sys.stderr)
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"Failed to create batch embeddings after {max_retries} attempts: {e}", file=sys.stderr)
                # Try creating embeddings one by one as fallback
                print("Attempting to create embeddings individually...", file=sys.stderr)
                embeddings = []
                successful_count = 0
                
                for i, text in enumerate(texts):
                    try:
                        individual_response = openai.embeddings.create(
                            model="text-embedding-3-small",
                            input=[text]
                        )
                        embeddings.append(individual_response.data[0].embedding)
                        successful_count += 1
                    except Exception as individual_error:
                        print(f"Failed to create embedding for text {i}: {individual_error}", file=sys.stderr)
                        # Add zero embedding as fallback
                        embeddings.append([0.0] * 1536)
                
                print(f"Successfully created {successful_count}/{len(texts)} embeddings individually", file=sys.stderr)
                return embeddings


def create_embedding(text: str) -> List[float]:
    """
    Create an embedding for a single text using OpenAI's API.
    
    Args:
        text: Text to create an embedding for
        
    Returns:
        List of floats representing the embedding
    """
    try:
        embeddings = create_embeddings_batch([text])
        return embeddings[0] if embeddings else [0.0] * 1536
    except Exception as e:
        print(f"Error creating embedding: {e}", file=sys.stderr)
        # Return empty embedding if there's an error
        return [0.0] * 1536


def generate_contextual_embedding(full_document: str, chunk: str) -> Tuple[str, bool]:
    """
    Generate contextual information for a chunk within a document to improve retrieval.
    
    Args:
        full_document: The complete document text
        chunk: The specific chunk of text to generate context for
        
    Returns:
        Tuple containing:
        - The contextual text that situates the chunk within the document
        - Boolean indicating if contextual embedding was performed
    """
    model_choice = os.getenv("MODEL_CHOICE")
    
    try:
        # Create the prompt for generating contextual information
        prompt = f"""<document> 
{full_document[:25000]} 
</document>
Here is the chunk we want to situate within the whole document 
<chunk> 
{chunk}
</chunk> 
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""

        # Call the OpenAI API to generate contextual information
        response = openai.chat.completions.create(
            model=model_choice,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise contextual information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        # Extract the generated context
        context = response.choices[0].message.content.strip()
        
        # Combine the context with the original chunk
        contextual_text = f"{context}\n---\n{chunk}"
        
        return contextual_text, True
    
    except Exception as e:
        print(f"Error generating contextual embedding: {e}. Using original chunk instead.", file=sys.stderr)
        return chunk, False


def process_chunk_with_context(args):
    """
    Process a single chunk with contextual embedding.
    This function is designed to be used with concurrent.futures.
    
    Args:
        args: Tuple containing (url, content, full_document)
        
    Returns:
        Tuple containing:
        - The contextual text that situates the chunk within the document
        - Boolean indicating if contextual embedding was performed
    """
    url, content, full_document = args
    return generate_contextual_embedding(full_document, content)


async def add_documents_to_database(
    database: VectorDatabase,
    urls: List[str], 
    chunk_numbers: List[int],
    contents: List[str], 
    metadatas: List[Dict[str, Any]],
    url_to_full_document: Dict[str, str],
    batch_size: int = 20
) -> None:
    """
    Add documents to the database with optional contextual embeddings.
    This is a database-agnostic wrapper around the database adapter.
    
    Args:
        database: VectorDatabase instance
        urls: List of URLs
        chunk_numbers: List of chunk numbers
        contents: List of document contents
        metadatas: List of document metadata
        url_to_full_document: Dictionary mapping URLs to their full document content
        batch_size: Size of each batch for insertion
    """
    # Check if we should use contextual embeddings
    use_contextual_embeddings = os.getenv("USE_CONTEXTUAL_EMBEDDINGS", "false") == "true"
    print(f"\n\nUse contextual embeddings: {use_contextual_embeddings}\n\n", file=sys.stderr)
    
    # Process all contents to potentially add context
    if use_contextual_embeddings:
        contextual_contents = []
        
        # Prepare arguments for parallel processing
        process_args = []
        for i, content in enumerate(contents):
            url = urls[i]
            full_document = url_to_full_document.get(url, "")
            process_args.append((url, content, full_document))
        
        # Process in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_idx = {executor.submit(process_chunk_with_context, arg): idx 
                            for idx, arg in enumerate(process_args)}
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    result, success = future.result()
                    contextual_contents.append(result)
                    if success:
                        metadatas[idx]["contextual_embedding"] = True
                except Exception as e:
                    print(f"Error processing chunk {idx}: {e}", file=sys.stderr)
                    contextual_contents.append(contents[idx])
        
        # Sort results back into original order
        if len(contextual_contents) != len(contents):
            print(f"Warning: Expected {len(contents)} results but got {len(contextual_contents)}", file=sys.stderr)
            contextual_contents = contents
    else:
        contextual_contents = contents
    
    # Create embeddings for all contents
    all_embeddings = []
    for i in range(0, len(contextual_contents), batch_size):
        batch_end = min(i + batch_size, len(contextual_contents))
        batch_texts = contextual_contents[i:batch_end]
        batch_embeddings = create_embeddings_batch(batch_texts)
        all_embeddings.extend(batch_embeddings)
    
    # Extract source IDs
    source_ids = []
    for url in urls:
        parsed_url = urlparse(url)
        source_id = parsed_url.netloc or parsed_url.path
        source_ids.append(source_id)
    
    # Add to database
    await database.add_documents(
        urls=urls,
        chunk_numbers=chunk_numbers,
        contents=contextual_contents,  # Use potentially contextualized content
        metadatas=metadatas,
        embeddings=all_embeddings,
        source_ids=source_ids
    )


async def search_documents(
    database: VectorDatabase,
    query: str, 
    match_count: int = 10, 
    filter_metadata: Optional[Dict[str, Any]] = None,
    source_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for documents using vector similarity.
    
    Args:
        database: VectorDatabase instance
        query: Query text
        match_count: Maximum number of results to return
        filter_metadata: Optional metadata filter
        source_filter: Optional source filter
        
    Returns:
        List of matching documents
    """
    # Create embedding for the query
    query_embedding = create_embedding(query)
    
    # Execute search using the database adapter
    return await database.search_documents(
        query_embedding=query_embedding,
        match_count=match_count,
        metadata_filter=filter_metadata,
        source_filter=source_filter
    )


def extract_code_blocks(markdown_content: str, min_length: int = 1000) -> List[Dict[str, Any]]:
    """
    Extract code blocks from markdown content along with context.
    
    Args:
        markdown_content: The markdown content to extract code blocks from
        min_length: Minimum length of code blocks to extract (default: 1000 characters)
        
    Returns:
        List of dictionaries containing code blocks and their context
    """
    code_blocks = []
    
    # Skip if content starts with triple backticks (edge case for files wrapped in backticks)
    # Find all occurrences of triple backticks
    backtick_positions = []
    pos = 0
    while True:
        pos = markdown_content.find('```', pos)
        if pos == -1:
            break
        backtick_positions.append(pos)
        pos += 3
    
    # Process pairs of backticks
    i = 0
    while i < len(backtick_positions) - 1:
        start_pos = backtick_positions[i]
        end_pos = backtick_positions[i + 1]
        
        # Extract the content between backticks
        code_section = markdown_content[start_pos+3:end_pos]
        
        # Check if there's a language specifier on the first line
        lines = code_section.split('\n', 1)
        if len(lines) > 1:
            # Check if first line is a language specifier (no spaces, common language names)
            first_line = lines[0].strip()
            if first_line and not ' ' in first_line and len(first_line) < 20:
                language = first_line
                code_content = lines[1] if len(lines) > 1 else ""
            else:
                language = ""
                code_content = code_section
        else:
            language = ""
            code_content = code_section
        
        # Skip if code block is too short
        if len(code_content) < min_length:
            i += 2  # Move to next pair
            continue
        
        # Extract context before (1000 chars)
        context_start = max(0, start_pos - 1000)
        context_before = markdown_content[context_start:start_pos].strip()
        
        # Extract context after (1000 chars)
        context_end = min(len(markdown_content), end_pos + 3 + 1000)
        context_after = markdown_content[end_pos + 3:context_end].strip()
        
        code_blocks.append({
            'code': code_content,
            'language': language,
            'context_before': context_before,
            'context_after': context_after,
            'full_context': f"{context_before}\n\n{code_content}\n\n{context_after}"
        })
        
        # Move to next pair (skip the closing backtick we just processed)
        i += 2
    
    return code_blocks


def generate_code_example_summary(code: str, context_before: str, context_after: str) -> str:
    """
    Generate a summary for a code example using its surrounding context.
    
    Args:
        code: The code example
        context_before: Context before the code
        context_after: Context after the code
        
    Returns:
        A summary of what the code example demonstrates
    """
    model_choice = os.getenv("MODEL_CHOICE")
    
    # Create the prompt
    prompt = f"""<context_before>
{context_before[-500:] if len(context_before) > 500 else context_before}
</context_before>

<code_example>
{code[:1500] if len(code) > 1500 else code}
</code_example>

<context_after>
{context_after[:500] if len(context_after) > 500 else context_after}
</context_after>

Based on the code example and its surrounding context, provide a concise summary (2-3 sentences) that describes what this code example demonstrates and its purpose. Focus on the practical application and key concepts illustrated.
"""
    
    try:
        response = openai.chat.completions.create(
            model=model_choice,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise code example summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"Error generating code example summary: {e}", file=sys.stderr)
        return "Code example for demonstration purposes."


async def add_code_examples_to_database(
    database: VectorDatabase,
    urls: List[str],
    chunk_numbers: List[int],
    code_examples: List[str],
    summaries: List[str],
    metadatas: List[Dict[str, Any]],
    batch_size: int = 20
):
    """
    Add code examples to the database.
    
    Args:
        database: VectorDatabase instance
        urls: List of URLs
        chunk_numbers: List of chunk numbers
        code_examples: List of code example contents
        summaries: List of code example summaries
        metadatas: List of metadata dictionaries
        batch_size: Size of each batch for insertion
    """
    if not urls:
        return
    
    # Create embeddings for code examples (combine code + summary for better search)
    all_embeddings = []
    for i in range(0, len(code_examples), batch_size):
        batch_end = min(i + batch_size, len(code_examples))
        batch_texts = []
        
        # Create combined texts for embedding
        for j in range(i, batch_end):
            combined_text = f"{code_examples[j]}\n\nSummary: {summaries[j]}"
            batch_texts.append(combined_text)
        
        batch_embeddings = create_embeddings_batch(batch_texts)
        all_embeddings.extend(batch_embeddings)
    
    # Extract source IDs
    source_ids = []
    for url in urls:
        parsed_url = urlparse(url)
        source_id = parsed_url.netloc or parsed_url.path
        source_ids.append(source_id)
    
    # Add to database
    await database.add_code_examples(
        urls=urls,
        chunk_numbers=chunk_numbers,
        code_examples=code_examples,
        summaries=summaries,
        metadatas=metadatas,
        embeddings=all_embeddings,
        source_ids=source_ids
    )


def extract_source_summary(source_id: str, content: str, max_length: int = 500) -> str:
    """
    Extract a summary for a source from its content using an LLM.
    
    This function uses the OpenAI API to generate a concise summary of the source content.
    
    Args:
        source_id: The source ID (domain)
        content: The content to extract a summary from
        max_length: Maximum length of the summary
        
    Returns:
        A summary string
    """
    # Default summary if we can't extract anything meaningful
    default_summary = f"Content from {source_id}"
    
    if not content or len(content.strip()) == 0:
        return default_summary
    
    # Get the model choice from environment variables
    model_choice = os.getenv("MODEL_CHOICE")
    
    # Limit content length to avoid token limits
    truncated_content = content[:25000] if len(content) > 25000 else content
    
    # Create the prompt for generating the summary
    prompt = f"""<source_content>
{truncated_content}
</source_content>

The above content is from the documentation for '{source_id}'. Please provide a concise summary (3-5 sentences) that describes what this library/tool/framework is about. The summary should help understand what the library/tool/framework accomplishes and the purpose.
"""
    
    try:
        # Call the OpenAI API to generate the summary
        response = openai.chat.completions.create(
            model=model_choice,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise library/tool/framework summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        # Extract the generated summary
        summary = response.choices[0].message.content.strip()
        
        # Ensure the summary is not too long
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
            
        return summary
    
    except Exception as e:
        print(f"Error generating summary with LLM for {source_id}: {e}. Using default summary.", file=sys.stderr)
        return default_summary


async def search_code_examples(
    database: VectorDatabase,
    query: str, 
    match_count: int = 10, 
    filter_metadata: Optional[Dict[str, Any]] = None,
    source_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for code examples using vector similarity.
    
    Args:
        database: VectorDatabase instance
        query: Query text
        match_count: Maximum number of results to return
        filter_metadata: Optional metadata filter
        source_filter: Optional source filter
        
    Returns:
        List of matching code examples
    """
    # Create a more descriptive query for better embedding match
    enhanced_query = f"Code example for {query}\n\nSummary: Example code showing {query}"
    
    # Create embedding for the enhanced query
    query_embedding = create_embedding(enhanced_query)
    
    # Execute search using the database adapter
    return await database.search_code_examples(
        query_embedding=query_embedding,
        match_count=match_count,
        filter_metadata=filter_metadata,
        source_filter=source_filter
    )