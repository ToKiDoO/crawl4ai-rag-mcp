# Neo4j-Qdrant Integration Usage Examples

**Practical examples for code search, validation, and hallucination detection**

## Quick Start Examples

### Example 1: Basic Repository Setup and Search

This example shows the complete workflow from repository indexing to validated search.

#### Step 1: Index a Repository

```bash
# Parse pydantic-ai repository into Neo4j knowledge graph
curl -X POST "http://localhost:8051/parse_github_repository" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/pydantic/pydantic-ai.git"
  }'
```

**Expected Response:**

```json
{
  "success": true,
  "repository": "pydantic-ai",
  "parsing_summary": {
    "files_processed": 45,
    "classes_found": 12,
    "methods_found": 89,
    "functions_found": 23,
    "total_parsing_time": "12.3s"
  },
  "neo4j_storage": {
    "nodes_created": 169,
    "relationships_created": 267,
    "indexes_updated": true
  }
}
```

#### Step 2: Extract and Index Code Examples

```bash
# Extract code from Neo4j and index in Qdrant for semantic search
curl -X POST "http://localhost:8051/extract_and_index_repository_code" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name": "pydantic-ai"
  }'
```

**Expected Response:**

```json
{
  "success": true,
  "repository_name": "pydantic-ai",
  "indexed_count": 124,
  "extraction_summary": {
    "classes": 12,
    "methods": 89,
    "functions": 23
  },
  "storage_summary": {
    "embeddings_generated": 124,
    "examples_stored": 124,
    "total_code_words": 15420
  },
  "message": "Successfully indexed 124 code examples from pydantic-ai"
}
```

#### Step 3: Perform Validated Search

```bash
# Search for AI agent creation patterns with validation
curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "create AI agent with OpenAI model",
    "match_count": 3,
    "source_filter": "pydantic-ai",
    "min_confidence": 0.6,
    "validation_mode": "balanced",
    "include_suggestions": true
  }'
```

**Example Response:**

```json
{
  "success": true,
  "query": "create AI agent with OpenAI model",
  "validation_mode": "balanced",
  "total_results": 3,
  "high_confidence_results": 2,
  "results": [
    {
      "code_example": "from pydantic_ai import Agent\n\nagent = Agent(\n    'openai:gpt-4',\n    system_prompt='You are a helpful assistant.'\n)",
      "summary": "Agent creation with OpenAI GPT-4 model",
      "similarity_score": 0.94,
      "validation": {
        "confidence_score": 0.89,
        "status": "validated",
        "neo4j_validation": {
          "class_exists": true,
          "method_exists": true,
          "parameters_valid": true,
          "confidence": 0.92
        },
        "qdrant_validation": {
          "semantic_match": true,
          "pattern_confidence": 0.85,
          "related_examples": 7
        }
      },
      "metadata": {
        "repository_name": "pydantic-ai",
        "file_path": "examples/basic_agent.py",
        "class_name": "Agent",
        "method_name": "__init__",
        "line_number": 12
      },
      "suggestions": [
        "Consider adding error handling for model initialization",
        "Set timeout parameters for production use"
      ]
    },
    {
      "code_example": "agent = Agent('openai:gpt-3.5-turbo')\nresult = await agent.run('Hello world')",
      "summary": "Simple agent with async execution",
      "similarity_score": 0.87,
      "validation": {
        "confidence_score": 0.82,
        "status": "validated",
        "neo4j_validation": {
          "class_exists": true,
          "method_exists": true,
          "parameters_valid": true,
          "confidence": 0.88
        },
        "qdrant_validation": {
          "semantic_match": true,
          "pattern_confidence": 0.74,
          "related_examples": 12
        }
      },
      "metadata": {
        "repository_name": "pydantic-ai",
        "file_path": "tests/test_agent.py",
        "class_name": "Agent",
        "method_name": "run",
        "line_number": 45
      }
    }
  ],
  "performance_metrics": {
    "search_time_ms": 156,
    "validation_time_ms": 89,
    "total_time_ms": 245,
    "cache_hit": false,
    "parallel_validations": 3
  },
  "health_status": {
    "neo4j": "healthy",
    "qdrant": "healthy",
    "integration": "optimal"
  }
}
```

