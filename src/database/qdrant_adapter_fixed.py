"""
Qdrant adapter implementation for VectorDatabase protocol.
Uses Qdrant vector database for similarity search.
Fixed version with proper async/sync handling.
"""

import asyncio
import hashlib
import os
import uuid
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointIdsList,
    PointStruct,
    VectorParams,
)


class QdrantAdapter:
    """
    Qdrant implementation of the VectorDatabase protocol.
    Uses Qdrant's native vector search capabilities.

    Note: QdrantClient is synchronous, so we use asyncio.run_in_executor
    to make it work with async methods.
    """

    def __init__(self, url: str | None = None, api_key: str | None = None):
        """Initialize Qdrant adapter with connection parameters"""
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.client: QdrantClient | None = None
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
            (self.SOURCES, 1536),  # OpenAI embedding size for consistency
        ]

        loop = asyncio.get_event_loop()

        for collection_name, vector_size in collections:
            try:
                await loop.run_in_executor(
                    None, self.client.get_collection, collection_name,
                )
            except Exception:
                # Collection doesn't exist, create it
                await loop.run_in_executor(
                    None,
                    self.client.create_collection,
                    collection_name,
                    VectorParams(size=vector_size, distance=Distance.COSINE),
                )

    def _generate_point_id(self, url: str, chunk_number: int) -> str:
        """Generate a deterministic ID for a document point"""
        id_string = f"{url}_{chunk_number}"
        return hashlib.md5(id_string.encode()).hexdigest()

    async def add_documents(
        self,
        urls: list[str],
        chunk_numbers: list[int],
        contents: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
        source_ids: list[str] | None = None,
    ) -> None:
        """Add documents to Qdrant"""
        if source_ids is None:
            source_ids = [None] * len(urls)

        # First, delete any existing documents with the same URLs
        unique_urls = list(set(urls))
        for url in unique_urls:
            try:
                await self.delete_documents_by_url(url)
            except Exception as e:
                print(f"Error deleting documents from Qdrant: {e}")

        # Process documents in batches
        for i in range(0, len(urls), self.batch_size):
            batch_slice = slice(i, min(i + self.batch_size, len(urls)))
            batch_urls = urls[batch_slice]
            batch_chunks = chunk_numbers[batch_slice]
            batch_contents = contents[batch_slice]
            batch_metadatas = metadatas[batch_slice]
            batch_embeddings = embeddings[batch_slice]
            batch_source_ids = source_ids[batch_slice]

            # Create points for Qdrant
            points = []
            for j, (
                url,
                chunk_num,
                content,
                metadata,
                embedding,
                source_id,
            ) in enumerate(
                zip(
                    batch_urls,
                    batch_chunks,
                    batch_contents,
                    batch_metadatas,
                    batch_embeddings,
                    batch_source_ids, strict=False,
                ),
            ):
                point_id = self._generate_point_id(url, chunk_num)

                # Prepare payload
                payload = {
                    "url": url,
                    "chunk_number": chunk_num,
                    "content": content,
                    "metadata": metadata or {},
                }
                if source_id:
                    payload["source_id"] = source_id

                point = PointStruct(id=point_id, vector=embedding, payload=payload)
                points.append(point)

            # Upsert batch to Qdrant
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, self.client.upsert, self.CRAWLED_PAGES, points,
                )
            except Exception as e:
                print(f"Error upserting documents to Qdrant: {e}")
                raise

    async def search_documents(
        self,
        query_embedding: list[float],
        match_count: int = 10,
        metadata_filter: dict[str, Any] | None = None,
        source_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar documents"""
        # Build filter conditions
        filter_conditions = []

        if metadata_filter:
            for key, value in metadata_filter.items():
                filter_conditions.append(
                    FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value)),
                )

        if source_filter:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.source", match=MatchValue(value=source_filter),
                ),
            )

        # Create filter if conditions exist
        search_filter = None
        if filter_conditions:
            search_filter = Filter(must=filter_conditions)

        # Perform search
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            self.client.search,
            self.CRAWLED_PAGES,
            query_embedding,
            search_filter,
            match_count,
        )

        # Format results
        formatted_results = []
        for result in results:
            doc = result.payload.copy()
            doc["score"] = result.score
            doc["id"] = result.id
            formatted_results.append(doc)

        return formatted_results

    async def search_documents_by_keyword(
        self,
        keyword: str,
        match_count: int = 10,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search documents by keyword using scroll API"""
        filter_conditions = []

        # Add keyword filter - search in content
        filter_conditions.append(
            FieldCondition(key="content", match=MatchValue(value=keyword)),
        )

        if metadata_filter:
            for key, value in metadata_filter.items():
                filter_conditions.append(
                    FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value)),
                )

        search_filter = Filter(must=filter_conditions)

        # Use scroll to find matching documents
        loop = asyncio.get_event_loop()
        scroll_result = await loop.run_in_executor(
            None,
            self.client.scroll,
            self.CRAWLED_PAGES,
            search_filter,
            limit=match_count,
        )

        points, _ = scroll_result

        # Format results
        formatted_results = []
        for point in points[:match_count]:
            doc = point.payload.copy()
            doc["id"] = point.id
            formatted_results.append(doc)

        return formatted_results

    async def get_documents_by_url(self, url: str) -> list[dict[str, Any]]:
        """Get all document chunks for a specific URL"""
        filter_condition = Filter(
            must=[FieldCondition(key="url", match=MatchValue(value=url))],
        )

        # Use scroll to get all chunks
        loop = asyncio.get_event_loop()
        scroll_result = await loop.run_in_executor(
            None,
            self.client.scroll,
            self.CRAWLED_PAGES,
            filter_condition,
            limit=1000,  # Large limit to get all chunks
        )

        points, _ = scroll_result

        # Format and sort by chunk number
        results = []
        for point in points:
            doc = point.payload.copy()
            doc["id"] = point.id
            results.append(doc)

        # Sort by chunk number
        results.sort(key=lambda x: x.get("chunk_number", 0))

        return results

    async def delete_documents_by_url(self, url: str) -> None:
        """Delete all document chunks for a specific URL"""
        # First, find all points with this URL
        filter_condition = Filter(
            must=[FieldCondition(key="url", match=MatchValue(value=url))],
        )

        loop = asyncio.get_event_loop()
        scroll_result = await loop.run_in_executor(
            None, self.client.scroll, self.CRAWLED_PAGES, filter_condition, limit=1000,
        )

        points, _ = scroll_result

        if points:
            # Extract point IDs
            point_ids = [point.id for point in points]

            # Delete the points
            await loop.run_in_executor(
                None,
                self.client.delete,
                self.CRAWLED_PAGES,
                PointIdsList(points=point_ids),
            )

    async def add_code_examples(
        self,
        urls: list[str],
        chunk_numbers: list[int],
        codes: list[str],
        summaries: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        """Add code examples to Qdrant"""
        # Process in batches
        for i in range(0, len(urls), self.batch_size):
            batch_slice = slice(i, min(i + self.batch_size, len(urls)))
            batch_urls = urls[batch_slice]
            batch_chunks = chunk_numbers[batch_slice]
            batch_codes = codes[batch_slice]
            batch_summaries = summaries[batch_slice]
            batch_metadatas = metadatas[batch_slice]
            batch_embeddings = embeddings[batch_slice]

            # Create points
            points = []
            for url, chunk_num, code, summary, metadata, embedding in zip(
                batch_urls,
                batch_chunks,
                batch_codes,
                batch_summaries,
                batch_metadatas,
                batch_embeddings, strict=False,
            ):
                point_id = f"code_{self._generate_point_id(url, chunk_num)}"

                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "url": url,
                        "chunk_number": chunk_num,
                        "code": code,
                        "summary": summary,
                        "metadata": metadata or {},
                    },
                )
                points.append(point)

            # Upsert to Qdrant
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self.client.upsert, self.CODE_EXAMPLES, points,
            )

    async def search_code_examples(
        self,
        query_embedding: list[float],
        match_count: int = 10,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar code examples"""
        # Build filter if needed
        search_filter = None
        if filter_metadata:
            filter_conditions = []
            for key, value in filter_metadata.items():
                filter_conditions.append(
                    FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value)),
                )
            search_filter = Filter(must=filter_conditions)

        try:
            # Use the same pattern as other search methods in this class
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                self.client.search,
                self.CODE_EXAMPLES,
                query_embedding,
                search_filter,
                match_count,
            )
            
            # Format results to match the expected interface
            formatted_results = []
            for result in results:
                doc = result.payload.copy()
                doc["score"] = result.score
                doc["id"] = result.id
                formatted_results.append(doc)

            return formatted_results
        except Exception as e:
            # Need to import logging at the top of the file
            print(f"Error searching code examples: {e}")
            return []

    async def add_source(
        self,
        source_id: str,
        url: str,
        title: str,
        description: str,
        metadata: dict[str, Any],
        embedding: list[float],
    ) -> None:
        """Add a source to Qdrant"""
        # Generate a deterministic UUID from source_id
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, source_id))

        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "source_id": source_id,
                "url": url,
                "title": title,
                "description": description,
                "metadata": metadata or {},
            },
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.client.upsert, self.SOURCES, [point])

    async def search_sources(
        self, query_embedding: list[float], match_count: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for similar sources"""
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, self.client.search, self.SOURCES, query_embedding, None, match_count,
        )

        # Format results
        formatted_results = []
        for result in results:
            doc = result.payload.copy()
            doc["score"] = result.score
            doc["id"] = result.id
            formatted_results.append(doc)

        return formatted_results

    async def update_source(self, source_id: str, updates: dict[str, Any]) -> None:
        """Update a source's metadata"""
        # Generate a deterministic UUID from source_id
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, source_id))

        # Get existing source
        loop = asyncio.get_event_loop()

        try:
            existing_points = await loop.run_in_executor(
                None, self.client.retrieve, self.SOURCES, [point_id],
            )

            if not existing_points:
                raise ValueError(f"Source {source_id} not found")

            # Update payload
            existing_point = existing_points[0]
            updated_payload = existing_point.payload.copy()
            updated_payload.update(updates)

            # Update the point
            await loop.run_in_executor(
                None, self.client.set_payload, self.SOURCES, {point_id: updated_payload},
            )
        except Exception as e:
            print(f"Error updating source: {e}")
            raise
