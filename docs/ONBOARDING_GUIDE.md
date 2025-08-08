# 🚀 Crawl4AI MCP Developer Onboarding Guide

Welcome to the **Crawl4AI MCP** project! This guide will help you get up and running quickly and become a productive contributor to our web crawling and RAG-enabled MCP server.

## 🎯 Project Overview

Crawl4AI MCP is a **Docker-based MCP (Model Context Protocol) server** that provides AI agents and coding assistants with complete web search, crawling, and RAG (Retrieval Augmented Generation) capabilities.

### What Makes This Project Special

- **🔍 Smart RAG vs Traditional Scraping**: Instead of dumping raw content, we use intelligent RAG to extract only relevant content using semantic similarity search
- **🐳 Zero Configuration**: Complete Docker stack that works out of the box
- **⚡ Production Ready**: Includes HTTPS, security, monitoring, and comprehensive testing
- **🧠 AI-Optimized**: RAG strategies specifically built for coding assistants

### Core Technologies

- **FastMCP**: Modern MCP server implementation with async support
- **Crawl4AI**: Advanced web crawling with intelligent content extraction
- **SearXNG**: Private search engine integration
- **Qdrant/Supabase**: Vector databases for semantic search
- **Neo4j**: Knowledge graphs for AI hallucination detection
- **Docker**: Containerized services for easy deployment

## 🛠 Development Environment Setup

### Prerequisites

Before you begin, ensure you have:

