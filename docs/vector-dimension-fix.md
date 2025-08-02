# Vector Dimension Fix Documentation

## Issue Description

**Error**: `Wrong input: Vector dimension error: expected dim: 1536, got 384`

**Context**: This error occurred when the MCP server attempted to store embeddings in Qdrant during search operations.

## Root Cause Analysis

The Qdrant adapter was creating embeddings with inconsistent dimensions:

1. **Collections Configuration**: All Qdrant collections (CRAWLED_PAGES, CODE_EXAMPLES, SOURCES) were configured to use 1536-dimensional vectors, matching OpenAI's `text-embedding-3-small` model.

2. **Embedding Generation**: The system correctly uses OpenAI's API to generate 1536-dimensional embeddings for regular content.

3. **Bug Location**: In `src/database/qdrant_adapter.py`, when creating a new source that didn't exist, the code was generating a simple embedding from a SHA256 hash but only creating 384 dimensions.

## Technical Details

### Original Code (Buggy)
```python
# Convert first 384 bytes to floats between -1 and 1
embedding = [(b - 128) / 128.0 for b in hash_bytes[:384]]
# Pad to 384 dimensions if needed
while len(embedding) < 384:
    embedding.append(0.0)
```

**Problems**:
- SHA256 produces only 32 bytes, not 384
- The code was trying to access `hash_bytes[:384]` which would only get 32 values
- It was padding to 384 dimensions instead of the required 1536

### Fixed Code
```python
# Convert hash bytes to floats between -1 and 1
# Use all 32 bytes from SHA256 and repeat to get 1536 dimensions
base_embedding = [(b - 128) / 128.0 for b in hash_bytes]
# Repeat the pattern to fill 1536 dimensions
embedding = []
while len(embedding) < 1536:
    embedding.extend(base_embedding)
# Trim to exactly 1536 dimensions
embedding = embedding[:1536]
```

**Solution**:
- Uses all 32 bytes from SHA256 hash
- Converts each byte (0-255) to a float in range [-1, 1]
- Repeats the 32-value pattern to fill 1536 dimensions
- Ensures exactly 1536 dimensions by trimming any excess

## Implementation Notes

### Why This Approach?

1. **Deterministic**: The embedding is generated from the source_id hash, ensuring the same source always gets the same embedding.

2. **Dimension Compatibility**: Matches the 1536 dimensions used by OpenAI's text-embedding-3-small model.

3. **Placeholder Nature**: These are placeholder embeddings for source metadata, not semantic embeddings. They allow the source to be stored in the vector database without requiring actual content embedding.

### Mathematical Details

- **Input**: SHA256 hash (32 bytes)
- **Normalization**: `(byte_value - 128) / 128.0` maps [0, 255] to [-1, 1]
- **Repetition**: 1536 ÷ 32 = 48 repetitions (exactly)
- **Result**: 1536-dimensional vector with values in range [-1, 1]

## Testing

To verify the fix:

```python
import hashlib

def create_test_embedding(source_id: str) -> list:
    hash_object = hashlib.sha256(source_id.encode())
    hash_bytes = hash_object.digest()
    base_embedding = [(b - 128) / 128.0 for b in hash_bytes]
    embedding = []
    while len(embedding) < 1536:
        embedding.extend(base_embedding)
    embedding = embedding[:1536]
    return embedding

# Test
embedding = create_test_embedding("test-source-123")
assert len(embedding) == 1536
assert all(-1 <= v <= 1 for v in embedding)
```

## Impact

This fix ensures:
1. All embeddings stored in Qdrant have consistent 1536 dimensions
2. No more dimension mismatch errors during search operations
3. Source metadata can be properly stored and retrieved
4. The system maintains compatibility with OpenAI's embedding model

## Related Files

- `src/database/qdrant_adapter.py` - Contains the fix
- `src/utils.py` - Uses OpenAI API for regular embeddings (1536 dims)
- `src/database/base.py` - Defines the vector database interface

## Future Considerations

1. Consider using actual content-based embeddings for sources instead of hash-based placeholders
2. Add dimension validation before storing embeddings
3. Implement proper error handling for dimension mismatches
4. Consider making embedding dimensions configurable based on the model used