### Example 2: AI Hallucination Detection

This example demonstrates detecting AI-generated code that contains non-existent methods or incorrect usage patterns.

#### Create Test Script with Potential Hallucinations

```python
# test_ai_script.py - Contains intentional hallucinations for testing
"""
AI-generated script with potential hallucinations
"""

from pydantic_ai import Agent, ModelError

def create_advanced_agent():
    # Potential hallucination: non-existent parameters
    agent = Agent(
        model='openai:gpt-4',
        temperature=0.7,
        max_retries=3,
        custom_validation=True,  # This might not exist
        memory_enabled=True      # This might not exist
    )
    
    # Potential hallucination: non-existent method
    agent.set_memory_limit(1000)  # Does this method exist?
    
    return agent

async def run_agent_with_validation():
    agent = create_advanced_agent()
    
    # Potential hallucination: incorrect method signature
    result = await agent.run_with_context(
        prompt="Hello",
        context_window=4000,      # Parameter might not exist
        validation_mode="strict"  # Parameter might not exist
    )
    
    # Potential hallucination: accessing non-existent attribute
    confidence = result.metadata.confidence_score  # Does this exist?
    
    return result, confidence
```

#### Run Hallucination Detection

```bash
# Save the script and run enhanced hallucination detection
curl -X POST "http://localhost:8051/check_ai_script_hallucinations_enhanced" \
  -H "Content-Type: application/json" \
  -d '{
    "script_path": "/tmp/test_ai_script.py",
    "include_code_suggestions": true,
    "detailed_analysis": true
  }'
```

**Example Response:**

```json
{
  "success": true,
  "script_path": "/tmp/test_ai_script.py", 
  "overall_assessment": {
    "risk_level": "high",
    "confidence_score": 0.32,
    "total_elements_analyzed": 8,
    "validated_elements": 3,
    "potential_hallucinations": 5,
    "critical_issues": 2
  },
  "hallucinations": {
    "critical": [
      {
        "type": "method_call",
        "element_name": "set_memory_limit",
        "line_number": 18,
        "confidence": 0.15,
        "severity": "high",
        "description": "Method 'set_memory_limit' not found in Agent class",
        "actual_signature": null,
        "suggestions": [
          "No direct equivalent found in Agent class",
          "Consider using configuration parameters in Agent constructor",
          "Review Agent class documentation for memory management options"
        ]
      },
      {
        "type": "method_call", 
        "element_name": "run_with_context",
        "line_number": 25,
        "confidence": 0.25,
        "severity": "high",
        "description": "Method 'run_with_context' not found in Agent class",
        "actual_signature": "run(user_prompt: str, message_history: list = None) -> RunResult",
        "suggestions": [
          "Use 'run()' method instead",
          "Pass context through system_prompt or message_history",
          "Example: await agent.run('Hello', message_history=context)"
        ]
      }
    ],
    "warnings": [
      {
        "type": "parameter",
        "element_name": "custom_validation",
        "line_number": 12,
        "confidence": 0.4,
        "severity": "medium",
        "description": "Parameter 'custom_validation' not found in Agent constructor",
        "actual_parameters": ["model", "system_prompt", "retries", "result_type"],
        "suggestions": [
          "Remove unknown parameter 'custom_validation'",
          "Use 'result_type' for result validation",
          "Consider implementing validation in system_prompt"
        ]
      },
      {
        "type": "parameter",
        "element_name": "memory_enabled",
        "line_number": 13,
        "confidence": 0.3,
        "severity": "medium", 
        "description": "Parameter 'memory_enabled' not found in Agent constructor",
        "suggestions": [
          "Remove unknown parameter 'memory_enabled'",
          "Memory management is handled automatically by the Agent",
          "Use message_history parameter in run() method for conversation memory"
        ]
      },
      {
        "type": "attribute_access",
        "element_name": "confidence_score",
        "line_number": 31,
        "confidence": 0.35,
        "severity": "medium",
        "description": "Attribute 'confidence_score' not found in result.metadata",
        "actual_attributes": ["usage", "cost", "model_name", "timestamp"],
        "suggestions": [
          "Use 'result.usage' for token usage information",
          "Use 'result.cost' for API cost information",
          "Confidence scoring not available in current API"
        ]
      }
    ]
  },
  "neo4j_validation": {
    "repositories_checked": ["pydantic-ai"],
    "classes_validated": 2,
    "methods_validated": 4,
    "validation_time_ms": 145,
    "confidence": 0.68
  },
  "qdrant_validation": {
    "semantic_searches": 5,
    "patterns_found": 12,
    "similar_examples": 8,
    "validation_time_ms": 89,
    "confidence": 0.42
  },
  "code_suggestions": [
    {
      "original_line": 12,
      "original_code": "agent = Agent(\n    model='openai:gpt-4',\n    temperature=0.7,\n    max_retries=3,\n    custom_validation=True,\n    memory_enabled=True\n)",
      "suggested_code": "agent = Agent(\n    'openai:gpt-4',\n    system_prompt='You are a helpful assistant.',\n    retries=3\n)",
      "confidence": 0.92,
      "source_example": "pydantic-ai/examples/basic_agent.py:15",
      "reasoning": "Removed non-existent parameters and used valid constructor signature"
    },
    {
      "original_line": 25,
      "original_code": "result = await agent.run_with_context(\n    prompt=\"Hello\",\n    context_window=4000,\n    validation_mode=\"strict\"\n)",
      "suggested_code": "result = await agent.run(\"Hello\")",
      "confidence": 0.89,
      "source_example": "pydantic-ai/tests/test_agent.py:45",
      "reasoning": "Used correct method signature from actual Agent class"
    }
  ],
  "corrected_script": "# Automatically corrected version\nfrom pydantic_ai import Agent, ModelError\n\ndef create_advanced_agent():\n    agent = Agent(\n        'openai:gpt-4',\n        system_prompt='You are a helpful assistant.',\n        retries=3\n    )\n    return agent\n\nasync def run_agent_with_validation():\n    agent = create_advanced_agent() \n    result = await agent.run('Hello')\n    usage_info = result.usage  # Use actual available attribute\n    return result, usage_info",
  "performance_metrics": {
    "total_analysis_time_ms": 456,
    "ast_parsing_time_ms": 23,
    "neo4j_validation_time_ms": 145,
    "qdrant_validation_time_ms": 89,
    "suggestion_generation_time_ms": 199
  }
}
```

