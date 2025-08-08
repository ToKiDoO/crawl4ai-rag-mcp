# Qdrant Point ID Fix Documentation

## Overview

This document describes the fix implemented for the Qdrant point ID error that occurred when storing sources with domain names as identifiers.

## Problem Description

When attempting to store crawled web content in Qdrant, the system would fail with the following error:

```
Format error in JSON body: value aider.chat is not a valid point ID, valid values are either an unsigned integer or a UUID
```

The issue occurred because the code was using URL domain names (e.g., "aider.chat") directly as Qdrant point IDs, but Qdrant only accepts:

- Unsigned integers
- Valid UUIDs

## Solution Implementation

### UUID Generation Strategy

The fix implements deterministic UUID generation using Python's `uuid.uuid5()` function with the DNS namespace. This ensures:

- Same source_id always maps to the same UUID (deterministic)
- Valid UUID format for Qdrant compatibility
- No collisions between different sources

### Code Changes

#### 1. Import Addition

```python
import uuid  # Added to support UUID generation
```

#### 2. Modified Methods in `qdrant_adapter.py`

**add_source() method:**

```python
# Generate a deterministic UUID from source_id
point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, source_id))

point = PointStruct(
    id=point_id,  # Use UUID instead of source_id
    vector=embedding,
    payload={
        "source_id": source_id,  # Store original ID in payload
        # ... other fields
    }
)
```

**update_source() method:**

```python
# Generate the same UUID for lookups
point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, source_id))

# Use UUID for retrieval
existing_points = await loop.run_in_executor(
    None,
    self.client.retrieve,
    self.SOURCES,
    [point_id]  # Use UUID instead of source_id
)
```

**update_source_info() method:**
Similar changes applied for both retrieval and creation of source points.

**get_sources() method:**

```python
# Extract source_id from payload instead of using point ID
"source_id": point.payload.get("source_id", point.id)
```

### UUID Mapping Examples

| Source ID | Generated UUID |
|-----------|----------------|
| aider.chat | df3dc4da-8788-5c00-ae80-a4b4f8264c0f |
| github.com | 6fca3dd2-d61d-58de-9363-1574b382ea68 |
| docs.python.org | bd7c3832-3a26-59e8-a0b9-9a01d6218c3b |

## Benefits

1. **Compatibility**: Fully compatible with Qdrant's ID requirements
2. **Deterministic**: Same source always generates the same UUID
3. **Backward Compatible**: Original source_id preserved in payload
4. **No Data Loss**: All existing functionality continues to work

## Testing

The fix was verified with a test script that:

1. Generated UUIDs for various domain formats
2. Validated UUID format compliance
3. Confirmed deterministic generation

## Impact

- All source storage operations now work correctly
- No changes required to calling code
- Existing source queries continue to function normally
