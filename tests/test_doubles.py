"""Test doubles to replace complex mocks."""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class FakeQdrantClient:
    """Fake Qdrant client for testing."""
    collections: Dict[str, List[Dict]] = field(default_factory=dict)
    search_results: List[Dict] = field(default_factory=list)
    should_fail: bool = False
    
    def search(self, collection_name: str, query_vector: List[float], limit: int = 10):
        if self.should_fail:
            raise Exception("Search failed")
        return self.search_results[:limit]
    
    def upsert(self, collection_name: str, points: List[Dict]):
        if self.should_fail:
            raise Exception("Upsert failed")
        if collection_name not in self.collections:
            self.collections[collection_name] = []
        self.collections[collection_name].extend(points)
        return {"status": "ok"}
    
    def delete(self, collection_name: str, points_selector: Dict):
        if self.should_fail:
            raise Exception("Delete failed")
        # Simple implementation
        return {"status": "ok"}

@dataclass 
class FakeEmbeddingService:
    """Fake embedding service for testing."""
    embedding_dim: int = 1536
    should_fail: bool = False
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        if self.should_fail:
            raise Exception("Embedding creation failed")
        # Return consistent fake embeddings
        return [[0.1] * self.embedding_dim for _ in texts]

@dataclass
class FakeCrawler:
    """Fake web crawler for testing."""
    responses: Dict[str, str] = field(default_factory=dict)
    should_fail: bool = False
    default_content: str = "<html><body>Test content</body></html>"
    
    async def arun(self, url: str, **kwargs):
        if self.should_fail:
            raise Exception(f"Failed to crawl {url}")
        
        content = self.responses.get(url, self.default_content)
        return type('CrawlResult', (), {
            'html': content,
            'success': True,
            'cleaned_html': content,
            'media': {'images': [], 'videos': []},
            'links': {'internal': [], 'external': []},
            'screenshot': None,
            'pdf': None,
            'markdown': content.replace('<[^>]+>', ''),  # Simple HTML strip
            'failed_before': False
        })

@dataclass
class FakeSupabaseClient:
    """Fake Supabase client for testing."""
    data: Dict[str, List[Dict]] = field(default_factory=dict)
    rpc_results: Dict[str, Any] = field(default_factory=dict)
    should_fail: bool = False
    
    def __init__(self):
        self.data = {}
        self.rpc_results = {}
        self.should_fail = False
        self._table_name = None
        self._operation = None
        self._filters = []
    
    def table(self, name: str):
        """Start a table operation."""
        self._table_name = name
        self._operation = None
        self._filters = []
        return self
    
    def insert(self, data: List[Dict]):
        """Insert operation."""
        self._operation = ('insert', data)
        return self
    
    def delete(self):
        """Delete operation."""
        self._operation = ('delete', None)
        return self
    
    def select(self, columns: str = "*"):
        """Select operation."""
        self._operation = ('select', columns)
        return self
    
    def update(self, data: Dict):
        """Update operation."""
        self._operation = ('update', data)
        return self
    
    def eq(self, column: str, value: Any):
        """Equal filter."""
        self._filters.append(('eq', column, value))
        return self
    
    def in_(self, column: str, values: List):
        """In filter."""
        self._filters.append(('in', column, values))
        return self
    
    def execute(self):
        """Execute the operation."""
        if self.should_fail:
            raise Exception("Operation failed")
        
        if self._operation is None:
            return type('Response', (), {'data': []})
        
        op_type, op_data = self._operation
        
        if op_type == 'insert':
            if self._table_name not in self.data:
                self.data[self._table_name] = []
            self.data[self._table_name].extend(op_data)
            return type('Response', (), {'data': op_data})
        
        elif op_type == 'select':
            table_data = self.data.get(self._table_name, [])
            # Apply filters
            for filter_type, column, value in self._filters:
                if filter_type == 'eq':
                    table_data = [row for row in table_data if row.get(column) == value]
                elif filter_type == 'in':
                    table_data = [row for row in table_data if row.get(column) in value]
            return type('Response', (), {'data': table_data})
        
        elif op_type == 'delete':
            if self._table_name in self.data:
                # Apply filters to determine what to delete
                for filter_type, column, value in self._filters:
                    if filter_type == 'in':
                        self.data[self._table_name] = [
                            row for row in self.data[self._table_name] 
                            if row.get(column) not in value
                        ]
            return type('Response', (), {'data': []})
        
        elif op_type == 'update':
            table_data = self.data.get(self._table_name, [])
            updated = []
            for row in table_data:
                for filter_type, column, value in self._filters:
                    if filter_type == 'eq' and row.get(column) == value:
                        row.update(op_data)
                        updated.append(row)
            return type('Response', (), {'data': updated})
        
        return type('Response', (), {'data': []})
    
    def rpc(self, function_name: str, params: Dict):
        """RPC call."""
        if self.should_fail:
            raise Exception(f"RPC {function_name} failed")
        
        result = self.rpc_results.get(function_name, [])
        return type('RPCResponse', (), {
            'execute': lambda: type('Response', (), {'data': result})
        })

# Example usage in tests
def test_with_fake_client():
    # Setup
    fake_client = FakeQdrantClient(
        search_results=[
            {"id": "1", "score": 0.9, "payload": {"content": "Test 1"}},
            {"id": "2", "score": 0.8, "payload": {"content": "Test 2"}}
        ]
    )
    
    # Test
    results = fake_client.search("test_collection", [0.1] * 1536, limit=1)
    assert len(results) == 1
    assert results[0]["score"] == 0.9
    
    # Test failure
    fake_client.should_fail = True
    try:
        fake_client.search("test_collection", [0.1] * 1536)
    except Exception as e:
        assert str(e) == "Search failed"