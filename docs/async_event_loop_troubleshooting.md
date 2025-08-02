# Async Event Loop Troubleshooting Guide

## Problem Summary

The integration tests in `test_integration.py` fail with:
```
RuntimeError: Runner.run() cannot be called from a running event loop
```

This occurs when using async generator fixtures (`async def` with `yield`) in pytest-asyncio.

## Root Cause

The issue stems from:
1. **Async generator fixtures** that use `yield` create event loop conflicts
2. **Parametrized fixtures** combined with async generators compound the problem
3. **pytest-asyncio** tries to manage event loops but conflicts with async generators

## Solutions

### Solution 1: Fixed Integration Tests (Recommended)

Use `test_integration_fixed.py` which:
- Replaces async generator fixtures with regular async methods
- Avoids the `yield` pattern in async fixtures
- Creates separate test methods for each database type

```python
# Instead of:
@pytest.fixture
async def qdrant_db(self):
    client = create_database_client()
    await client.initialize()
    yield client  # This causes the issue!

# Use:
async def create_qdrant_db(self):
    client = create_database_client()
    await client.initialize()
    return client
```

### Solution 2: Direct Runner Script

Use `scripts/test_integration_runner.py` for quick testing:
```bash
# Start Qdrant
docker compose -f docker-compose.test.yml up -d qdrant

# Run integration test
python scripts/test_integration_runner.py
```

### Solution 3: Update pytest Configuration

Add to `pytest.ini`:
```ini
[tool:pytest]
asyncio_mode = auto
# or
asyncio_mode = strict
```

### Solution 4: Use pytest-asyncio Fixtures Properly

For fixtures that need cleanup:
```python
@pytest_asyncio.fixture
async def database():
    db = await create_database()
    # No yield here!
    return db

# Cleanup in a separate fixture if needed
@pytest.fixture
def cleanup_database(database):
    yield
    # Cleanup code here
```

## Running the Fixed Tests

1. **Start test environment:**
   ```bash
   docker compose -f docker-compose.test.yml up -d
   ```

2. **Run fixed integration tests:**
   ```bash
   # Run all fixed tests
   pytest tests/test_integration_fixed.py -v

   # Run specific test
   pytest tests/test_integration_fixed.py::TestDatabaseIntegration::test_qdrant_document_operations -v
   ```

3. **Run simple integration test:**
   ```bash
   python scripts/test_integration_runner.py
   ```

## Alternative Testing Approaches

### 1. Use unittest.IsolatedAsyncioTestCase
```python
import unittest

class TestIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_something(self):
        # Your async test here
        pass
```

### 2. Manual Event Loop Management
```python
def test_with_manual_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(async_function())
        assert result == expected
    finally:
        loop.close()
```

### 3. Use Regular Fixtures with Context Managers
```python
@pytest.fixture
def database():
    async def _create():
        db = create_database_client()
        await db.initialize()
        return db
    
    loop = asyncio.new_event_loop()
    db = loop.run_until_complete(_create())
    yield db
    loop.close()
```

## Debugging Tips

1. **Check event loop state:**
   ```python
   import asyncio
   try:
       loop = asyncio.get_running_loop()
       print(f"Loop is running: {loop.is_running()}")
   except RuntimeError:
       print("No event loop running")
   ```

2. **Use pytest verbose mode:**
   ```bash
   pytest -vvv tests/test_integration.py
   ```

3. **Enable asyncio debug mode:**
   ```python
   import asyncio
   asyncio.set_debug(True)
   ```

## Best Practices

1. **Avoid async generators in fixtures** - Use regular async functions
2. **Keep fixtures simple** - Complex async fixtures often cause issues
3. **Use context managers** for resource cleanup
4. **Test in isolation** - Use separate test files for different scenarios
5. **Consider sync fixtures** with async context managers for complex cases

## References

- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [Python asyncio testing guide](https://docs.python.org/3/library/asyncio-dev.html#debug-mode)
- [FastAPI testing patterns](https://fastapi.tiangolo.com/tutorial/testing/) (similar async patterns)