### Example 3: Multiple Repository Analysis

This example shows how to work with multiple repositories for comprehensive code analysis.

#### Index Multiple Repositories

```bash
# Index FastAPI for web framework patterns
curl -X POST "http://localhost:8051/parse_github_repository" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/tiangolo/fastapi.git"}'

# Index SQLAlchemy for database patterns  
curl -X POST "http://localhost:8051/parse_github_repository" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/sqlalchemy/sqlalchemy.git"}'

# Extract and index code from both repositories
curl -X POST "http://localhost:8051/extract_and_index_repository_code" \
  -H "Content-Type: application/json" \
  -d '{"repo_name": "fastapi"}'

curl -X POST "http://localhost:8051/extract_and_index_repository_code" \
  -H "Content-Type: application/json" \
  -d '{"repo_name": "sqlalchemy"}'
```

#### Cross-Repository Search

```bash
# Search across multiple repositories for async database patterns
curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "async database connection with dependency injection",
    "match_count": 5,
    "min_confidence": 0.6,
    "validation_mode": "thorough",
    "include_suggestions": true
  }'
```

**Example Response (Cross-Repository Results):**

```json
{
  "success": true,
  "query": "async database connection with dependency injection",
  "total_results": 5,
  "repositories_searched": ["fastapi", "sqlalchemy", "pydantic-ai"],
  "results": [
    {
      "code_example": "@app.get(\"/users/{user_id}\")\nasync def get_user(user_id: int, db: AsyncSession = Depends(get_db)):\n    result = await db.execute(select(User).where(User.id == user_id))\n    return result.scalar_one_or_none()",
      "summary": "FastAPI endpoint with async database dependency",
      "similarity_score": 0.96,
      "validation": {
        "confidence_score": 0.91,
        "cross_repository_validation": true
      },
      "metadata": {
        "repository_name": "fastapi",
        "file_path": "examples/async_sql.py",
        "patterns_found": ["dependency_injection", "async_database", "sqlalchemy_async"]
      }
    },
    {
      "code_example": "async def get_db() -> AsyncGenerator[AsyncSession, None]:\n    async with async_session_maker() as session:\n        yield session",
      "summary": "Database session dependency factory",
      "similarity_score": 0.88,
      "validation": {
        "confidence_score": 0.84
      },
      "metadata": {
        "repository_name": "sqlalchemy",
        "file_path": "examples/asyncio/basic.py"
      }
    }
  ]
}
```

