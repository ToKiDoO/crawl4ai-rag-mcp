"""Test data factories for consistent test data generation."""
from typing import Dict, List, Any, Optional
import random
import string
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json

@dataclass
class TestDocument:
    """Test document model."""
    url: str
    content: str
    embedding: List[float]
    chunk_number: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

class DocumentFactory:
    """Factory for generating test documents."""
    
    @staticmethod
    def _random_text(min_words: int = 10, max_words: int = 50) -> str:
        """Generate random text content."""
        words = [
            "machine", "learning", "artificial", "intelligence", "neural",
            "network", "algorithm", "data", "science", "model", "training",
            "prediction", "classification", "regression", "clustering"
        ]
        num_words = random.randint(min_words, max_words)
        return " ".join(random.choices(words, k=num_words))
    
    @staticmethod
    def _random_url() -> str:
        """Generate random URL."""
        domains = ["example.com", "test.org", "demo.net", "sample.io"]
        paths = ["docs", "articles", "posts", "pages", "content"]
        return f"https://{random.choice(domains)}/{random.choice(paths)}/{random.randint(1, 1000)}"
    
    @staticmethod
    def _random_embedding(dim: int = 1536) -> List[float]:
        """Generate random embedding vector."""
        # Create somewhat realistic embeddings (normalized)
        embedding = [random.gauss(0, 0.5) for _ in range(dim)]
        # Normalize
        norm = sum(x**2 for x in embedding) ** 0.5
        return [x / norm for x in embedding] if norm > 0 else embedding
    
    @classmethod
    def create(
        cls,
        url: Optional[str] = None,
        content: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        chunk_number: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> TestDocument:
        """Create a single test document."""
        return TestDocument(
            url=url or cls._random_url(),
            content=content or cls._random_text(),
            embedding=embedding or cls._random_embedding(),
            chunk_number=chunk_number,
            metadata=metadata or {
                "source": "test",
                "category": random.choice(["tech", "science", "news"]),
                "timestamp": datetime.now().isoformat()
            },
            **kwargs
        )
    
    @classmethod
    def create_batch(cls, count: int = 10, **kwargs) -> List[TestDocument]:
        """Create a batch of test documents."""
        return [cls.create(**kwargs) for _ in range(count)]
    
    @classmethod
    def create_with_similarity(
        cls,
        base_document: TestDocument,
        similarity: float = 0.8,
        count: int = 5
    ) -> List[TestDocument]:
        """Create documents similar to a base document."""
        similar_docs = []
        
        for i in range(count):
            # Vary embedding slightly based on similarity
            new_embedding = [
                e + random.gauss(0, (1 - similarity) * 0.1)
                for e in base_document.embedding
            ]
            
            # Modify content slightly
            words = base_document.content.split()
            num_changes = int(len(words) * (1 - similarity))
            for _ in range(num_changes):
                if words:
                    idx = random.randint(0, len(words) - 1)
                    words[idx] = cls._random_text(1, 1).split()[0]
            
            similar_docs.append(cls.create(
                url=f"{base_document.url}/similar-{i}",
                content=" ".join(words),
                embedding=new_embedding,
                metadata={**base_document.metadata, "similarity": similarity}
            ))
        
        return similar_docs

class CodeExampleFactory:
    """Factory for generating test code examples."""
    
    SAMPLE_CODE = {
        "python": [
            "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)",
            "class Stack:\n    def __init__(self):\n        self.items = []",
            "async def fetch_data(url):\n    async with aiohttp.ClientSession() as session:\n        return await session.get(url)"
        ],
        "javascript": [
            "const sum = (a, b) => a + b;",
            "function debounce(func, wait) {\n    let timeout;\n    return function(...args) {\n        clearTimeout(timeout);\n        timeout = setTimeout(() => func.apply(this, args), wait);\n    };\n}",
            "class EventEmitter {\n    constructor() {\n        this.events = {};\n    }\n}"
        ],
        "sql": [
            "SELECT * FROM users WHERE age > 18 ORDER BY created_at DESC;",
            "CREATE INDEX idx_user_email ON users(email);",
            "INSERT INTO logs (user_id, action) VALUES (?, ?);"
        ]
    }
    
    @classmethod
    def create(
        cls,
        language: Optional[str] = None,
        code: Optional[str] = None,
        description: Optional[str] = None,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a test code example."""
        lang = language or random.choice(list(cls.SAMPLE_CODE.keys()))
        
        return {
            "language": lang,
            "code": code or random.choice(cls.SAMPLE_CODE.get(lang, ["print('Hello')"])),
            "description": description or f"Example {lang} code",
            "url": url or f"https://example.com/code/{random.randint(1, 100)}",
            "embedding": DocumentFactory._random_embedding()
        }

class QueryFactory:
    """Factory for generating test queries."""
    
    SAMPLE_QUERIES = [
        "How does machine learning work?",
        "What are neural networks?",
        "Explain the difference between supervised and unsupervised learning",
        "Best practices for Python programming",
        "How to optimize database queries",
        "What is artificial intelligence?",
        "How to implement a REST API",
        "Explain microservices architecture"
    ]
    
    @classmethod
    def create(cls, query: Optional[str] = None) -> Dict[str, Any]:
        """Create a test query."""
        return {
            "query": query or random.choice(cls.SAMPLE_QUERIES),
            "embedding": DocumentFactory._random_embedding(),
            "metadata": {
                "source": "test",
                "timestamp": datetime.now().isoformat()
            }
        }
    
    @classmethod
    def create_batch(cls, count: int = 5) -> List[Dict[str, Any]]:
        """Create a batch of test queries."""
        return [cls.create() for _ in range(count)]

# Test data sets for specific scenarios
class TestDataSets:
    """Pre-defined test data sets for common scenarios."""
    
    @staticmethod
    def ml_tutorial_set() -> List[TestDocument]:
        """Machine learning tutorial documents."""
        topics = [
            ("Introduction to ML", "Basic concepts of machine learning including supervised and unsupervised learning"),
            ("Neural Networks", "Deep dive into artificial neural networks and deep learning"),
            ("Linear Regression", "Understanding linear regression for predictive modeling"),
            ("Classification", "Binary and multiclass classification algorithms"),
            ("Clustering", "K-means and hierarchical clustering techniques")
        ]
        
        docs = []
        for i, (title, content) in enumerate(topics):
            docs.append(DocumentFactory.create(
                url=f"https://ml-tutorial.com/lesson-{i+1}",
                content=f"{title}: {content}",
                metadata={"title": title, "lesson": i+1, "category": "tutorial"}
            ))
        
        return docs
    
    @staticmethod
    def code_examples_set() -> List[Dict[str, Any]]:
        """Programming code examples."""
        return [
            CodeExampleFactory.create("python"),
            CodeExampleFactory.create("javascript"),
            CodeExampleFactory.create("sql"),
        ]

if __name__ == "__main__":
    # Example usage
    doc = DocumentFactory.create()
    print(f"Created document: {doc.url}")
    
    # Create similar documents
    similar = DocumentFactory.create_with_similarity(doc, similarity=0.9)
    print(f"Created {len(similar)} similar documents")
    
    # Create ML tutorial set
    ml_docs = TestDataSets.ml_tutorial_set()
    print(f"Created {len(ml_docs)} ML tutorial documents")