- **Python 3.12+** (required)
- **Docker & Docker Compose** (required)
- **UV Package Manager** (we'll install this)
- **Git** (for version control)
- Basic familiarity with async Python and Docker

### Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/krashnicov/crawl4aimcp.git
cd crawl4aimcp

# Install UV package manager (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or restart your terminal

# Install Python dependencies
uv sync

# Copy environment configuration
cp .env.example .env
```

### Step 2: Configure Environment

Edit your `.env` file with the required credentials:

```bash
# Essential settings
OPENAI_API_KEY=your_openai_api_key_here

# Choose your vector database (Qdrant for local development)
VECTOR_DATABASE=qdrant
QDRANT_URL=http://qdrant:6333

# Optional: For knowledge graph features
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Optional: For Supabase (alternative to Qdrant)
# VECTOR_DATABASE=supabase
# SUPABASE_URL=your_supabase_project_url
# SUPABASE_SERVICE_KEY=your_supabase_service_key
```

### Step 3: Start Development Environment

```bash
# Start the complete development stack
make dev

# Or start in background with watch mode
make dev-bg

# Check status
make ps
```

This starts:

- **MCP Server**: <http://localhost:8051>
- **SearXNG Search**: <http://localhost:8080> (internal)
- **Qdrant Dashboard**: <http://localhost:6333/dashboard>
- **Neo4j Browser**: <http://localhost:7474>

### Step 4: Verify Setup

```bash
# Test the MCP server
curl http://localhost:8051/health

# Run unit tests to verify everything works
make test-unit

# Run integration tests (requires Docker services)
make test-integration
```

## 🏗 Architecture Deep Dive

### MCP Server Architecture

```
┌─────────────┐    MCP Protocol    ┌─────────────┐
│ MCP Clients │ ◄──────────────► │   FastMCP   │
│(Claude/etc) │                   │   Server    │
└─────────────┘                   └──────┬──────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
              ┌─────▼─────┐         ┌─────▼─────┐         ┌─────▼─────┐
              │  SearXNG  │         │ Crawl4AI  │         │   Neo4j   │
              │  Search   │         │ Crawler   │         │   Graph   │
              └─────┬─────┘         └─────┬─────┘         └─────┬─────┘
                    │                     │                     │
              ┌─────▼─────┐         ┌─────▼─────┐         ┌─────▼─────┐
              │   Valkey  │         │  Qdrant   │         │Knowledge  │
              │   Cache   │         │  Vectors  │         │   Graph   │
              └───────────┘         └───────────┘         └───────────┘
```

### Key Components

1. **`src/crawl4ai_mcp.py`**: Main MCP server with tool definitions
2. **`src/utils.py`**: Core utilities and database operations  
3. **`src/database/`**: Database adapters and interfaces
4. **`tests/`**: Comprehensive test suite
5. **`knowledge_graphs/`**: Neo4j integration for hallucination detection

### Tool Architecture

All functionality is exposed via `@mcp.tool()` decorators:

```python
@mcp.tool()
async def scrape_urls(urls: list[str]) -> str:
    """Scrape URLs and store in vector database"""
    # Implementation here
```

**Available Tools**:

- `scrape_urls`: Batch URL scraping with vector storage
- `smart_crawl_url`: Intelligent website crawling
- `perform_rag_query`: Semantic search with reranking
- `search`: Integrated search + scrape + RAG workflow
- `search_code_examples`: Code-specific RAG (when enabled)
- `parse_github_repository`: GitHub repo to knowledge graph
- `check_ai_script_hallucinations`: AI code validation

## 📝 Making Your First Contribution

### Development Workflow

1. **Create a feature branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Set up pre-commit hooks** (automatic quality checks):

   ```bash
   uv run pre-commit install
   uv run pre-commit install --hook-type commit-msg
   ```

3. **Start development environment**:

   ```bash
   make dev  # Foreground with logs
   # OR
   make dev-bg  # Background with watch mode
   ```

4. **Make your changes** following our coding standards:
   - Use async/await for all I/O operations
   - Add comprehensive docstrings (Google style)
   - Include type hints
   - Follow the existing code patterns

5. **Test your changes**:

   ```bash
   # Quick unit tests
   make test-unit
   
   # Integration tests
   make test-integration
   
   # Specific file
   make test-file FILE=tests/test_your_feature.py
   ```

6. **Commit with conventional commit format**:

   ```bash
   git add .
   git commit -m "feat: add new RAG enhancement strategy"
   ```

### Example: Adding a New MCP Tool

Let's add a simple tool to count words in crawled content:

1. **Add the tool in `src/crawl4ai_mcp.py`**:

   ```python
   @mcp.tool()
   async def count_words_in_source(source: str) -> str:
       """Count words in all content from a specific source domain.
       
       Args:
           source: Domain to count words for (e.g., 'docs.python.org')
       
       Returns:
           JSON string with word count statistics
       """
       try:
           # Get database adapter
           db_adapter = get_database_adapter()
           
           # Search for all content from source
           results = await db_adapter.search_similar(
               query="", 
               source_filter=source,
               match_count=1000
           )
           
           # Count words
           total_words = 0
           for result in results:
               total_words += len(result['content'].split())
           
           return json.dumps({
               "source": source,
               "total_documents": len(results),
               "total_words": total_words,
               "average_words_per_doc": total_words / len(results) if results else 0
           })
           
       except Exception as e:
           logger.error(f"Error counting words: {e}")
           return json.dumps({"error": str(e)})
   ```

2. **Add tests in `tests/test_crawl4ai_mcp.py`**:

   ```python
   @pytest.mark.asyncio
   async def test_count_words_in_source():
       """Test word counting functionality"""
       # Mock database response
       mock_results = [
           {"content": "hello world test content"},
           {"content": "more test content here"}
       ]
       
       # Test implementation
       # ... test code here
   ```

3. **Test your changes**:

   ```bash
   make test-file FILE=tests/test_crawl4ai_mcp.py
   ```

4. **Update documentation** if needed and commit:

   ```bash
   git add .
   git commit -m "feat: add word count tool for source analysis"
   ```

## 🧪 Testing Guidelines

We maintain **80% test coverage** with comprehensive unit and integration tests.

### Test Structure

```
tests/
├── test_utils.py      # Core utility tests
├── test_database_factory.py      # Database factory tests
├── test_crawl4ai_mcp.py          # MCP server tests
├── test_supabase_adapter.py      # Supabase integration
├── test_qdrant_adapter.py        # Qdrant integration
└── test_integration_simple.py    # End-to-end tests
```

### Running Tests

```bash
# Quick unit tests (30 seconds)
make test-unit

# Full test suite with coverage
make test-ci

# Specific service tests
make test-qdrant
make test-neo4j

# Debug failing tests
make test-debug

# Run with debugger
make test-pdb
```

### Test Environment

We use isolated Docker services for integration tests:

- **Qdrant Test**: `localhost:6333`
- **Neo4j Test**: `localhost:7474/7687`
- **SearXNG Test**: `localhost:8081`

### Writing Tests

**Unit Tests** (no external dependencies):

```python
@pytest.mark.unit
async def test_utility_function():
    """Test core functionality without external services"""
    result = await some_utility_function("test_input")
    assert result == "expected_output"
```

**Integration Tests** (require Docker services):

```python
@pytest.mark.integration
async def test_database_integration():
    """Test with real database connection"""
    db = get_database_adapter()
    result = await db.store_content("test", "content")
    assert result is not None
```

### Coverage Requirements

- **Minimum**: 80% overall coverage
- **Unit tests**: 85%+ for core modules
- **Integration tests**: 70%+ for adapters
- **Exclude**: Test files, configuration files

## 🔧 Common Development Tasks

### Adding a New RAG Strategy

1. **Update environment configuration**:

   ```bash
   # Add to .env
   USE_CUSTOM_STRATEGY=true
   ```

2. **Implement in `src/utils.py`**:

   ```python
   async def custom_rag_strategy(content: str, query: str) -> dict:
       """Custom RAG enhancement strategy"""
       # Implementation here
   ```

3. **Add configuration in `src/crawl4ai_mcp.py`**:

   ```python
   if os.getenv('USE_CUSTOM_STRATEGY', 'false').lower() == 'true':
       # Enable custom strategy
   ```

### Adding a New Database Adapter

1. **Create adapter in `src/database/custom_adapter.py`**:

   ```python
   from .base_interface import DatabaseInterface
   
   class CustomAdapter(DatabaseInterface):
       async def store_content(self, content: str) -> str:
           # Implementation
   ```

2. **Register in `src/database/factory.py`**:

   ```python
   def get_database_adapter():
       if database_type == "custom":
           return CustomAdapter()
   ```

3. **Add comprehensive tests**

### Debugging Issues

**View logs**:

```bash
# Development logs
make dev-logs

# All service logs
make logs

# Specific service
docker compose logs -f mcp-crawl4ai
```

**Interactive debugging**:

```bash
# Python REPL in container
make python

# Shell access
make shell

# Test specific functionality
make test-debug
```

**Database inspection**:

```bash
# Qdrant dashboard
make qdrant-shell  # Opens http://localhost:6333/dashboard

# Neo4j browser
make neo4j-shell   # Opens http://localhost:7474
```

## 📚 Resources and Getting Help

### Documentation

- **[README.md](../README.md)**: Complete project overview
- **[CLAUDE.md](../CLAUDE.md)**: Claude Code integration guide
- **[CONTRIBUTING.md](../CONTRIBUTING.md)**: Detailed contribution guidelines
- **[MCP_CLIENT_CONFIG.md](../MCP_CLIENT_CONFIG.md)**: MCP client setup
- **[Makefile](../Makefile)**: All available commands

### Key Technologies to Learn

1. **FastMCP**: [FastMCP Documentation](https://github.com/pydantic/fastmcp)
2. **Model Context Protocol**: [MCP Specification](https://modelcontextprotocol.io)
3. **Crawl4AI**: [Crawl4AI Documentation](https://crawl4ai.com)
4. **Qdrant**: [Vector Database Guide](https://qdrant.tech/documentation/)
5. **Docker Compose**: [Compose Documentation](https://docs.docker.com/compose/)

### Development Commands Reference

```bash
# Environment Management
make dev              # Start development environment
make dev-bg           # Start in background with watch
make dev-logs         # View development logs
make dev-down         # Stop development environment

# Testing
make test-unit        # Quick unit tests
make test-integration # Full integration tests
make test-ci          # Complete CI suite
make test-coverage    # Coverage reports

# Code Quality
make lint             # Run linting
make format           # Format code
make validate         # All quality checks

# Database Operations
make db-test          # Test database connections
make qdrant-shell     # Open Qdrant dashboard
make neo4j-shell      # Open Neo4j browser

# Utilities
make clean            # Clean test artifacts
make env-check        # Validate environment
make help             # Show all commands
```

### Getting Help

1. **Check existing issues**: Browse [GitHub Issues](https://github.com/krashnicov/crawl4aimcp/issues)
2. **Review documentation**: Start with README.md and related docs
3. **Run diagnostics**: Use `make env-check` and `make test-ci`
4. **Ask questions**: Create a GitHub issue with:
   - Clear problem description
   - Steps to reproduce
   - Environment details (`make env-check` output)
   - Relevant logs

### Code Style and Standards

- **Python**: Follow PEP 8 with 88-character line length
- **Docstrings**: Google style with comprehensive examples
- **Type Hints**: Required for all public functions
- **Async/Await**: Use for all I/O operations
- **Error Handling**: Comprehensive with proper logging
- **Testing**: Write tests before implementation (TDD encouraged)

### Performance Considerations

1. **Async Operations**: Always use async for I/O
2. **Batch Processing**: Group database operations
3. **Connection Pooling**: Reuse database connections
4. **Caching**: Leverage Valkey/Redis for frequently accessed data
5. **Resource Limits**: Be mindful of memory usage with large documents

## 🎉 Welcome to the Team

You're now ready to contribute to Crawl4AI MCP! Remember:

- **Start small**: Pick up "good first issue" tickets
- **Ask questions**: Better to ask than make assumptions
- **Test thoroughly**: Maintain our high coverage standards
- **Document changes**: Help future developers understand your work
- **Follow conventions**: Consistency makes the codebase maintainable

**Happy coding!** 🚀

---

*Last updated: January 2025*
*For questions or suggestions about this guide, please create a GitHub issue.*