### Example 4: Performance Optimization Workflow

This example demonstrates monitoring and optimizing search performance.

#### Monitor System Health

```bash
# Check overall integration health
curl -X GET "http://localhost:8051/health" \
  -H "Content-Type: application/json"
```

**Example Response:**

```json
{
  "status": "healthy",
  "components": {
    "neo4j": {
      "status": "healthy",
      "response_time_ms": 12,
      "connection_pool": "active",
      "last_check": "2024-01-15T10:30:00Z"
    },
    "qdrant": {
      "status": "healthy",
      "response_time_ms": 8,
      "collections": 3,
      "total_points": 1247,
      "last_check": "2024-01-15T10:30:00Z"
    },
    "integration_layer": {
      "status": "optimal",
      "cache_hit_rate": 0.82,
      "avg_confidence": 0.76,
      "avg_response_time_ms": 156
    }
  },
  "performance_stats": {
    "total_searches": 1234,
    "successful_validations": 1189,
    "average_confidence": 0.76,
    "cache_statistics": {
      "hit_rate": 0.82,
      "size": 892,
      "evictions": 45,
      "memory_usage_mb": 48
    }
  }
}
```

#### Performance Testing with Different Modes

```bash
# Test fast mode performance
time curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "create API endpoint with authentication",
    "validation_mode": "fast",
    "match_count": 3
  }'

# Test thorough mode performance  
time curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "create API endpoint with authentication", 
    "validation_mode": "thorough",
    "match_count": 3
  }'
```

**Performance Comparison:**

```
Fast Mode:    ~150ms (confidence: 0.65-0.80)
Balanced Mode: ~300ms (confidence: 0.70-0.85) 
Thorough Mode: ~800ms (confidence: 0.75-0.90)
```

### Example 5: Advanced Search Patterns

This example shows advanced search techniques and filtering options.

#### Repository-Specific Expertise Search

```bash
# Find authentication patterns specifically in FastAPI
curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "JWT token authentication middleware",
    "source_filter": "fastapi",
    "match_count": 3,
    "min_confidence": 0.7,
    "validation_mode": "balanced"
  }'
```

#### Pattern-Based Search with High Confidence

```bash
# Search for database migration patterns with high confidence threshold
curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "database schema migration with version control",
    "source_filter": "sqlalchemy",
    "match_count": 5,
    "min_confidence": 0.85,
    "validation_mode": "thorough",
    "include_suggestions": true
  }'
```

#### Error Handling Pattern Search

```bash
# Find comprehensive error handling patterns
curl -X POST "http://localhost:8051/smart_code_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "async function with comprehensive error handling and logging",
    "match_count": 4,
    "min_confidence": 0.6,
    "validation_mode": "balanced"
  }'
```

### Example 6: Integration Testing Workflow

This example demonstrates testing the complete integration pipeline.

#### Comprehensive Integration Test

