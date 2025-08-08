# IDE Setup Guide for Crawl4AI MCP

This guide provides comprehensive setup instructions for developing the Crawl4AI MCP project in your preferred IDE, focusing on productivity and developer experience optimization.

## Table of Contents

- [Quick Start](#quick-start)
- [VS Code Setup](#vs-code-setup)
- [PyCharm/IntelliJ Setup](#pycharmintellij-setup)
- [Debugging MCP Servers](#debugging-mcp-servers)
- [Testing Configuration](#testing-configuration)
- [Docker Integration](#docker-integration)
- [Productivity Tips](#productivity-tips)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

1. **Install UV** (Python package manager):

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Dependencies**:

   ```bash
   uv sync
   ```

3. **Setup Environment**:

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start Development Environment**:

   ```bash
   make dev-bg  # Start services in background
   ```

## VS Code Setup

VS Code configuration files are provided in `.vscode/` directory.

### Installation and Configuration

1. **Install VS Code**: Download from [code.visualstudio.com](https://code.visualstudio.com/)

2. **Open Project**:

   ```bash
   code /path/to/crawl4ai-mcp
   ```

3. **Install Recommended Extensions**: VS Code will prompt to install extensions listed in `.vscode/extensions.json`

### Key Features Configured

#### Python Development

- **Interpreter**: Automatically detects UV-managed virtual environment
- **Formatting**: Ruff formatter with format-on-save
- **Linting**: Ruff linter with real-time feedback
- **Type Checking**: Basic type checking enabled
- **Testing**: Pytest integration with test discovery

#### Code Quality

- **Format on Save**: Automatically formats Python code
- **Import Organization**: Sorts and organizes imports
- **Line Length**: 88 characters (Black/Ruff compatible)
- **Error Highlighting**: Real-time error and warning display

#### Environment Integration

- **Environment Variables**: Automatically loads `.env` file
- **Docker Support**: Docker containers and compose files
- **Git Integration**: Enhanced Git features with GitLens

### Essential Extensions

The following extensions are automatically recommended:

#### Core Python Development

- `ms-python.python` - Python language support
- `charliermarsh.ruff` - Fast Python linting and formatting
- `ms-python.pytest` - Pytest test framework integration

#### Testing and Quality

- `ryanluker.vscode-coverage-gutters` - Test coverage visualization
- `usernamehw.errorlens` - Inline error display
- `sonarsource.sonarlint-vscode` - Code quality analysis

#### Docker and DevOps

- `ms-azuretools.vscode-docker` - Docker containers support
- `ms-vscode-remote.remote-containers` - Development containers

#### Productivity

- `eamodio.gitlens` - Enhanced Git capabilities
- `christian-kohler.path-intellisense` - File path completion
- `yzhang.markdown-all-in-one` - Markdown support

### Debug Configurations

Pre-configured debug sessions available via `F5`:

1. **Run MCP Server (stdio)** - Debug MCP server in stdio mode
2. **Run MCP Server (HTTP)** - Debug MCP server in HTTP mode  
3. **Debug Current Test File** - Debug the currently open test file
4. **Debug All Unit Tests** - Debug all unit tests
5. **Debug Integration Tests** - Debug integration tests with services
6. **Debug with Coverage** - Run tests with coverage analysis

### Task Automation

Pre-configured tasks available via `Ctrl+Shift+P > Tasks: Run Task`:

#### Development Tasks

- **Start Development Environment** - `make dev-bg`
- **Stop Development Environment** - `make dev-down`
- **View Development Logs** - `make dev-logs`

#### Testing Tasks  

- **Run Unit Tests** - `make test-unit`
- **Run Integration Tests** - `make test-integration`
- **Run All Tests** - `make test-all`
- **Run Tests with Coverage** - `make test-coverage`

#### Code Quality Tasks

- **Format Code** - `make format`
- **Lint Code** - `make lint`
- **Type Check** - `make type-check`
- **Validate All** - Run all validation checks

### Keyboard Shortcuts

| Action | Shortcut | Description |
|--------|----------|-------------|
| Run Tests | `Ctrl+Shift+T` | Run unit tests |
| Debug | `F5` | Start debugging |
| Format Document | `Shift+Alt+F` | Format current file |
| Command Palette | `Ctrl+Shift+P` | Access all commands |
| Quick Open | `Ctrl+P` | Open files quickly |
| Toggle Terminal | `Ctrl+`` | Show/hide terminal |

## PyCharm/IntelliJ Setup

Detailed configuration guide available in `.idea/README.md`.

### Quick Setup Steps

1. **Open Project**: File → Open → Select project root directory

2. **Configure Python Interpreter**:
   - File → Settings → Project → Python Interpreter
   - Add Interpreter → System Interpreter → `./venv/bin/python`

3. **Install Ruff Plugin**: File → Settings → Plugins → Search "Ruff" → Install

4. **Configure Environment Variables**:
   - Run/Debug Configurations → Templates → Python
   - Environment Variables → Load from file: `.env`

### Key Features

#### Code Intelligence

- **Advanced Refactoring**: Intelligent code transformations
- **Code Inspection**: Real-time code analysis
- **Smart Navigation**: Jump to definitions and usages
- **Database Tools**: Built-in database browser and query tools

#### Testing Integration  

- **Visual Test Runner**: Graphical test execution and results
- **Coverage Analysis**: Detailed coverage reports with visualization
- **Test Generation**: Automatic test template creation
- **Debugging**: Advanced debugging with variable inspection

#### Professional Features (PyCharm Pro)

- **Docker Integration**: Full Docker and Docker Compose support
- **Database Tools**: Connect to Neo4j and other databases
- **HTTP Client**: Built-in REST client for API testing
- **Profiling**: Python profiler integration

## Debugging MCP Servers

MCP servers can be challenging to debug due to their communication protocol. Here are effective strategies:

### Method 1: Direct Python Debugging

1. **Run Server Directly**:

   ```bash
   uv run python src/crawl4ai_mcp.py
   ```

2. **Set Breakpoints**: Use your IDE's debugger normally

3. **Test with MCP Client**:

   ```bash
   # In another terminal
   uv run python test_mcp_client.py
   ```

### Method 2: HTTP Mode Debugging

1. **Start Server in HTTP Mode**:

   ```bash
   MCP_TRANSPORT=http MCP_PORT=8000 uv run python src/crawl4ai_mcp.py
   ```

2. **Test HTTP Endpoints**:

   ```bash
   curl -X POST http://localhost:8000/mcp/v1/tools/crawl_url \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.org"}'
   ```

### Method 3: Docker Debugging

1. **Enable Debug Mode**: Set `MCP_DEBUG=true` in `.env`

2. **View Logs**:

   ```bash
   make dev-logs  # Follow MCP server logs
   ```

3. **Attach Debugger**: Use VS Code's "Attach to Docker" configuration

### Debugging Best Practices

#### Logging Strategy

```python
import logging
logger = logging.getLogger('crawl4ai-mcp')

# Use structured logging
logger.info("Processing request", extra={
    "tool": "crawl_url",
    "url": url,
    "request_id": request_id
})
```

#### Error Handling

```python
@mcp.tool()
async def my_tool(param: str) -> str:
    try:
        # Tool implementation
        return result
    except Exception as e:
        logger.error(f"Tool failed: {e}", exc_info=True)
        raise MCPToolError(f"Operation failed: {e}")
```

#### Testing Tools Individually

```python
# Test individual tool functions
async def test_tool():
    result = await crawl_url("https://example.org")
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_tool())
```

## Testing Configuration

### Test Structure

```
tests/
├── unit/                    # Unit tests (no external dependencies)
├── integration/            # Integration tests (require Docker services)
├── fixtures/              # Test data and fixtures
├── conftest.py           # Pytest configuration
└── test_*.py            # Individual test modules
```

### Test Markers

Use pytest markers to categorize tests:

```python
@pytest.mark.unit           # Unit test (fast, no dependencies)
@pytest.mark.integration    # Integration test (slower, requires services)
@pytest.mark.slow          # Slow-running tests
@pytest.mark.network       # Requires network access
@pytest.mark.docker        # Requires Docker services
```

### Running Tests

#### VS Code

- **Current File**: Right-click → "Run Python Tests in File"
- **All Tests**: Test Explorer panel → Run All
- **With Coverage**: Task → "Run Tests with Coverage"

#### PyCharm

- **Right-click Test**: Right-click test function/class → Run
- **Coverage**: Run → Run with Coverage
- **Debug**: Right-click → Debug

#### Command Line

```bash
# Unit tests only (fast)
make test-unit

# Integration tests (requires Docker services)
make test-integration

# All tests
make test-all

# With coverage
make test-coverage

# Specific test file
make test-file FILE=tests/test_utils.py

# Tests with specific marker
make test-mark MARK=unit
```

### Test Environment Setup

Tests use separate environment configuration:

1. **Copy Test Environment**:

   ```bash
   cp .env.example .env.test
   # Configure test-specific settings
   ```

2. **Start Test Services**:

   ```bash
   make docker-test-up-wait
   ```

3. **Run Tests**:

   ```bash
   make test-integration
   ```

4. **Cleanup**:

   ```bash
   make docker-test-down
   ```

## Docker Integration

### Development Environment

The project uses Docker Compose for development:

```bash
# Start all services in background
make dev-bg

# Start with watch mode (auto-restart on changes)
make dev

# View logs
make dev-logs

# Stop services
make dev-down
```

### Service Architecture

```
┌─────────────┐    ┌─────────────┐
│ MCP Server  │    │   SearXNG   │
│   (Python)  │────│  (Search)   │
└─────────────┘    └─────────────┘
       │                   │
   ┌───▼───┐           ┌───▼───┐
   │ Valkey│           │ Qdrant│
   │(Cache)│           │(Vector)│
   └───────┘           └───────┘
       │                   │
   ┌───▼──────────────────▼───┐
   │       Neo4j Graph       │
   │    (Knowledge Graph)    │
   └─────────────────────────┘
```

### Service Endpoints

- **MCP Server**: stdio mode (default)
- **SearXNG**: <http://localhost:8080>
- **Qdrant Dashboard**: <http://localhost:6333/dashboard>
- **Neo4j Browser**: <http://localhost:7474>
- **Valkey**: localhost:6379

### Docker Development Tips

#### Live Reloading

Docker Compose watch mode automatically restarts the MCP server when code changes:

```bash
make dev  # Enables watch mode
```

#### Service Health Checks

```bash
make health  # Check all services
make docker-test-status  # Check test services
```

#### Volume Mounts

- **Source Code**: `./src:/app/src` (live reload)
- **Data**: `./data:/app/data` (persistent data)
- **Logs**: `./logs:/app/logs` (log files)

#### Environment Variables

- **Development**: `.env` file
- **Testing**: `.env.test` file  
- **Production**: Set in deployment environment

## Productivity Tips

### VS Code Tips

#### Multi-cursor Editing

- `Ctrl+D` - Select next occurrence
- `Ctrl+Shift+L` - Select all occurrences
- `Alt+Click` - Add cursor at position

#### Code Navigation

- `Ctrl+Shift+O` - Go to symbol in file
- `Ctrl+T` - Go to symbol in workspace
- `F12` - Go to definition
- `Shift+F12` - Find all references

#### Integrated Terminal

- `Ctrl+`` - Toggle terminal
- `Ctrl+Shift+`` - New terminal
- `Ctrl+Shift+C` - Copy to clipboard from terminal

#### Git Integration

- `Ctrl+Shift+G` - Open source control
- `Ctrl+K Ctrl+C` - Commit changes
- `Ctrl+Shift+P` → "Git: Pull" - Pull changes

### PyCharm Tips

#### Smart Navigation

- `Ctrl+N` - Go to class
- `Ctrl+Shift+N` - Go to file
- `Ctrl+Alt+Shift+N` - Go to symbol
- `Ctrl+B` - Go to declaration

#### Code Generation

- `Alt+Insert` - Generate code (tests, getters, etc.)
- `Ctrl+Alt+T` - Surround with template
- `Ctrl+D` - Duplicate line/selection

#### Refactoring

- `Shift+F6` - Rename
- `Ctrl+Alt+M` - Extract method
- `Ctrl+Alt+V` - Extract variable
- `F6` - Move class/method

### General Productivity

#### Environment Management

```bash
# Quick environment setup
make deps              # Install dependencies
make env-check        # Validate environment
make clean            # Clean artifacts
```

#### Testing Workflow

```bash
# Quick test cycle
make test-quick       # Fast unit tests
make test-file FILE=tests/test_specific.py
make test-watch       # Continuous testing
```

#### Code Quality

```bash
# Quality checks
make format          # Format code
make lint           # Check code quality  
make type-check     # Type checking
make validate       # All checks
```

#### Development Cycle

```bash
# Full development cycle
make dev-bg         # Start services
# ... develop and test ...
make validate       # Check quality
make test-all       # Full test suite
make dev-down       # Stop services
```

## Troubleshooting

### Common Issues

#### Python Interpreter Not Found

**Symptoms**: IDE can't find Python interpreter or imports fail

**Solutions**:

1. Run `uv sync` to create virtual environment
2. Point IDE to `./venv/bin/python`
3. Add `src/` to Python path in IDE settings
4. Restart IDE after configuration changes

#### Tests Not Running

**Symptoms**: Test discovery fails or tests don't execute

**Solutions**:

1. Verify pytest is configured as test runner
2. Check test file naming follows `test_*.py` pattern
3. Ensure `PYTHONPATH` includes `src/` directory
4. Copy `.env.test` to `.env` for test environment

#### Docker Services Won't Start

**Symptoms**: `make dev` fails or services show as unhealthy

**Solutions**:

1. Check Docker daemon is running: `docker info`
2. Free up ports: `docker compose down` then retry
3. Rebuild images: `make build-no-cache`
4. Check logs: `docker compose logs [service-name]`

#### MCP Server Connection Issues

**Symptoms**: MCP client can't connect to server

**Solutions**:

1. Check server is running: `ps aux | grep crawl4ai_mcp`
2. Verify stdio mode: MCP servers use stdin/stdout by default
3. Check environment variables in `.env` file
4. Enable debug mode: `MCP_DEBUG=true`
5. Test with HTTP mode: `MCP_TRANSPORT=http`

#### Import Errors

**Symptoms**: Module import failures in tests or development

**Solutions**:

1. Verify virtual environment activation
2. Check `PYTHONPATH` includes `src/`
3. Install in development mode: `uv pip install -e .`
4. Restart language server in IDE

#### Performance Issues

**Symptoms**: Slow IDE response, high CPU usage

**Solutions**:

1. Exclude cache directories from indexing:
   - `__pycache__`, `.pytest_cache`, `.ruff_cache`
   - `htmlcov`, `logs`, `data`
2. Disable unnecessary extensions/plugins
3. Increase IDE memory allocation
4. Use project-specific settings instead of global

### Getting Help

#### Documentation

- **MCP Protocol**: [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- **FastMCP**: [FastMCP GitHub Repository](https://github.com/jlowin/fastmcp)
- **Crawl4AI**: [Crawl4AI Documentation](https://crawl4ai.com/)

#### Project Resources

- **README.md**: Project overview and quick start
- **CONTRIBUTING.md**: Contribution guidelines
- **Makefile**: Available development commands
- **pyproject.toml**: Project configuration and dependencies

#### IDE-Specific Help

- **VS Code**: <https://code.visualstudio.com/docs/python/python-tutorial>
- **PyCharm**: <https://www.jetbrains.com/help/pycharm/>

#### Community Support

- **Issues**: Report bugs and request features on GitHub
- **Discussions**: Community discussions and Q&A
- **Discord**: Real-time chat with other developers (if available)

### Advanced Configuration

#### Custom Task Creation

**VS Code** - Add to `.vscode/tasks.json`:

```json
{
  "label": "My Custom Task",
  "type": "shell",
  "command": "make",
  "args": ["my-target"],
  "group": "build"
}
```

**PyCharm** - Run/Debug Configurations → Add New → Shell Script:

- Script text: `make my-target`
- Working directory: `$ProjectFileDir$`

#### Environment-Specific Settings

Create environment-specific configuration files:

- `.env.development` - Development settings
- `.env.testing` - Test environment settings  
- `.env.production` - Production settings

Load appropriate environment:

```bash
export ENV=testing
make test-integration  # Uses .env.testing
```

#### Custom Code Templates

**VS Code** - Create snippets in `.vscode/snippets.json`
**PyCharm** - File → Settings → Editor → Live Templates

#### Integration with External Tools

Configure external tools for enhanced workflow:

- **Pre-commit hooks**: Automatic code quality checks
- **GitHub Actions**: CI/CD integration
- **Monitoring tools**: Performance and error tracking
- **Documentation generators**: API documentation

This completes the comprehensive IDE setup guide. The configuration optimizes developer productivity while maintaining code quality and providing robust debugging capabilities for MCP server development.
