<h1 align="left">🐳 Crawl4AI+SearXNG MCP Server</h1>

<em>Web Crawling, Search and RAG Capabilities for AI Agents and AI Coding Assistants</em>

[![CI/CD Pipeline](https://github.com/krashnicov/crawl4aimcp/workflows/CI%2FCD%20Pipeline%20-%20Test%20%26%20Coverage/badge.svg)](https://github.com/krashnicov/crawl4aimcp/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **(FORKED FROM <https://github.com/coleam00/mcp-crawl4ai-rag>). Added SearXNG integration and batch scrape and processing capabilities.**

A **self-contained Docker solution** that combines the [Model Context Protocol (MCP)](https://modelcontextprotocol.io), [Crawl4AI](https://crawl4ai.com), [SearXNG](https://github.com/searxng/searxng), and [Supabase](https://supabase.com/) to provide AI agents and coding assistants with complete web **search, crawling, and RAG capabilities**.

**🚀 Complete Stack in One Command**: Deploy everything with `make prod` - no Python setup, no dependencies, no external services required.

### 🎯 Smart RAG vs Traditional Scraping

Unlike traditional scraping (such as [Firecrawl](https://github.com/mendableai/firecrawl-mcp-server)) that dumps raw content and overwhelms LLM context windows, this solution uses **intelligent RAG (Retrieval Augmented Generation)** to:

- **🔍 Extract only relevant content** using semantic similarity search
- **⚡ Prevent context overflow** by returning focused, pertinent information
- **🧠 Enhance AI responses** with precisely targeted knowledge
- **📊 Maintain context efficiency** for better LLM performance

**Flexible Output Options:**

- **RAG Mode** (default): Returns semantically relevant chunks with similarity scores
- **Raw Markdown Mode**: Full content extraction when complete context is needed
- **Hybrid Search**: Combines semantic and keyword search for comprehensive results

## 💡 Key Benefits

- **🔧 Zero Configuration**: Pre-configured SearXNG instance included
- **🐳 Docker-Only**: No Python environment setup required
- **🔍 Integrated Search**: Built-in SearXNG for private, fast search
- **⚡ Production Ready**: HTTPS, security, and monitoring included
- **🎯 AI-Optimized**: RAG strategies built for coding assistants

## Overview

This Docker-based MCP server provides a complete web intelligence stack that enables AI agents to:

- **Search the web** using the integrated SearXNG instance
- **Crawl and scrape** websites with advanced content extraction
- **Store content** in vector databases with intelligent chunking
- **Perform RAG queries** with multiple enhancement strategies

**Advanced RAG Strategies Available:**

- **Contextual Embeddings** for enriched semantic understanding
- **Hybrid Search** combining vector and keyword search
- **Agentic RAG** for specialized code example extraction
- **Reranking** for improved result relevance using cross-encoder models
- **Knowledge Graph** for AI hallucination detection and repository code analysis

See the [Configuration section](#configuration) below for details on how to enable and configure these strategies.

## Features

- **Smart URL Detection**: Automatically detects and handles different URL types (regular webpages, sitemaps, text files)
- **Recursive Crawling**: Follows internal links to discover content
- **Parallel Processing**: Efficiently crawls multiple pages simultaneously
- **Content Chunking**: Intelligently splits content by headers and size for better processing
- **Vector Search**: Performs RAG over crawled content, optionally filtering by data source for precision
- **Source Retrieval**: Retrieve sources available for filtering to guide the RAG process

## Tools

The server provides essential web crawling and search tools:

### Core Tools (Always Available)

1. **`scrape_urls`**: Scrape one or more URLs and store their content in the vector database. Supports both single URLs and lists of URLs for batch processing.
2. **`smart_crawl_url`**: Intelligently crawl a full website based on the type of URL provided (sitemap, llms-full.txt, or a regular webpage that needs to be crawled recursively)
3. **`get_available_sources`**: Get a list of all available sources (domains) in the database
4. **`perform_rag_query`**: Search for relevant content using semantic search with optional source filtering
5. **NEW!** **`search`**: Comprehensive web search tool that integrates SearXNG search with automated scraping and RAG processing. Performs a complete workflow: (1) searches SearXNG with the provided query, (2) extracts URLs from search results, (3) automatically scrapes all found URLs using existing scraping infrastructure, (4) stores content in vector database, and (5) returns either RAG-processed results organized by URL or raw markdown content. Key parameters: `query` (search terms), `return_raw_markdown` (bypasses RAG for raw content), `num_results` (search result limit), `batch_size` (database operation batching), `max_concurrent` (parallel scraping sessions). Ideal for research workflows, competitive analysis, and content discovery with built-in intelligence.

### Conditional Tools

6. **`search_code_examples`** (requires `USE_AGENTIC_RAG=true`): Search specifically for code examples and their summaries from crawled documentation. This tool provides targeted code snippet retrieval for AI coding assistants.

### Knowledge Graph Tools (requires `USE_KNOWLEDGE_GRAPH=true`, see below)

7. **`parse_github_repository`**: Parse a GitHub repository into a Neo4j knowledge graph, extracting classes, methods, functions, and their relationships for hallucination detection
8. **`check_ai_script_hallucinations`**: Analyze Python scripts for AI hallucinations by validating imports, method calls, and class usage against the knowledge graph
9. **`query_knowledge_graph`**: Explore and query the Neo4j knowledge graph with commands like `repos`, `classes`, `methods`, and custom Cypher queries
10. **`get_script_analysis_info`**: Get information about script analysis setup, available paths, and usage instructions for hallucination detection tools

## 🔍 Code Search and Validation

**Advanced Neo4j-Qdrant Integration for Reliable AI Code Generation**

The system provides sophisticated code search and validation capabilities by combining:

- **Qdrant**: Semantic vector search for finding relevant code examples
- **Neo4j**: Structural validation against parsed repository knowledge graphs
- **AI Hallucination Detection**: Prevents AI from generating non-existent methods or incorrect usage patterns

### When to Use Neo4j vs Qdrant

| Use Case | Neo4j (Knowledge Graph) | Qdrant (Vector Search) | Combined Approach |
|----------|------------------------|----------------------|-------------------|
| **Exact Structure Validation** | ✅ Perfect - validates class/method existence | ❌ Cannot verify structure | 🏆 Best - structure + semantics |
| **Semantic Code Search** | ❌ Limited - no semantic understanding | ✅ Perfect - finds similar patterns | 🏆 Best - validated similarity |
| **Hallucination Detection** | ✅ Good - catches structural errors | ❌ Cannot detect fake methods | 🏆 Best - comprehensive validation |
| **Code Discovery** | ❌ Requires exact names | ✅ Perfect - fuzzy semantic search | 🏆 Best - discovered + validated |
| **Performance** | ⚡ Fast for exact queries | ⚡ Fast for semantic search | ⚖️ Balanced - parallel validation |

### Enhanced Tools for Code Search and Validation

#### 10. **`smart_code_search`** (requires both `USE_KNOWLEDGE_GRAPH=true` and `USE_AGENTIC_RAG=true`)

Intelligent code search that combines Qdrant semantic search with Neo4j structural validation:

- **Semantic Discovery**: Find code patterns using natural language queries
- **Structural Validation**: Verify all code examples against real repository structure
- **Confidence Scoring**: Get reliability scores for each result (0.0-1.0)
- **Validation Modes**: Choose between "fast", "balanced", or "thorough" validation
- **Intelligent Fallback**: Works even when one system is unavailable

#### 11. **`extract_and_index_repository_code`** (requires both systems)

Bridge Neo4j knowledge graph data into Qdrant for searchable code examples:

- **Knowledge Graph Extraction**: Pull structured code from Neo4j
- **Semantic Indexing**: Generate embeddings and store in Qdrant
- **Rich Metadata**: Preserve class/method relationships and context
- **Batch Processing**: Efficient indexing of large repositories

#### 12. **`check_ai_script_hallucinations_enhanced`** (requires both systems)

Advanced hallucination detection using dual validation:

- **Neo4j Structural Check**: Validate against actual repository structure
- **Qdrant Semantic Check**: Find similar real code examples
- **Combined Confidence**: Merge validation results for higher accuracy
- **Code Suggestions**: Provide corrections from real code examples

### Basic Workflow

1. **Index Repository Structure**:

   ```
   parse_github_repository("https://github.com/pydantic/pydantic-ai.git")
   ```

2. **Extract and Index Code Examples**:

   ```
   extract_and_index_repository_code("pydantic-ai")
   ```

3. **Search with Validation**:

   ```
   smart_code_search(
     query="async function with error handling",
     source_filter="pydantic-ai",
     min_confidence=0.7,
     validation_mode="balanced"
   )
   ```

4. **Validate AI Code**:

   ```
   check_ai_script_hallucinations_enhanced("/path/to/ai_script.py")
   ```

### 📁 Using Hallucination Detection Tools

The hallucination detection tools require access to Python scripts. The Docker container includes volume mounts for convenient script analysis:

**Script Locations:**

- **`./analysis_scripts/user_scripts/`** - Place your Python scripts here (recommended)
- **`./analysis_scripts/test_scripts/`** - For test scripts
- **`/tmp/`** - Temporary scripts (automatically mapped to container)

**How to Use:**

1. **Place your script in the appropriate directory:**

   ```bash
   cp my_ai_script.py ./analysis_scripts/user_scripts/
   ```

2. **Call the hallucination detection tool:**

   ```json
   {
     "tool": "check_ai_script_hallucinations",
     "arguments": {
       "script_path": "analysis_scripts/user_scripts/my_ai_script.py"
     }
   }
   ```

3. **Alternative paths work automatically:**
   - `"script_path": "/tmp/test.py"` - Uses /tmp mount
   - `"script_path": "my_script.py"` - Defaults to user_scripts directory

4. **Use the helper tool for setup info:**

   ```json
   {
     "tool": "get_script_analysis_info",
     "arguments": {}
   }
   ```

**Results** are saved to `./analysis_scripts/validation_results/` for review.

### Simple Usage Examples

**Find validated code examples**:

```json
{
  "tool": "smart_code_search",
  "arguments": {
    "query": "database connection with async context manager",
    "min_confidence": 0.6,
    "validation_mode": "fast"
  }
}
```

**Detect AI hallucinations**:

```json
{
  "tool": "check_ai_script_hallucinations_enhanced", 
  "arguments": {
    "script_path": "/tmp/ai_generated_code.py",
    "include_code_suggestions": true
  }
}
```

For complete setup instructions, configuration options, and advanced usage patterns, see the [Neo4j-Qdrant Integration Guide](docs/NEO4J_QDRANT_INTEGRATION.md).

## Prerequisites

**Required:**

- [Docker and Docker Compose](https://www.docker.com/products/docker-desktop/) - This is a Docker-only solution
- [OpenAI API key](https://platform.openai.com/api-keys) - For generating embeddings
- **Vector Database** (choose one):
  - [Supabase account](https://supabase.com/) - Cloud-hosted PostgreSQL with pgvector (default)
  - [Qdrant](https://qdrant.tech/) - Self-hosted vector database (runs in Docker)

**Optional:**

- [Neo4j instance](https://neo4j.com/) - For knowledge graph functionality (see [Knowledge Graph Setup](#knowledge-graph-setup))
- Custom domain - For production HTTPS deployment

## Installation

This is a **Docker-only solution** - no Python environment setup required!

### Quick Start

1. **Clone this repository:**

   ```bash
   git clone https://github.com/coleam00/mcp-crawl4ai-rag.git
   cd mcp-crawl4ai-rag
   ```

2. **Configure environment:**

   ```bash
   cp .env.example .env
   # Edit .env with your API keys (see Configuration section below)
   ```

3. **Deploy the complete stack:**

   ```bash
   make prod  # For production
   # or
   make dev-bg  # For development with watch mode
   ```

That's it! Your complete search, crawl, and RAG stack is now running:

- **MCP Server**: <http://localhost:8051>
- **SearXNG Search**: <http://localhost:8080> (internal)
- **Caddy Proxy**: Handles HTTPS and routing

### What Gets Deployed

The Docker Compose stack includes:

- **MCP Crawl4AI Server** - Main application server
- **SearXNG** - Private search engine instance
- **Valkey** - Redis-compatible cache for SearXNG
- **Caddy** - Reverse proxy with automatic HTTPS

## Database Setup *IMPORTANT!*

Before running the server, you need to set up the database with the pgvector extension:

1. Go to the SQL Editor in your Supabase dashboard (create a new project first if necessary)

2. Create a new query and paste the contents of `crawled_pages.sql`

3. Run the query to create the necessary tables and functions

## Knowledge Graph Setup (Optional)

To enable AI hallucination detection and repository analysis features, you need to set up Neo4j.

**Note:** The knowledge graph functionality works fully with Docker and supports all features.

### Neo4j Setup Options

**Option 1: Local AI Package (Recommended)**

The easiest way to get Neo4j running is with the [Local AI Package](https://github.com/coleam00/local-ai-packaged):

1. **Clone and start Neo4j**:

   ```bash
   git clone https://github.com/coleam00/local-ai-packaged.git
   cd local-ai-packaged
   # Follow repository instructions to start Neo4j with Docker Compose
   ```

2. **Connection details for Docker**:
   - URI: `bolt://host.docker.internal:7687` (for Docker containers)
   - URI: `bolt://localhost:7687` (for local access)
   - Username: `neo4j`
   - Password: Check Local AI Package documentation

**Option 2: Neo4j Docker**

Run Neo4j directly with Docker:

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your-password \
  neo4j:latest
```

**Option 3: Neo4j Desktop**

Use Neo4j Desktop for a local GUI-based installation:

1. **Download and install**: [Neo4j Desktop](https://neo4j.com/download/)
2. **Create a new database** with your preferred settings
3. **Connection details**:
   - URI: `bolt://host.docker.internal:7687` (for Docker containers)
   - URI: `bolt://localhost:7687` (for local access)
   - Username: `neo4j`
   - Password: Whatever you set during database creation

## Configuration

Configure the Docker stack by editing your `.env` file (copy from `.env.example`):

```bash
# ========================================
# MCP SERVER CONFIGURATION
# ========================================
TRANSPORT=sse
HOST=0.0.0.0
PORT=8051

# ========================================
# INTEGRATED SEARXNG CONFIGURATION
# ========================================
# Pre-configured for Docker Compose - SearXNG runs internally
SEARXNG_URL=http://searxng:8080
SEARXNG_USER_AGENT=MCP-Crawl4AI-RAG-Server/1.0
SEARXNG_DEFAULT_ENGINES=google,bing,duckduckgo
SEARXNG_TIMEOUT=30

# Optional: Custom domain for production HTTPS
SEARXNG_HOSTNAME=http://localhost
# SEARXNG_TLS=your-email@example.com  # For Let's Encrypt

# ========================================
# AI SERVICES CONFIGURATION
# ========================================
# Required: OpenAI API for embeddings
OPENAI_API_KEY=your_openai_api_key

# LLM for summaries and contextual embeddings
MODEL_CHOICE=gpt-4.1-nano-2025-04-14

# ========================================
# VECTOR DATABASE CONFIGURATION
# ========================================
# Choose your vector database: supabase or qdrant
VECTOR_DATABASE=supabase

# Option 1: Supabase (cloud-hosted PostgreSQL with pgvector)
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Option 2: Qdrant (self-hosted, runs in Docker)
# Qdrant service is included in the docker compose setup
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=  # Optional, leave empty for local development

# ========================================
# RAG ENHANCEMENT STRATEGIES
# ========================================
USE_CONTEXTUAL_EMBEDDINGS=false
USE_HYBRID_SEARCH=false
USE_AGENTIC_RAG=false
USE_RERANKING=false
USE_KNOWLEDGE_GRAPH=false

# Optional: Neo4j for knowledge graph (if USE_KNOWLEDGE_GRAPH=true)
# Use host.docker.internal:7687 for Docker Desktop on Windows/Mac
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

### Key Configuration Notes

**🔍 SearXNG Integration**: The stack includes a pre-configured SearXNG instance that runs automatically. No external setup required!

**🐳 Docker Networking**: The default configuration uses Docker internal networking (`http://searxng:8080`) which works out of the box.

**🔐 Production Setup**: For production, set `SEARXNG_HOSTNAME` to your domain and `SEARXNG_TLS` to your email for automatic HTTPS.

### Choosing a Vector Database

This solution supports two vector database options:

#### Supabase (Default)

- **Pros**: Cloud-hosted, no infrastructure management, built-in authentication, scales automatically
- **Cons**: Requires account creation, potential latency for remote queries, usage limits on free tier
- **Best for**: Production deployments, teams, when you want managed infrastructure

#### Qdrant (Self-hosted)

- **Pros**: Runs locally in Docker, no external accounts needed, full control over data, no usage limits
- **Cons**: Requires more memory/CPU, you manage backups and scaling
- **Best for**: Local development, privacy-sensitive applications, when you want complete control

**To use Qdrant instead of Supabase:**

1. Set `VECTOR_DATABASE=qdrant` in your `.env` file
2. Run `make prod` or `make dev-bg`

### RAG Strategy Options

The Crawl4AI RAG MCP server supports four powerful RAG strategies that can be enabled independently:

#### 1. **USE_CONTEXTUAL_EMBEDDINGS**

When enabled, this strategy enhances each chunk's embedding with additional context from the entire document. The system passes both the full document and the specific chunk to an LLM (configured via `MODEL_CHOICE`) to generate enriched context that gets embedded alongside the chunk content.

- **When to use**: Enable this when you need high-precision retrieval where context matters, such as technical documentation where terms might have different meanings in different sections.
- **Trade-offs**: Slower indexing due to LLM calls for each chunk, but significantly better retrieval accuracy.
- **Cost**: Additional LLM API calls during indexing.

#### 2. **USE_HYBRID_SEARCH**

Combines traditional keyword search with semantic vector search to provide more comprehensive results. The system performs both searches in parallel and intelligently merges results, prioritizing documents that appear in both result sets.

- **When to use**: Enable this when users might search using specific technical terms, function names, or when exact keyword matches are important alongside semantic understanding.
- **Trade-offs**: Slightly slower search queries but more robust results, especially for technical content.
- **Cost**: No additional API costs, just computational overhead.

#### 3. **USE_AGENTIC_RAG**

Enables specialized code example extraction and storage. When crawling documentation, the system identifies code blocks (≥300 characters), extracts them with surrounding context, generates summaries, and stores them in a separate vector database table specifically designed for code search.

- **When to use**: Essential for AI coding assistants that need to find specific code examples, implementation patterns, or usage examples from documentation.
- **Trade-offs**: Significantly slower crawling due to code extraction and summarization, requires more storage space.
- **Cost**: Additional LLM API calls for summarizing each code example.
- **Benefits**: Provides a dedicated `search_code_examples` tool that AI agents can use to find specific code implementations.

#### 4. **USE_RERANKING**

Applies cross-encoder reranking to search results after initial retrieval. Uses a lightweight cross-encoder model (`cross-encoder/ms-marco-MiniLM-L-6-v2`) to score each result against the original query, then reorders results by relevance.

- **When to use**: Enable this when search precision is critical and you need the most relevant results at the top. Particularly useful for complex queries where semantic similarity alone might not capture query intent.
- **Trade-offs**: Adds ~100-200ms to search queries depending on result count, but significantly improves result ordering.
- **Cost**: No additional API costs - uses a local model that runs on CPU.
- **Benefits**: Better result relevance, especially for complex queries. Works with both regular RAG search and code example search.

#### 5. **USE_KNOWLEDGE_GRAPH**

Enables AI hallucination detection and repository analysis using Neo4j knowledge graphs. When enabled, the system can parse GitHub repositories into a graph database and validate AI-generated code against real repository structures. **Fully compatible with Docker** - all functionality works within the containerized environment.

- **When to use**: Enable this for AI coding assistants that need to validate generated code against real implementations, or when you want to detect when AI models hallucinate non-existent methods, classes, or incorrect usage patterns.
- **Trade-offs**: Requires Neo4j setup and additional dependencies. Repository parsing can be slow for large codebases, and validation requires repositories to be pre-indexed.
- **Cost**: No additional API costs for validation, but requires Neo4j infrastructure (can use free local installation or cloud AuraDB).
- **Benefits**: Provides three powerful tools: `parse_github_repository` for indexing codebases, `check_ai_script_hallucinations` for validating AI-generated code, and `query_knowledge_graph` for exploring indexed repositories.

**Usage with MCP Tools:**

You can tell the AI coding assistant to add a Python GitHub repository to the knowledge graph:

"Add <https://github.com/pydantic/pydantic-ai.git> to the knowledge graph"

Make sure the repo URL ends with .git.

You can also have the AI coding assistant check for hallucinations with scripts it creates using the MCP `check_ai_script_hallucinations` tool.

### Recommended Configurations

**For general documentation RAG:**

```
USE_CONTEXTUAL_EMBEDDINGS=false
USE_HYBRID_SEARCH=true
USE_AGENTIC_RAG=false
USE_RERANKING=true
```

**For AI coding assistant with code examples:**

```
USE_CONTEXTUAL_EMBEDDINGS=true
USE_HYBRID_SEARCH=true
USE_AGENTIC_RAG=true
USE_RERANKING=true
USE_KNOWLEDGE_GRAPH=false
```

**For AI coding assistant with hallucination detection:**

```
USE_CONTEXTUAL_EMBEDDINGS=true
USE_HYBRID_SEARCH=true
USE_AGENTIC_RAG=true
USE_RERANKING=true
USE_KNOWLEDGE_GRAPH=true
```

**For fast, basic RAG:**

```
USE_CONTEXTUAL_EMBEDDINGS=false
USE_HYBRID_SEARCH=true
USE_AGENTIC_RAG=false
USE_RERANKING=false
USE_KNOWLEDGE_GRAPH=false
```

## Running the Server

The complete stack is managed through Docker Compose:

### Start the Stack

```bash
make prod  # For production
# or
make dev-bg  # For development
```

### View Logs

```bash
# View logs
make logs  # Choose environment when prompted
# or directly:
make dev-logs  # For development logs
make prod-logs  # For production logs
```

### Stop the Stack

```bash
make down  # Stops all environments
# or specifically:
make dev-down  # Stop development
make prod-down  # Stop production
```

### Restart Services

```bash
# Restart services
make restart  # Choose environment when prompted
# or directly:
make dev-restart  # Restart development
make prod-restart  # Restart production
```

The MCP server will be available at `http://localhost:8051` for SSE connections.

## Integration with MCP Clients

After starting the Docker stack with `make prod` or `make dev-bg`, your MCP server will be available for integration.

### HTTP Configuration (Docker Default)

The Docker stack runs with HTTP transport by default. For complete configuration instructions, see [MCP_CLIENT_CONFIG.md](MCP_CLIENT_CONFIG.md).

**Quick Claude Desktop Config:**

```json
{
  "mcpServers": {
    "crawl4ai-docker": {
      "url": "http://localhost:8051",
      "transport": "http"
    }
  }
}
```

**Windsurf (alternative syntax):**

```json
{
  "mcpServers": {
    "crawl4ai-rag": {
      "transport": "sse",
      "serverUrl": "http://localhost:8051/sse"
    }
  }
}
```

**Claude Code CLI:**

```bash
claude mcp add-json crawl4ai-rag '{"type":"http","url":"http://localhost:8051/sse"}' --scope user
```

### Docker Networking Notes

- **Same machine**: Use `http://localhost:8051/sse`
- **Different container**: Use `http://host.docker.internal:8051/sse`
- **Remote access**: Replace `localhost` with your server's IP address

### Production Deployment

For production use with custom domains:

1. **Update your `.env`**:

   ```bash
   SEARXNG_HOSTNAME=https://yourdomain.com
   SEARXNG_TLS=your-email@example.com
   ```

2. **Access via HTTPS**:

   ```
   https://yourdomain.com:8051/sse
   ```

### Health Check

Verify the server is running:

```bash
curl http://localhost:8051/health
```

## Knowledge Graph Architecture

The knowledge graph system stores repository code structure in Neo4j with the following components:

### Core Components (`knowledge_graphs/` folder)

- **`parse_repo_into_neo4j.py`**: Clones and analyzes GitHub repositories, extracting Python classes, methods, functions, and imports into Neo4j nodes and relationships
- **`ai_script_analyzer.py`**: Parses Python scripts using AST to extract imports, class instantiations, method calls, and function usage
- **`knowledge_graph_validator.py`**: Validates AI-generated code against the knowledge graph to detect hallucinations (non-existent methods, incorrect parameters, etc.)
- **`hallucination_reporter.py`**: Generates comprehensive reports about detected hallucinations with confidence scores and recommendations
- **`query_knowledge_graph.py`**: Interactive CLI tool for exploring the knowledge graph (functionality now integrated into MCP tools)

### Knowledge Graph Schema

The Neo4j database stores code structure as:

**Nodes:**

- `Repository`: GitHub repositories
- `File`: Python files within repositories  
- `Class`: Python classes with methods and attributes
- `Method`: Class methods with parameter information
- `Function`: Standalone functions
- `Attribute`: Class attributes

**Relationships:**

- `Repository` -[:CONTAINS]-> `File`
- `File` -[:DEFINES]-> `Class`
- `File` -[:DEFINES]-> `Function`
- `Class` -[:HAS_METHOD]-> `Method`
- `Class` -[:HAS_ATTRIBUTE]-> `Attribute`

### Workflow

1. **Repository Parsing**: Use `parse_github_repository` tool to clone and analyze open-source repositories
2. **Code Validation**: Use `check_ai_script_hallucinations` tool to validate AI-generated Python scripts
3. **Knowledge Exploration**: Use `query_knowledge_graph` tool to explore available repositories, classes, and methods

## Troubleshooting

### Docker Issues

**Container won't start:**

```bash
# Check logs for specific errors
make logs  # Choose environment

# Restart problematic services
make restart  # Choose environment
```

**SearXNG not accessible:**

```bash
# Check if SearXNG is running
make logs  # Choose environment, then view searxng logs

# Open shell to verify networking
make shell  # Choose environment
```

**Port conflicts:**

```bash
# Check what's using ports
netstat -tulpn | grep -E ":(8051|8080)"

# Change ports in docker-compose.yml if needed
ports:
  - "8052:8051"  # Changed from 8051:8051
```

### Common Configuration Issues

**Environment variables not loading:**

- Ensure `.env` file is in the root directory
- Verify no spaces around `=` in `.env` file
- Check for special characters that need quoting

**API connection failures:**

- Verify `OPENAI_API_KEY` is valid and has credits
- Check `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` are correct
- Test API connectivity from within container:

  ```bash
  make shell  # Choose environment
  # Then run: curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
  ```

**Neo4j connection issues:**

- Use `host.docker.internal:7687` instead of `localhost:7687` for Neo4j running on host
- Verify Neo4j is running and accessible
- Check firewall settings for port 7687

### Performance Optimization

**Memory usage:**

```bash
# Monitor resource usage
docker stats

# Adjust memory limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 2G
```

**Disk space:**

```bash
# Clean up Docker
docker system prune -a

# Check volume usage
docker volume ls
```

### Getting Help

1. **Check logs first**: `make logs`
2. **Test connectivity**: `make shell` then use `curl` commands
3. **Reset everything**: `make clean-all && make prod`

## Testing

The project includes comprehensive unit and integration tests with a fully isolated test environment. All tests run independently without interfering with development or production environments.

### 📋 Deprecation Warnings

**Important**: Before running tests, review the [Deprecation Warnings Documentation](docs/DEPRECATION_WARNINGS.md) to track any warnings from dependencies. Current known warnings are from external dependencies (Pydantic, fake_http_header) and do not affect functionality.

### 🚀 Quick Start

**Validate test environment and run tests**:

```bash
# Validate entire test setup (recommended first run)
./scripts/validate-test-environment.sh

# Quick unit tests (no external dependencies, ~30 seconds)
make test-unit

# Full test suite with coverage (includes integration tests, ~2 minutes)
make test-ci
```

### 📋 Test Environment Setup

The test environment uses completely isolated services with dedicated ports and configurations:

- **Qdrant Test**: `localhost:6333` (isolated vector database)
- **Neo4j Test**: `localhost:7474` / `localhost:7687` (isolated graph database)  
- **SearXNG Test**: `localhost:8081` (isolated search engine)
- **Test Configuration**: `.env.test` (optimized for fast testing)

**Manual setup**:

```bash
# 1. Ensure test configuration exists
ls .env.test  # Should exist (created automatically)

# 2. Start isolated test services
make docker-test-up-wait

# 3. Verify services are ready
make test-db-connect
```

### 🧪 Running Tests

**Quick development tests**:

```bash
make test-quick      # Core unit tests only (~15 seconds)
make test-unit       # All unit tests (~30 seconds)
make test-coverage   # Unit tests with coverage report
```

**Integration tests** (require Docker services):

```bash
make test-integration    # All integration tests (~1 minute)
make test-searxng       # SearXNG-specific integration tests
make test-qdrant        # Qdrant-specific integration tests  
make test-neo4j         # Neo4j-specific integration tests
```

**Comprehensive testing**:

```bash
make test-all        # All tests (unit + integration)
make test-ci         # Full CI suite with coverage
make test-coverage-ci # All tests with coverage (mimics CI)
```

**Specialized testing**:

```bash
make test-file FILE=tests/test_example.py    # Test specific file
make test-mark MARK=integration              # Test specific marker
make test-debug                              # Verbose debugging output
make test-pdb                               # Run with PDB debugger
```

### 🔧 Test Environment Management

**Service management**:

```bash
make docker-test-up           # Start test services
make docker-test-up-wait      # Start and wait for readiness
make docker-test-down         # Stop and clean test services
make docker-test-status       # Show service status
make docker-test-logs         # View service logs
```

**Service health checks**:

```bash
make test-db-connect         # Test database connectivity
curl http://localhost:6333/readyz   # Qdrant health
curl http://localhost:8081/healthz  # SearXNG health
```

### 📊 Coverage and CI

**Coverage reports**:

```bash
make test-coverage           # Generate HTML coverage report
# View: open htmlcov/index.html

make test-coverage-ci        # CI-style coverage with XML output
```

**CI Integration**:

- **GitHub Actions**: Automated testing on push/PR
- **Multi-Python**: Tests run on Python 3.12 and 3.13
- **Matrix Testing**: Unit tests grouped by component
- **Integration Testing**: Full service stack testing
- **Coverage Threshold**: 80% minimum required (enforced in GitHub Actions)
- **Coverage Reporting**: Automatic coverage reports generated as artifacts with PR comments
- **Security Scanning**: Trivy vulnerability scanning

### 🏗️ Test Structure

**Test organization**:

```
tests/
├── test_utils.py      # Core utility tests
├── test_database_factory.py      # Database factory tests  
├── test_crawl4ai_mcp.py          # MCP server tests
├── test_supabase_adapter.py      # Supabase integration
├── test_qdrant_adapter.py        # Qdrant integration
├── test_database_interface.py    # Database interface tests
└── test_integration_simple.py    # Basic integration tests
```

**Test markers**:

- `@pytest.mark.unit`: Unit tests (fast, no external deps)
- `@pytest.mark.integration`: Integration tests (require services)
- `@pytest.mark.searxng`: SearXNG-specific tests
- `@pytest.mark.performance`: Performance/benchmark tests

**Test isolation**:

- ✅ Separate test databases and collections
- ✅ Isolated Docker network (`test-network`)  
- ✅ Different ports to avoid conflicts
- ✅ Independent configuration (`.env.test`)
- ✅ Cleanup between test runs

### 🔍 Development Testing

**Watch mode** (for active development):

```bash
make test-watch             # Re-run tests on file changes
make test-debug             # Verbose output for troubleshooting
```

**Performance testing**:

```bash
make test-performance       # Run performance benchmarks
# Add custom benchmarks with @pytest.mark.performance
```

### 🧹 Cleanup

**Clean test artifacts**:

```bash
make clean                  # Remove test caches and reports
make clean-all              # Remove everything including Docker volumes
make docker-test-down       # Stop test services and remove volumes
```

**Reset test environment**:

```bash
make docker-test-down && make docker-test-up-wait
```

### 🚨 Troubleshooting Tests

**Common issues**:

1. **Services not ready**:

   ```bash
   make docker-test-logs      # Check service startup logs
   make test-db-connect       # Verify connectivity
   ```

2. **Port conflicts**:

   ```bash
   # Check what's using test ports
   lsof -i :6333 -i :7474 -i :7687 -i :8081
   ```

3. **Test failures**:

   ```bash
   make test-debug            # Verbose test output
   make test-pdb             # Interactive debugging
   ```

4. **Environment issues**:

   ```bash
   ./scripts/validate-test-environment.sh  # Full validation
   ```

**Performance optimization**:

- Unit tests run in parallel by default
- Integration tests use optimized service configurations
- Test data is minimized for speed
- Services use resource limits for consistency

## Development & Customization

This Docker stack provides a foundation for building more complex MCP servers:

1. **Modify the MCP server**: Edit files in `src/` and rebuild: `make dev-rebuild`
2. **Add custom tools**: Extend `src/crawl4ai_mcp.py` with `@mcp.tool()` decorators
3. **Customize SearXNG**: Edit `searxng/settings.yml` and restart
4. **Add services**: Extend `docker-compose.yml` with additional containers