```python
# integration_test.py
import asyncio
import aiohttp
import json

async def test_complete_workflow():
    """Test complete Neo4j-Qdrant integration workflow"""
    base_url = "http://localhost:8051"
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Parse repository
        print("1. Parsing repository...")
        async with session.post(
            f"{base_url}/parse_github_repository",
            json={"repo_url": "https://github.com/pydantic/pydantic-ai.git"}
        ) as response:
            parse_result = await response.json()
            print(f"   Repository parsed: {parse_result['success']}")
            print(f"   Classes found: {parse_result['parsing_summary']['classes_found']}")
        
        # Step 2: Extract and index code
        print("2. Extracting and indexing code...")
        async with session.post(
            f"{base_url}/extract_and_index_repository_code",
            json={"repo_name": "pydantic-ai"}
        ) as response:
            index_result = await response.json()
            print(f"   Indexing successful: {index_result['success']}")
            print(f"   Examples indexed: {index_result['indexed_count']}")
        
        # Step 3: Test validated search
        print("3. Testing validated search...")
        search_queries = [
            "create AI agent with OpenAI",
            "async function error handling", 
            "pydantic model validation"
        ]
        
        for query in search_queries:
            async with session.post(
                f"{base_url}/smart_code_search",
                json={
                    "query": query,
                    "source_filter": "pydantic-ai",
                    "match_count": 2,
                    "min_confidence": 0.6,
                    "validation_mode": "balanced"
                }
            ) as response:
                search_result = await response.json()
                print(f"   Query: '{query}'")
                print(f"   Results: {search_result['total_results']}")
                print(f"   Avg confidence: {np.mean([r['validation']['confidence_score'] for r in search_result['results']]):.2f}")
        
        # Step 4: Test hallucination detection
        print("4. Testing hallucination detection...")
        test_script = '''
from pydantic_ai import Agent

agent = Agent('openai:gpt-4')
result = agent.run_with_validation('test', strict_mode=True)  # Potential hallucination
        '''
        
        with open('/tmp/test_script.py', 'w') as f:
            f.write(test_script)
        
        async with session.post(
            f"{base_url}/check_ai_script_hallucinations_enhanced",
            json={
                "script_path": "/tmp/test_script.py",
                "include_code_suggestions": True
            }
        ) as response:
            hallucination_result = await response.json()
            print(f"   Hallucinations detected: {len(hallucination_result['hallucinations']['warnings']) + len(hallucination_result['hallucinations']['critical'])}")
            print(f"   Overall confidence: {hallucination_result['overall_assessment']['confidence_score']:.2f}")
        
        # Step 5: Check system health
        print("5. Checking system health...")
        async with session.get(f"{base_url}/health") as response:
            health_result = await response.json()
            print(f"   Overall status: {health_result['status']}")
            print(f"   Neo4j: {health_result['components']['neo4j']['status']}")
            print(f"   Qdrant: {health_result['components']['qdrant']['status']}")
            print(f"   Cache hit rate: {health_result['performance_stats']['cache_statistics']['hit_rate']:.2%}")

# Run the test
if __name__ == "__main__":
    asyncio.run(test_complete_workflow())
```

#### Run Integration Test

```bash
python integration_test.py
```

**Expected Output:**

```
1. Parsing repository...
   Repository parsed: True
   Classes found: 12

2. Extracting and indexing code...
   Indexing successful: True
   Examples indexed: 124

3. Testing validated search...
   Query: 'create AI agent with OpenAI'
   Results: 2
   Avg confidence: 0.87
   
   Query: 'async function error handling'
   Results: 2
   Avg confidence: 0.73
   
   Query: 'pydantic model validation'
   Results: 2
   Avg confidence: 0.79

4. Testing hallucination detection...
   Hallucinations detected: 2
   Overall confidence: 0.42

5. Checking system health...
   Overall status: healthy
   Neo4j: healthy
   Qdrant: healthy
   Cache hit rate: 84%
```

## Practical Development Scenarios

### Scenario 1: Code Review Assistant

Use the integration to validate code during review:

```python
# validate_pr.py - Code review validation script
import os
import glob
import asyncio
import aiohttp

async def validate_python_files(directory: str):
    """Validate all Python files in a directory for potential hallucinations"""
    base_url = "http://localhost:8051"
    
    python_files = glob.glob(f"{directory}/**/*.py", recursive=True)
    results = []
    
    async with aiohttp.ClientSession() as session:
        for file_path in python_files:
            if os.path.getsize(file_path) > 100:  # Skip very small files
                async with session.post(
                    f"{base_url}/check_ai_script_hallucinations_enhanced",
                    json={
                        "script_path": file_path,
                        "include_code_suggestions": True,
                        "detailed_analysis": False
                    }
                ) as response:
                    result = await response.json()
                    if result.get('success') and result['overall_assessment']['confidence_score'] < 0.7:
                        results.append({
                            'file': file_path,
                            'confidence': result['overall_assessment']['confidence_score'],
                            'issues': len(result['hallucinations']['critical']) + len(result['hallucinations']['warnings'])
                        })
    
    # Sort by confidence (lowest first)
    results.sort(key=lambda x: x['confidence'])
    
    print("Code Review Results:")
    print("===================")
    for result in results:
        print(f"⚠️  {result['file']}")
        print(f"    Confidence: {result['confidence']:.2f}")
        print(f"    Issues: {result['issues']}")
        print()

# Usage
# asyncio.run(validate_python_files("./src"))
```

