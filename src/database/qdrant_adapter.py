"""
Qdrant adapter implementation for VectorDatabase protocol.
Uses Qdrant vector database for similarity search.
"""
import os
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from uuid import uuid4
import hashlib
from qdrant_client import QdrantClient, models
from qdrant_client.models import (
    VectorParams, Distance, PointStruct, Filter, FieldCondition, 
    MatchValue, Range, PointIdsList
)


class QdrantAdapter:
    """
    Qdrant implementation of the VectorDatabase protocol.
    Uses Qdrant's native vector search capabilities.
    """
    
    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        """Initialize Qdrant adapter with connection parameters"""
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.client: Optional[QdrantClient] = None
        self.batch_size = 100  # Qdrant can handle larger batches
        
        # Collection names
        self.CRAWLED_PAGES = "crawled_pages"
        self.CODE_EXAMPLES = "code_examples"
        self.SOURCES = "sources"
    
    async def initialize(self) -> None:
        """Initialize Qdrant client and create collections if needed"""
        if self.client is None:
            self.client = QdrantClient(url=self.url, api_key=self.api_key)
        
        # Create collections if they don't exist
        await self._ensure_collections()
    
    async def _ensure_collections(self) -> None:
        """Ensure all required collections exist"""
        collections = [
            (self.CRAWLED_PAGES, 1536),  # OpenAI embedding size
            (self.CODE_EXAMPLES, 1536),
            (self.SOURCES, 1536)  # OpenAI embedding size for consistency
        ]
        
        for collection_name, vector_size in collections:
            try:
                self.client.get_collection(collection_name)
            except Exception:
                # Collection doesn't exist, create it
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
                )
    
    def _generate_point_id(self, url: str, chunk_number: int) -> str:
        """Generate a deterministic ID for a document point"""
        id_string = f"{url}_{chunk_number}"
        return hashlib.md5(id_string.encode()).hexdigest()
    
    async def add_documents(
        self,
        urls: List[str],
        chunk_numbers: List[int],
        contents: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: List[List[float]],
        source_ids: List[str]
    ) -> None:
        """Add documents to Qdrant"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        # Delete existing documents first
        await self.delete_documents_by_url(list(set(urls)))
        
        # Process in batches
        for i in range(0, len(contents), self.batch_size):
            batch_end = min(i + self.batch_size, len(contents))
            
            # Create points for this batch
            points = []
            for j in range(i, batch_end):
                # Generate deterministic ID
                point_id = self._generate_point_id(urls[j], chunk_numbers[j])
                
                # Extract source_id
                if j < len(source_ids) and source_ids[j]:
                    source_id = source_ids[j]
                else:
                    parsed_url = urlparse(urls[j])
                    source_id = parsed_url.netloc or parsed_url.path
                
                # Create payload
                payload = {
                    "url": urls[j],
                    "chunk_number": chunk_numbers[j],
                    "content": contents[j],
                    "metadata": metadatas[j] if j < len(metadatas) else {},
                    "source_id": source_id,
                    "chunk_size": len(contents[j])
                }
                
                # Create point
                point = PointStruct(
                    id=point_id,
                    vector=embeddings[j],
                    payload=payload
                )
                points.append(point)
            
            # Upsert batch to Qdrant
            try:
                await self.client.upsert(
                    collection_name=self.CRAWLED_PAGES,
                    points=points
                )
            except Exception as e:
                print(f"Error upserting documents to Qdrant: {e}")
                raise
    
    async def search_documents(
        self,
        query_embedding: List[float],
        match_count: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search documents using vector similarity"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        # Build query filter
        query_filter = self._build_filter(filter_metadata, source_filter)
        
        try:
            # Perform search
            results = await self.client.search(
                collection_name=self.CRAWLED_PAGES,
                query_vector=query_embedding,
                limit=match_count,
                query_filter=query_filter
            )
            
            # Convert results to expected format
            output = []
            for result in results:
                doc = {
                    "id": result.id,
                    "url": result.payload.get("url"),
                    "chunk_number": result.payload.get("chunk_number"),
                    "content": result.payload.get("content"),
                    "metadata": result.payload.get("metadata", {}),
                    "source_id": result.payload.get("source_id"),
                    "similarity": result.score  # Qdrant returns cosine similarity
                }
                output.append(doc)
            
            return output
        except Exception as e:
            print(f"Error searching documents in Qdrant: {e}")
            return []
    
    async def delete_documents_by_url(self, urls: List[str]) -> None:
        """Delete documents by URL"""
        if not self.client or not urls:
            return
        
        try:
            # Search for all points with these URLs
            point_ids = []
            for url in urls:
                # Search for all chunks of this URL
                results = await self.client.search(
                    collection_name=self.CRAWLED_PAGES,
                    query_vector=[0.0] * 1536,  # Dummy vector
                    limit=1000,  # Get all chunks
                    query_filter=Filter(
                        must=[
                            FieldCondition(
                                key="url",
                                match=MatchValue(value=url)
                            )
                        ]
                    )
                )
                
                # Collect point IDs
                for result in results:
                    point_ids.append(result.id)
            
            # Delete all found points
            if point_ids:
                await self.client.delete(
                    collection_name=self.CRAWLED_PAGES,
                    points_selector=point_ids
                )
        except Exception as e:
            print(f"Error deleting documents from Qdrant: {e}")
    
    async def add_code_examples(
        self,
        urls: List[str],
        chunk_numbers: List[int],
        code_examples: List[str],
        summaries: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: List[List[float]],
        source_ids: List[str]
    ) -> None:
        """Add code examples to Qdrant"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        # Delete existing code examples first
        await self.delete_code_examples_by_url(list(set(urls)))
        
        # Process in batches
        for i in range(0, len(code_examples), self.batch_size):
            batch_end = min(i + self.batch_size, len(code_examples))
            
            # Create points for this batch
            points = []
            for j in range(i, batch_end):
                # Generate deterministic ID
                point_id = self._generate_point_id(urls[j], chunk_numbers[j])
                
                # Extract source_id
                parsed_url = urlparse(urls[j])
                source_id = parsed_url.netloc or parsed_url.path
                
                # Create payload
                payload = {
                    "url": urls[j],
                    "chunk_number": chunk_numbers[j],
                    "content": code_examples[j],
                    "summary": summaries[j],
                    "metadata": metadatas[j] if j < len(metadatas) else {},
                    "source_id": source_id
                }
                
                # Create point
                point = PointStruct(
                    id=point_id,
                    vector=embeddings[j],
                    payload=payload
                )
                points.append(point)
            
            # Upsert batch to Qdrant
            try:
                await self.client.upsert(
                    collection_name=self.CODE_EXAMPLES,
                    points=points
                )
            except Exception as e:
                print(f"Error upserting code examples to Qdrant: {e}")
                raise
    
    async def search_code_examples(
        self,
        query_embedding: List[float],
        match_count: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search code examples using vector similarity"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        # Build query filter
        query_filter = self._build_filter(filter_metadata, source_filter)
        
        try:
            # Perform search
            results = await self.client.search(
                collection_name=self.CODE_EXAMPLES,
                query_vector=query_embedding,
                limit=match_count,
                query_filter=query_filter
            )
            
            # Convert results to expected format
            output = []
            for result in results:
                example = {
                    "id": result.id,
                    "url": result.payload.get("url"),
                    "chunk_number": result.payload.get("chunk_number"),
                    "content": result.payload.get("content"),
                    "summary": result.payload.get("summary"),
                    "metadata": result.payload.get("metadata", {}),
                    "source_id": result.payload.get("source_id"),
                    "similarity": result.score
                }
                output.append(example)
            
            return output
        except Exception as e:
            print(f"Error searching code examples in Qdrant: {e}")
            return []
    
    async def delete_code_examples_by_url(self, urls: List[str]) -> None:
        """Delete code examples by URL"""
        if not self.client or not urls:
            return
        
        try:
            # Similar to delete_documents_by_url but for code_examples collection
            point_ids = []
            for url in urls:
                results = await self.client.search(
                    collection_name=self.CODE_EXAMPLES,
                    query_vector=[0.0] * 1536,
                    limit=1000,
                    query_filter=Filter(
                        must=[
                            FieldCondition(
                                key="url",
                                match=MatchValue(value=url)
                            )
                        ]
                    )
                )
                
                for result in results:
                    point_ids.append(result.id)
            
            if point_ids:
                await self.client.delete(
                    collection_name=self.CODE_EXAMPLES,
                    points_selector=point_ids
                )
        except Exception as e:
            print(f"Error deleting code examples from Qdrant: {e}")
    
    async def update_source_info(
        self,
        source_id: str,
        summary: str,
        word_count: int
    ) -> None:
        """Update or create source information"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        try:
            # Use source_id as the point ID
            point = PointStruct(
                id=source_id,
                vector=[0.0, 0.0, 0.0, 0.0],  # Dummy vector for metadata storage
                payload={
                    "source_id": source_id,
                    "summary": summary,
                    "total_word_count": word_count,
                    "updated_at": "now()"  # This is just for compatibility
                }
            )
            
            await self.client.upsert(
                collection_name=self.SOURCES,
                points=[point]
            )
        except Exception as e:
            print(f"Error updating source info in Qdrant: {e}")
    
    async def get_documents_by_url(self, url: str) -> List[Dict[str, Any]]:
        """Get all document chunks for a specific URL"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        try:
            # Search for all documents with matching URL
            results = await self.client.scroll(
                collection_name=self.CRAWLED_PAGES,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="url",
                            match=models.MatchValue(value=url)
                        )
                    ]
                ),
                limit=1000,  # Get all chunks for the URL
                with_payload=True,
                with_vectors=False
            )
            
            documents = []
            for point in results[0]:  # results is a tuple (points, next_offset)
                doc = point.payload
                doc["id"] = point.id
                documents.append(doc)
            
            # Sort by chunk_number for consistency
            documents.sort(key=lambda x: x.get("chunk_number", 0))
            return documents
        except Exception as e:
            print(f"Error getting documents by URL from Qdrant: {e}")
            return []
    
    async def search_documents_by_keyword(
        self,
        keyword: str,
        match_count: int = 10,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for documents containing a keyword"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        try:
            # Create filter conditions
            filter_conditions = []
            
            # Add keyword filter (case-insensitive search in content)
            # Note: Qdrant doesn't have native ILIKE, so we search for exact matches
            # In production, you might want to use a full-text search solution
            filter_conditions.append(
                models.FieldCondition(
                    key="content",
                    match=models.MatchText(text=keyword.lower())
                )
            )
            
            # Add source filter if provided
            if source_filter:
                filter_conditions.append(
                    models.FieldCondition(
                        key="source_id",
                        match=models.MatchValue(value=source_filter)
                    )
                )
            
            # Perform scroll search
            results = await self.client.scroll(
                collection_name=self.CRAWLED_PAGES,
                scroll_filter=models.Filter(must=filter_conditions) if filter_conditions else None,
                limit=match_count,
                with_payload=True,
                with_vectors=False
            )
            
            documents = []
            for point in results[0]:  # results is a tuple (points, next_offset)
                doc = point.payload
                doc["id"] = point.id
                documents.append(doc)
            
            return documents
        except Exception as e:
            print(f"Error searching documents by keyword in Qdrant: {e}")
            return []
    
    async def search_code_examples_by_keyword(
        self,
        keyword: str,
        match_count: int = 10,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for code examples containing a keyword"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        try:
            # Create filter conditions
            filter_conditions = []
            
            # Search in both content and summary
            # Note: This is a simplified implementation
            # In production, consider using Qdrant's full-text search capabilities
            keyword_conditions = [
                models.FieldCondition(
                    key="content",
                    match=models.MatchText(text=keyword.lower())
                ),
                models.FieldCondition(
                    key="summary", 
                    match=models.MatchText(text=keyword.lower())
                )
            ]
            
            # Combine keyword conditions with OR
            if source_filter:
                filter_conditions = [
                    models.Filter(
                        should=keyword_conditions,
                        must=[
                            models.FieldCondition(
                                key="source_id",
                                match=models.MatchValue(value=source_filter)
                            )
                        ]
                    )
                ]
            else:
                filter_conditions = [models.Filter(should=keyword_conditions)]
            
            # Perform scroll search
            results = await self.client.scroll(
                collection_name=self.CODE_EXAMPLES,
                scroll_filter=filter_conditions[0] if filter_conditions else None,
                limit=match_count,
                with_payload=True,
                with_vectors=False
            )
            
            examples = []
            for point in results[0]:  # results is a tuple (points, next_offset)
                example = point.payload
                example["id"] = point.id
                examples.append(example)
            
            return examples
        except Exception as e:
            print(f"Error searching code examples by keyword in Qdrant: {e}")
            return []

    async def get_sources(self) -> List[Dict[str, Any]]:
        """Get all available sources"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        try:
            # Scroll through all points in sources collection
            sources = []
            offset = None
            
            while True:
                results, next_offset = await self.client.scroll(
                    collection_name=self.SOURCES,
                    limit=100,
                    offset=offset
                )
                
                for point in results:
                    source = {
                        "source_id": point.payload.get("source_id"),
                        "summary": point.payload.get("summary"),
                        "total_word_count": point.payload.get("total_word_count"),
                        "created_at": point.payload.get("created_at", ""),
                        "updated_at": point.payload.get("updated_at", "")
                    }
                    sources.append(source)
                
                if next_offset is None:
                    break
                offset = next_offset
            
            # Sort by source_id for consistency
            sources.sort(key=lambda x: x["source_id"])
            return sources
        except Exception as e:
            print(f"Error getting sources from Qdrant: {e}")
            return []
    
    def _build_filter(
        self, 
        filter_metadata: Optional[Dict[str, Any]] = None,
        source_filter: Optional[str] = None
    ) -> Optional[Filter]:
        """Build Qdrant filter from metadata and source filters"""
        conditions = []
        
        # Add metadata filters
        if filter_metadata:
            for key, value in filter_metadata.items():
                conditions.append(
                    FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=value)
                    )
                )
        
        # Add source filter
        if source_filter:
            conditions.append(
                FieldCondition(
                    key="source_id",
                    match=MatchValue(value=source_filter)
                )
            )
        
        # Return filter if conditions exist
        if conditions:
            return Filter(must=conditions)
        return None