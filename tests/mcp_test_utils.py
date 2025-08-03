"""
MCP test utilities for simulating client requests and validating responses.
"""
import json
import asyncio
import sys
import subprocess
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from unittest.mock import Mock, AsyncMock
import os


@dataclass
class MCPRequest:
    """Represents an MCP JSON-RPC request"""
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    
    def to_json(self) -> str:
        """Convert to JSON-RPC format"""
        request = {
            "jsonrpc": "2.0",
            "method": self.method,
            "id": self.id or 1
        }
        if self.params:
            request["params"] = self.params
        return json.dumps(request)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        request = {
            "jsonrpc": "2.0", 
            "method": self.method,
            "id": self.id or 1
        }
        if self.params:
            request["params"] = self.params
        return request


@dataclass
class MCPResponse:
    """Represents an MCP JSON-RPC response"""
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPResponse':
        """Parse JSON-RPC response"""
        data = json.loads(json_str)
        return cls(
            result=data.get('result'),
            error=data.get('error'),
            id=data.get('id')
        )
    
    def is_success(self) -> bool:
        """Check if response is successful"""
        return self.error is None and self.result is not None
    
    def is_error(self) -> bool:
        """Check if response is an error"""
        return self.error is not None


class MCPTestClient:
    """Test client for simulating MCP requests"""
    
    def __init__(self):
        self.request_id = 0
        
    def create_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> MCPRequest:
        """Create a new MCP request"""
        self.request_id += 1
        return MCPRequest(method=method, params=params, id=self.request_id)
    
    def create_tool_discovery_request(self) -> MCPRequest:
        """Create a tool discovery request"""
        return self.create_request("tools/list")
    
    def create_tool_call_request(self, tool_name: str, arguments: Dict[str, Any]) -> MCPRequest:
        """Create a tool call request"""
        return self.create_request(
            "tools/call",
            params={
                "name": tool_name,
                "arguments": arguments
            }
        )
    
    async def send_stdio_request(self, request: MCPRequest, 
                                 server_command: List[str]) -> MCPResponse:
        """Send request via stdio transport"""
        # Start MCP server process
        process = await asyncio.create_subprocess_exec(
            *server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Send request
        request_json = request.to_json() + "\n"
        process.stdin.write(request_json.encode())
        await process.stdin.drain()
        
        # Read response
        response_line = await process.stdout.readline()
        response_json = response_line.decode().strip()
        
        # Clean up
        process.terminate()
        await process.wait()
        
        return MCPResponse.from_json(response_json)


class MCPValidator:
    """Validates MCP protocol compliance"""
    
    @staticmethod
    def validate_tool_list_response(response: Dict[str, Any]) -> List[str]:
        """Validate tool list response format"""
        errors = []
        
        # Check basic structure
        if 'tools' not in response:
            errors.append("Missing 'tools' field in response")
            return errors
        
        tools = response['tools']
        if not isinstance(tools, list):
            errors.append("'tools' field must be an array")
            return errors
        
        # Validate each tool
        for i, tool in enumerate(tools):
            if not isinstance(tool, dict):
                errors.append(f"Tool {i} must be an object")
                continue
                
            # Required fields
            if 'name' not in tool:
                errors.append(f"Tool {i} missing 'name' field")
            elif not isinstance(tool['name'], str):
                errors.append(f"Tool {i} 'name' must be string")
                
            if 'description' not in tool:
                errors.append(f"Tool {i} missing 'description' field")
            elif not isinstance(tool['description'], str):
                errors.append(f"Tool {i} 'description' must be string")
                
            # Optional but recommended
            if 'inputSchema' in tool and not isinstance(tool['inputSchema'], dict):
                errors.append(f"Tool {i} 'inputSchema' must be object")
        
        return errors
    
    @staticmethod
    def validate_error_response(response: Dict[str, Any]) -> List[str]:
        """Validate error response format"""
        errors = []
        
        if 'error' not in response:
            errors.append("Error response missing 'error' field")
            return errors
            
        error = response['error']
        if not isinstance(error, dict):
            errors.append("'error' field must be object")
            return errors
            
        # Required error fields
        if 'code' not in error:
            errors.append("Error missing 'code' field")
        elif not isinstance(error['code'], int):
            errors.append("Error 'code' must be integer")
            
        if 'message' not in error:
            errors.append("Error missing 'message' field")
        elif not isinstance(error['message'], str):
            errors.append("Error 'message' must be string")
            
        return errors
    
    @staticmethod
    def validate_parameter_schema(schema: Dict[str, Any]) -> List[str]:
        """Validate parameter schema structure"""
        errors = []
        
        if 'type' not in schema:
            errors.append("Schema missing 'type' field")
            
        if 'properties' in schema:
            if not isinstance(schema['properties'], dict):
                errors.append("'properties' must be object")
            else:
                # Validate each property
                for prop_name, prop_schema in schema['properties'].items():
                    if 'type' not in prop_schema and 'oneOf' not in prop_schema:
                        errors.append(f"Property '{prop_name}' missing type definition")
                        
        if 'required' in schema and not isinstance(schema['required'], list):
            errors.append("'required' field must be array")
            
        return errors


class MockMCPServer:
    """Mock MCP server for testing"""
    
    def __init__(self):
        self.tools = {}
        self.handlers = {}
        
    def add_tool(self, name: str, description: str, 
                 input_schema: Dict[str, Any],
                 handler: Optional[Any] = None):
        """Add a tool to the mock server"""
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema
        }
        if handler:
            self.handlers[name] = handler
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle an MCP request"""
        if request.method == "tools/list":
            return MCPResponse(
                result={"tools": list(self.tools.values())},
                id=request.id
            )
        elif request.method == "tools/call":
            tool_name = request.params.get("name")
            if tool_name not in self.tools:
                return MCPResponse(
                    error={
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    },
                    id=request.id
                )
            
            # Call handler if available
            if tool_name in self.handlers:
                try:
                    handler = self.handlers[tool_name]
                    arguments = request.params.get("arguments", {})
                    result = await handler(**arguments) if asyncio.iscoroutinefunction(handler) else handler(**arguments)
                    return MCPResponse(result=result, id=request.id)
                except Exception as e:
                    return MCPResponse(
                        error={
                            "code": -32603,
                            "message": str(e)
                        },
                        id=request.id
                    )
            else:
                return MCPResponse(result="Mock result", id=request.id)
        else:
            return MCPResponse(
                error={
                    "code": -32601,
                    "message": f"Unknown method: {request.method}"
                },
                id=request.id
            )


def create_test_context(crawler=None, database_client=None, reranking_model=None):
    """Create a test context for MCP tools"""
    from crawl4ai_mcp import Crawl4AIContext
    
    ctx = Mock()
    ctx.request_context = Mock()
    ctx.request_context.session_id = "test-session"
    ctx.request_context.meta = {}
    ctx.request_context.lifespan_context = Crawl4AIContext(
        crawler=crawler or AsyncMock(),
        database_client=database_client or AsyncMock(),
        reranking_model=reranking_model,
        knowledge_validator=None,
        repo_extractor=None
    )
    return ctx


async def test_tool_directly(tool_name: str, arguments: Dict[str, Any]):
    """Test an MCP tool directly without JSON-RPC layer"""
    from crawl4ai_mcp import mcp
    
    # Get tool handler
    tools = mcp._FastMCP__tools
    if tool_name not in tools:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    handler = tools[tool_name]['handler']
    
    # Create test context
    ctx = create_test_context()
    
    # Call handler
    return await handler(ctx, **arguments)


# Test data generators
def generate_test_urls(count: int = 5) -> List[str]:
    """Generate test URLs"""
    return [f"https://example.com/page{i}" for i in range(1, count + 1)]


def generate_test_markdown(size: str = "small") -> str:
    """Generate test markdown content"""
    if size == "small":
        return "# Test Page\n\nThis is test content."
    elif size == "medium":
        return "# Test Page\n\n" + "This is test content. " * 50
    else:  # large
        return "# Test Page\n\n" + "This is test content. " * 500


def generate_test_embedding(dimensions: int = 1536) -> List[float]:
    """Generate test embedding vector"""
    import random
    return [random.random() for _ in range(dimensions)]