### Scenario 2: Learning Assistant

Use the integration to help developers learn new libraries:

```python
# learning_assistant.py
async def explore_library_patterns(library_name: str, topic: str):
    """Help developers learn library patterns through validated examples"""
    
    base_url = "http://localhost:8051"
    
    # Search for patterns in the library
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/smart_code_search",
            json={
                "query": f"{topic} in {library_name}",
                "source_filter": library_name,
                "match_count": 5,
                "min_confidence": 0.7,
                "validation_mode": "balanced",
                "include_suggestions": True
            }
        ) as response:
            search_result = await response.json()
    
    if search_result['success']:
        print(f"Learning {topic} in {library_name}")
        print("=" * 50)
        
        for i, result in enumerate(search_result['results'], 1):
            print(f"\n{i}. {result['summary']}")
            print(f"   Confidence: {result['validation']['confidence_score']:.2f}")
            print(f"   Location: {result['metadata']['file_path']}")
            print(f"   Code Example:")
            print("   " + result['code_example'].replace('\n', '\n   '))
            
            if result.get('suggestions'):
                print(f"   💡 Suggestions:")
                for suggestion in result['suggestions']:
                    print(f"      • {suggestion}")

# Usage examples:
# asyncio.run(explore_library_patterns("fastapi", "authentication middleware"))
# asyncio.run(explore_library_patterns("sqlalchemy", "async database queries"))
# asyncio.run(explore_library_patterns("pydantic-ai", "agent creation"))
```

### Scenario 3: Code Generation Validation

Validate AI-generated code in real-time:

```python
# code_gen_validator.py
class CodeGenerationValidator:
    def __init__(self, base_url="http://localhost:8051"):
        self.base_url = base_url
    
    async def validate_generated_code(self, code: str, context: str = ""):
        """Validate AI-generated code snippet"""
        
        # Save code to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/check_ai_script_hallucinations_enhanced",
                    json={
                        "script_path": temp_path,
                        "include_code_suggestions": True,
                        "detailed_analysis": True
                    }
                ) as response:
                    result = await response.json()
            
            validation_summary = {
                'confidence': result['overall_assessment']['confidence_score'],
                'risk_level': result['overall_assessment']['risk_level'],
                'issues': result['overall_assessment']['potential_hallucinations'],
                'suggestions': []
            }
            
            # Extract suggestions
            for suggestion in result.get('code_suggestions', []):
                validation_summary['suggestions'].append({
                    'original': suggestion['original_code'],
                    'suggested': suggestion['suggested_code'],
                    'confidence': suggestion['confidence'],
                    'reasoning': suggestion['reasoning']
                })
            
            return validation_summary
            
        finally:
            os.unlink(temp_path)
    
    async def search_similar_patterns(self, description: str, library: str = None):
        """Find similar code patterns for reference"""
        
        async with aiohttp.ClientSession() as session:
            search_params = {
                "query": description,
                "match_count": 3,
                "min_confidence": 0.6,
                "validation_mode": "fast",
                "include_suggestions": True
            }
            
            if library:
                search_params["source_filter"] = library
            
            async with session.post(
                f"{self.base_url}/smart_code_search",
                json=search_params
            ) as response:
                result = await response.json()
        
        return result.get('results', [])

# Usage example:
# validator = CodeGenerationValidator()
# 
# generated_code = """
# from fastapi import FastAPI
# app = FastAPI()
# 
# @app.get("/users")
# async def get_users(db: Database = Depends(get_database)):
#     return await db.fetch_users_with_pagination(limit=100)
# """
# 
# validation = await validator.validate_generated_code(generated_code)
# similar_patterns = await validator.search_similar_patterns("FastAPI database pagination", "fastapi")
```

These comprehensive examples demonstrate the full capabilities of the Neo4j-Qdrant integration, from basic setup to advanced validation workflows. The integration provides powerful tools for ensuring AI-generated code quality and learning from validated real-world examples.
