# PyCharm/IntelliJ IDEA Setup Guide

This directory contains configuration templates for PyCharm Professional and IntelliJ IDEA with Python plugin.

## Quick Setup

1. **Open Project**: Open the project root directory in PyCharm
2. **Python Interpreter**: Configure UV-managed virtual environment
   - File → Settings → Project → Python Interpreter
   - Add Interpreter → System Interpreter
   - Select: `./venv/bin/python` (created by `uv sync`)

3. **Environment Variables**: Configure `.env` file loading
   - Run/Debug Configurations → Templates → Python
   - Environment Variables → Load from file: `.env`

## Essential Configurations

### 1. Code Style and Formatting

Configure Ruff integration:

- Install "Ruff" plugin from marketplace
- File → Settings → Tools → Ruff
  - Enable: "Use ruff"  
  - Executable: `uv run ruff`
  - Configuration file: `pyproject.toml`

### 2. Testing Configuration

Configure pytest:

- File → Settings → Tools → Python Integrated Tools
  - Default test runner: pytest
  - pytest arguments: `-v --tb=short`

### 3. Docker Integration

Enable Docker plugin:

- File → Settings → Plugins → Docker (enable if not already)
- File → Settings → Build, Execution, Deployment → Docker
  - Add Docker server (usually auto-detected)

### 4. Database Tools

Configure database connections:

- View → Tool Windows → Database
- Add data sources:
  - Neo4j: `bolt://localhost:7687` (neo4j/testpassword123)
  - Add Qdrant HTTP connection: `http://localhost:6333`

## Run Configurations

Create these run configurations for common tasks:

### MCP Server (stdio)

- Type: Python
- Script path: `src/crawl4ai_mcp.py`
- Environment variables: Load from `.env`
- Working directory: Project root

### MCP Server (HTTP)

- Type: Python
- Script path: `src/crawl4ai_mcp.py`
- Environment variables: Load from `.env` + `MCP_TRANSPORT=http`
- Working directory: Project root

### Unit Tests

- Type: pytest
- Target: `tests/`
- Additional arguments: `-m "not integration"`

### Integration Tests  

- Type: pytest
- Target: `tests/`
- Additional arguments: `-m integration`
- Before launch: Run external tool → `make docker-test-up-wait`

### Docker Development Environment

- Type: Shell Script
- Script text: `make dev-bg`
- Working directory: Project root

## File Templates

Create file templates for common patterns:

### MCP Tool Template

```python
@mcp.tool()
async def ${NAME}(${PARAMS}) -> str:
    """${DESCRIPTION}"""
    try:
        # Implementation
        return "Success"
    except Exception as e:
        logger.error(f"Error in ${NAME}: {e}")
        raise MCPToolError(f"${NAME} failed: {e}")
```

### Test Template

```python
import pytest
from unittest.mock import Mock, patch

@pytest.mark.unit
async def test_${NAME}():
    """Test ${DESCRIPTION}"""
    # Arrange
    
    # Act
    
    # Assert
    assert True
```

## Useful Plugins

Install these plugins for enhanced development:

### Essential

- **Ruff**: Python linting and formatting
- **Docker**: Container management
- **Makefile**: Makefile support
- **.env files support**: Environment file syntax

### Recommended  

- **Rainbow Brackets**: Visual bracket matching
- **GitToolBox**: Enhanced Git integration
- **Python Security**: Security scanning
- **Requirements**: Dependencies management
- **String Manipulation**: Text utilities

## Debugging Setup

### MCP Server Debugging

1. Add debugger entry point in code:

   ```python
   import debugpy
   debugpy.listen(5678)
   debugpy.wait_for_client()
   ```

2. Create "Python Debug Server" run configuration:
   - Port: 5678
   - IDE host name: localhost

3. Start MCP server, then attach debugger

### Docker Debugging

1. Modify Dockerfile to expose debug port:

   ```dockerfile
   EXPOSE 5678
   ```

2. Run container with port mapping:

   ```bash
   docker run -p 5678:5678 your-image
   ```

3. Use "Python Debug Server" configuration to attach

## Keyboard Shortcuts

Set up productive shortcuts:

- **Run Tests**: `Ctrl+Shift+T`
- **Debug Tests**: `Ctrl+Shift+D`  
- **Format Code**: `Ctrl+Alt+L`
- **Run MCP Server**: `Shift+F10`
- **Docker Compose Up**: Custom (`Ctrl+Alt+D`)
- **View Logs**: Custom (`Ctrl+Alt+L`)

## Project Structure Navigation

Configure scope filters:

- **Source Code**: `src/`, `tests/`
- **Configuration**: `*.yml`, `*.yaml`, `*.toml`, `*.env*`
- **Docker**: `Dockerfile*`, `docker-compose*.yml`
- **Documentation**: `*.md`, `docs/`

## Tips and Tricks

### Performance Optimization

- Exclude directories from indexing:
  - `__pycache__`, `.pytest_cache`, `htmlcov`
  - `logs/`, `data/`, `.ruff_cache`
  - Docker volumes and build contexts

### Code Navigation

- Use "Recent Files" (`Ctrl+E`) for quick switching
- Bookmark important files (`F11`)
- Use "Find Action" (`Ctrl+Shift+A`) for commands

### Version Control

- Enable "Show Diff Preview in Editor"
- Configure "On Commit" actions:
  - Reformat code
  - Rearrange code
  - Run Ruff

### Testing Workflow

- Use "Run with Coverage" for test analysis
- Enable "Auto-test" mode for continuous testing
- Configure test output format for clarity

## Troubleshooting

### Common Issues

**Python Interpreter Not Found:**

- Run `uv sync` to create virtual environment
- Refresh interpreter list in settings
- Manually point to `./venv/bin/python`

**Tests Not Discovered:**

- Check pytest configuration in settings
- Verify test file naming (`test_*.py`)
- Check `PYTHONPATH` includes `src/`

**Docker Integration Issues:**

- Verify Docker daemon is running
- Check Docker plugin is enabled
- Refresh Docker service configuration

**Environment Variables Not Loaded:**

- Verify `.env` file exists and is readable
- Check run configuration settings
- Use absolute path to `.env` file if needed

### Getting Help

- PyCharm Documentation: <https://www.jetbrains.com/help/pycharm/>
- Docker Plugin Docs: <https://www.jetbrains.com/help/pycharm/docker.html>
- Python Development: <https://www.jetbrains.com/help/pycharm/python.html>
