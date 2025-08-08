"""
Qdrant adapter implementation for VectorDatabase protocol.

Uses Qdrant vector database for similarity search.
Fixed version with proper async/sync handling.
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC
from typing import Any

from qdrant_client import QdrantClient, models
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
                    None,
                    self.client.get_collection,
                    collection_name,
                )
            except Exception:
                # Collection doesn't exist, create it
                try:
                    await loop.run_in_executor(
                        None,
                        self.client.create_collection,
                        collection_name,
                        VectorParams(size=vector_size, distance=Distance.COSINE),
                    )
                except Exception as create_error:
                    # Log error but continue - collection might already exist
                    print(
                        f"Warning: Could not create collection {collection_name}: {create_error}",
                        file=sys.stderr,
                    )

    def _generate_point_id(self, url: str, chunk_number: int) -> str:
        """Generate a deterministic UUID for a document point"""
        id_string = f"{url}_{chunk_number}"
        # Use uuid5 to generate a deterministic UUID from the URL and chunk number
        return str(uuid.uuid5(uuid.NAMESPACE_URL, id_string))

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
                    batch_source_ids,
                    strict=False,
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

                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
                points.append(point)

            # Upsert batch to Qdrant
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self.client.upsert,
                    self.CRAWLED_PAGES,
                    points,
                )
            except Exception as e:
                print(f"Error upserting documents to Qdrant: {e}")
                raise

    async def search_documents(
        self,
        query_embedding: list[float],
        match_count: int = 10,
        filter_metadata: dict[str, Any] | None = None,
        source_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar documents"""
        # Build filter conditions
        filter_conditions = []

        if filter_metadata:
            for key, value in filter_metadata.items():
                filter_conditions.append(
                    FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=value),
                    ),
                )

        if source_filter:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.source",
                    match=MatchValue(value=source_filter),
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
            lambda: self.client.search(
                collection_name=self.CRAWLED_PAGES,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=match_count,
            ),
        )

        # Format results
        formatted_results = []
        for result in results:
            doc = result.payload.copy()
            doc["similarity"] = result.score  # Interface expects "similarity"
            doc["id"] = result.id
            formatted_results.append(doc)

        return formatted_results

    async def search_documents_by_keyword(
        self,
        keyword: str,
        match_count: int = 10,
        source_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search documents by keyword using scroll API"""
        filter_conditions = []

        # Add keyword filter - search in content
        filter_conditions.append(
            FieldCondition(
                key="content",
                match=MatchValue(value=keyword),
            ),
        )

        if source_filter:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.source",
                    match=MatchValue(value=source_filter),
                ),
            )

        search_filter = Filter(must=filter_conditions)

        # Use scroll to find matching documents
        loop = asyncio.get_event_loop()

        def scroll_keyword_search():
            return self.client.scroll(
                collection_name=self.CRAWLED_PAGES,
                scroll_filter=search_filter,
                limit=match_count,
            )

        scroll_result = await loop.run_in_executor(None, scroll_keyword_search)

        points, _ = scroll_result

        # Format results
        formatted_results = []
        for point in points[:match_count]:
            doc = point.payload.copy()
            doc["id"] = point.id
            formatted_results.append(doc)

        return formatted_results

    async def search(
        self,
        query: str,
        match_count: int = 10,
        filter_metadata: dict[str, Any] | None = None,
        source_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Generic search method that generates embeddings internally.

        Args:
            query: Search query string
            match_count: Maximum number of results to return
            filter_metadata: Optional metadata filter
            source_filter: Optional source filter

        Returns:
            List of matching documents with similarity scores
        """
        # Generate embedding for the query
        from utils import create_embedding

        query_embedding = create_embedding(query)

        # Delegate to the existing search_documents method
        return await self.search_documents(
            query_embedding=query_embedding,
            match_count=match_count,
            filter_metadata=filter_metadata,
            source_filter=source_filter,
        )

    async def hybrid_search(
        self,
        query: str,
        match_count: int = 10,
        filter_metadata: dict[str, Any] | None = None,
        source_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Hybrid search combining vector similarity and keyword matching.

        Args:
            query: Search query string
            match_count: Maximum number of results to return
            filter_metadata: Optional metadata filter
            source_filter: Optional source filter

        Returns:
            List of matching documents combining vector and keyword results
        """
        # Perform vector search
        vector_results = await self.search(
            query=query,
            match_count=match_count // 2 + 1,  # Get half from vector search
            filter_metadata=filter_metadata,
            source_filter=source_filter,
        )

        # Perform keyword search
        keyword_results = await self.search_documents_by_keyword(
            keyword=query,
            match_count=match_count // 2 + 1,  # Get half from keyword search
            source_filter=source_filter,
        )

        # Combine and deduplicate results
        combined_results = {}

        # Add vector results with their similarity scores
        for result in vector_results:
            doc_id = result.get("id", result.get("url", ""))
            if doc_id:
                result["search_type"] = "vector"
                result["combined_score"] = (
                    result.get("similarity", 0.0) * 0.7
                )  # Weight vector search more
                combined_results[doc_id] = result

        # Add keyword results (give them a base similarity score)
        for result in keyword_results:
            doc_id = result.get("id", result.get("url", ""))
            if doc_id:
                if doc_id in combined_results:
                    # Document found in both searches - boost the score
                    combined_results[doc_id]["combined_score"] += (
                        0.3  # Boost for appearing in both
                    )
                    combined_results[doc_id]["search_type"] = "hybrid"
                else:
                    # Document only found in keyword search
                    result["search_type"] = "keyword"
                    result["similarity"] = 0.5  # Base similarity for keyword matches
                    result["combined_score"] = (
                        0.3  # Lower weight for keyword-only matches
                    )
                    combined_results[doc_id] = result

        # Sort by combined score and return top results
        final_results = list(combined_results.values())
        final_results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)

        # Update similarity to reflect combined score and limit results
        for result in final_results[:match_count]:
            result["similarity"] = result.get("combined_score", 0)
            # Remove the temporary combined_score field
            result.pop("combined_score", None)

        return final_results[:match_count]

    async def get_documents_by_url(self, url: str) -> list[dict[str, Any]]:
        """Get all document chunks for a specific URL"""
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="url",
                    match=MatchValue(value=url),
                ),
            ],
        )

        # Use scroll to get all chunks
        loop = asyncio.get_event_loop()

        def scroll_for_url():
            return self.client.scroll(
                collection_name=self.CRAWLED_PAGES,
                scroll_filter=filter_condition,
                limit=1000,  # Large limit to get all chunks
            )

        scroll_result = await loop.run_in_executor(None, scroll_for_url)

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

    async def delete_documents_by_url(self, urls: list[str]) -> None:
        """Delete all document chunks for the given URLs"""
        loop = asyncio.get_event_loop()

        for url in urls:
            # First, find all points with this URL
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="url",
                        match=MatchValue(value=url),
                    ),
                ],
            )

            def scroll_with_filter():
                return self.client.scroll(
                    collection_name=self.CRAWLED_PAGES,
                    scroll_filter=filter_condition,
                    limit=1000,
                )

            scroll_result = await loop.run_in_executor(None, scroll_with_filter)

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
        code_examples: list[str],
        summaries: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
        source_ids: list[str] | None = None,
    ) -> None:
        """Add code examples to Qdrant"""
        if source_ids is None:
            source_ids = [None] * len(urls)

        # Process in batches
        for i in range(0, len(urls), self.batch_size):
            batch_slice = slice(i, min(i + self.batch_size, len(urls)))
            batch_urls = urls[batch_slice]
            batch_chunks = chunk_numbers[batch_slice]
            batch_code_examples = code_examples[batch_slice]
            batch_summaries = summaries[batch_slice]
            batch_metadatas = metadatas[batch_slice]
            batch_embeddings = embeddings[batch_slice]
            batch_source_ids = source_ids[batch_slice]

            # Create points
            points = []
            for (
                url,
                chunk_num,
                code_example,
                summary,
                metadata,
                embedding,
                source_id,
            ) in zip(
                batch_urls,
                batch_chunks,
                batch_code_examples,
                batch_summaries,
                batch_metadatas,
                batch_embeddings,
                batch_source_ids,
                strict=False,
            ):
                # Generate a unique UUID for code examples using a different namespace
                id_string = f"code_{url}_{chunk_num}"
                point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, id_string))

                payload = {
                    "url": url,
                    "chunk_number": chunk_num,
                    "code": code_example,
                    "summary": summary,
                    "metadata": metadata or {},
                }
                if source_id:
                    payload["source_id"] = source_id

                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
                points.append(point)

            # Upsert to Qdrant
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.client.upsert,
                self.CODE_EXAMPLES,
                points,
            )

    async def search_code_examples(
        self,
        query: str | list[float] | None = None,
        match_count: int = 10,
        filter_metadata: dict[str, Any] | None = None,
        source_filter: str | None = None,
        # Legacy parameter for backward compatibility
        query_embedding: list[float] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar code examples"""
        # Handle backward compatibility - prioritize query_embedding if provided
        if query_embedding is not None:
            final_embedding = query_embedding
        elif query is not None:
            # Generate embedding if query is a string
            if isinstance(query, str):
                from utils import create_embedding

                final_embedding = create_embedding(query)
            else:
                final_embedding = query
        else:
            raise ValueError("Either 'query' or 'query_embedding' must be provided")

        # Build filter if needed
        filter_conditions = []

        if filter_metadata:
            for key, value in filter_metadata.items():
                filter_conditions.append(
                    FieldCondition(
                        key=f"metadata.{key}",
                        match=MatchValue(value=value),
                    ),
                )

        if source_filter:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.source",
                    match=MatchValue(value=source_filter),
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
            lambda: self.client.search(
                collection_name=self.CODE_EXAMPLES,
                query_vector=final_embedding,
                query_filter=search_filter,
                limit=match_count,
            ),
        )

        # Format results
        formatted_results = []
        for result in results:
            doc = result.payload.copy()
            doc["similarity"] = result.score  # Interface expects "similarity"
            doc["id"] = result.id
            formatted_results.append(doc)

        return formatted_results

    async def delete_code_examples_by_url(self, urls: list[str]) -> None:
        """Delete all code examples with the given URLs"""
        loop = asyncio.get_event_loop()

        for url in urls:
            # First, find all points with this URL
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="url",
                        match=MatchValue(value=url),
                    ),
                ],
            )

            def scroll_code_for_deletion():
                return self.client.scroll(
                    collection_name=self.CODE_EXAMPLES,
                    scroll_filter=filter_condition,
                    limit=1000,
                )

            scroll_result = await loop.run_in_executor(None, scroll_code_for_deletion)

            points, _ = scroll_result

            if points:
                # Extract point IDs
                point_ids = [point.id for point in points]

                # Delete the points
                await loop.run_in_executor(
                    None,
                    self.client.delete,
                    self.CODE_EXAMPLES,
                    PointIdsList(points=point_ids),
                )

    async def search_code_examples_by_keyword(
        self,
        keyword: str,
        match_count: int = 10,
        source_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search code examples by keyword using scroll API"""
        filter_conditions = []

        # Add keyword filter - search in code content
        filter_conditions.append(
            FieldCondition(
                key="code",
                match=MatchValue(value=keyword),
            ),
        )

        if source_filter:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.source",
                    match=MatchValue(value=source_filter),
                ),
            )

        search_filter = Filter(must=filter_conditions)

        # Use scroll to find matching code examples
        loop = asyncio.get_event_loop()

        def scroll_code_keyword_search():
            return self.client.scroll(
                collection_name=self.CODE_EXAMPLES,
                scroll_filter=search_filter,
                limit=match_count,
            )

        scroll_result = await loop.run_in_executor(None, scroll_code_keyword_search)

        points, _ = scroll_result

        # Format results
        formatted_results = []
        for point in points[:match_count]:
            doc = point.payload.copy()
            doc["id"] = point.id
            formatted_results.append(doc)

        return formatted_results

    async def get_repository_code_examples(
        self,
        repo_name: str,
        code_type: str | None = None,
        match_count: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get all code examples for a specific repository.

        Args:
            repo_name: Repository name to filter by
            code_type: Optional code type filter ('class', 'method', 'function')
            match_count: Maximum number of results

        Returns:
            List of code examples from the repository
        """
        filter_conditions = [
            FieldCondition(
                key="metadata.repository_name",
                match=MatchValue(value=repo_name),
            ),
        ]

        if code_type:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.code_type",
                    match=MatchValue(value=code_type),
                ),
            )

        search_filter = Filter(must=filter_conditions)

        loop = asyncio.get_event_loop()

        def scroll_repository_code():
            return self.client.scroll(
                collection_name=self.CODE_EXAMPLES,
                scroll_filter=search_filter,
                limit=match_count,
            )

        scroll_result = await loop.run_in_executor(None, scroll_repository_code)
        points, _ = scroll_result

        # Format results
        formatted_results = []
        for point in points:
            doc = point.payload.copy()
            doc["id"] = point.id
            formatted_results.append(doc)

        return formatted_results

    async def delete_repository_code_examples(self, repo_name: str) -> None:
        """
        Delete all code examples for a specific repository.

        Args:
            repo_name: Repository name to delete code examples for
        """
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="metadata.repository_name",
                    match=MatchValue(value=repo_name),
                ),
            ],
        )

        loop = asyncio.get_event_loop()

        def scroll_for_deletion():
            return self.client.scroll(
                collection_name=self.CODE_EXAMPLES,
                scroll_filter=filter_condition,
                limit=1000,
            )

        scroll_result = await loop.run_in_executor(None, scroll_for_deletion)
        points, _ = scroll_result

        if points:
            # Extract point IDs
            point_ids = [point.id for point in points]

            # Delete the points
            await loop.run_in_executor(
                None,
                self.client.delete,
                self.CODE_EXAMPLES,
                PointIdsList(points=point_ids),
            )

    async def search_code_by_signature(
        self,
        method_name: str,
        class_name: str | None = None,
        repo_filter: str | None = None,
        match_count: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for code examples by method/function signature.

        Args:
            method_name: Name of method or function to search for
            class_name: Optional class name to filter by
            repo_filter: Optional repository name to filter by
            match_count: Maximum number of results

        Returns:
            List of matching code examples
        """
        filter_conditions = [
            FieldCondition(
                key="metadata.name",
                match=MatchValue(value=method_name),
            ),
        ]

        if class_name:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.class_name",
                    match=MatchValue(value=class_name),
                ),
            )

        if repo_filter:
            filter_conditions.append(
                FieldCondition(
                    key="metadata.repository_name",
                    match=MatchValue(value=repo_filter),
                ),
            )

        search_filter = Filter(must=filter_conditions)

        loop = asyncio.get_event_loop()

        def scroll_signature_search():
            return self.client.scroll(
                collection_name=self.CODE_EXAMPLES,
                scroll_filter=search_filter,
                limit=match_count,
            )

        scroll_result = await loop.run_in_executor(None, scroll_signature_search)
        points, _ = scroll_result

        # Format results
        formatted_results = []
        for point in points:
            doc = point.payload.copy()
            doc["id"] = point.id
            formatted_results.append(doc)

        return formatted_results

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
        await loop.run_in_executor(
            None,
            self.client.upsert,
            self.SOURCES,
            [point],
        )

    async def search_sources(
        self,
        query_embedding: list[float],
        match_count: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for similar sources"""
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: self.client.search(
                collection_name=self.SOURCES,
                query_vector=query_embedding,
                query_filter=None,
                limit=match_count,
            ),
        )

        # Format results
        formatted_results = []
        for result in results:
            doc = result.payload.copy()
            doc["similarity"] = result.score  # Interface expects "similarity"
            doc["id"] = result.id
            formatted_results.append(doc)

        return formatted_results

    async def update_source(
        self,
        source_id: str,
        updates: dict[str, Any],
    ) -> None:
        """Update a source's metadata"""
        # Generate a deterministic UUID from source_id
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, source_id))

        # Get existing source
        loop = asyncio.get_event_loop()

        try:
            existing_points = await loop.run_in_executor(
                None,
                self.client.retrieve,
                self.SOURCES,
                [point_id],
            )

            if not existing_points:
                raise ValueError(f"Source {source_id} not found")

            # Update payload
            existing_point = existing_points[0]
            updated_payload = existing_point.payload.copy()
            updated_payload.update(updates)

            # Update the point
            await loop.run_in_executor(
                None,
                self.client.set_payload,
                self.SOURCES,
                {point_id: updated_payload},
            )
        except Exception as e:
            print(f"Error updating source: {e}", file=sys.stderr)
            raise

    async def get_sources(self) -> list[dict[str, Any]]:
        """
        Get all available sources.

        Returns:
            List of sources, each containing:
            - source_id: Source identifier
            - summary: Source summary
            - total_word_count: Total word count
            - created_at: Creation timestamp
            - updated_at: Update timestamp
        """
        loop = asyncio.get_event_loop()

        try:
            # Scroll through all points in the sources collection
            all_sources = []
            offset = None
            limit = 100

            while True:
                # Get a batch of sources
                def scroll_sources():
                    return self.client.scroll(
                        collection_name=self.SOURCES,
                        offset=offset,
                        limit=limit,
                        with_payload=True,
                    )

                result = await loop.run_in_executor(None, scroll_sources)

                points, next_offset = result

                # Format each source
                for point in points:
                    source_data = {
                        "source_id": point.payload.get(
                            "source_id",
                            point.id,
                        ),  # Get from payload, fallback to ID
                        "summary": point.payload.get("summary", ""),
                        "total_word_count": point.payload.get("total_word_count", 0),
                        "created_at": point.payload.get("created_at", ""),
                        "updated_at": point.payload.get("updated_at", ""),
                        "enabled": point.payload.get("enabled", True),
                        "url_count": point.payload.get("url_count", 0),
                    }
                    all_sources.append(source_data)

                # Check if there are more sources
                if next_offset is None:
                    break

                offset = next_offset

            # Sort by source_id for consistency
            all_sources.sort(key=lambda x: x["source_id"])

            return all_sources

        except Exception as e:
            print(f"Error getting sources: {e}", file=sys.stderr)
            return []

    async def update_source_info(
        self,
        source_id: str,
        summary: str,
        word_count: int,
    ) -> None:
        """
        Update or insert source information.

        Args:
            source_id: Source identifier
            summary: Source summary
            word_count: Word count for this source
        """
        from datetime import datetime

        loop = asyncio.get_event_loop()
        timestamp = datetime.now(UTC).isoformat()

        try:
            # Generate a deterministic UUID from source_id
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, source_id))

            # Try to get existing source
            try:
                existing_points = await loop.run_in_executor(
                    None,
                    self.client.retrieve,
                    self.SOURCES,
                    [point_id],
                )

                if existing_points:
                    # Update existing source
                    existing_point = existing_points[0]
                    updated_payload = existing_point.payload.copy()
                    updated_payload.update(
                        {
                            "summary": summary,
                            "total_word_count": word_count,
                            "updated_at": timestamp,
                        },
                    )

                    await loop.run_in_executor(
                        None,
                        self.client.set_payload,
                        self.SOURCES,
                        {point_id: updated_payload},
                    )
                else:
                    # Create new source
                    await self._create_new_source(
                        source_id,
                        summary,
                        word_count,
                        timestamp,
                        point_id,
                    )
            except Exception:
                # Source doesn't exist, create new one
                await self._create_new_source(
                    source_id,
                    summary,
                    word_count,
                    timestamp,
                    point_id,
                )

        except Exception as e:
            print(f"Error updating source info: {e}", file=sys.stderr)
            raise

    async def _create_new_source(
        self,
        source_id: str,
        summary: str,
        word_count: int,
        timestamp: str,
        point_id: str,
    ) -> None:
        """Helper method to create a new source"""
        try:
            loop = asyncio.get_event_loop()
            # Create new source with a deterministic embedding
            # IMPORTANT: This embedding must be 1536 dimensions to match OpenAI's text-embedding-3-small model
            # Previously this was creating 384-dimensional embeddings which caused vector dimension errors

            # Generate a deterministic embedding from the source_id using SHA256 hash
            import hashlib

            hash_object = hashlib.sha256(source_id.encode())
            hash_bytes = hash_object.digest()  # 32 bytes from SHA256

            # Convert hash bytes to floats between -1 and 1
            # Each byte (0-255) is normalized to the range [-1, 1]
            base_embedding = [(b - 128) / 128.0 for b in hash_bytes]

            # OpenAI embeddings are 1536 dimensions, but SHA256 only gives us 32 values
            # We repeat the pattern to fill all 1536 dimensions deterministically
            embedding = []
            while len(embedding) < 1536:
                embedding.extend(base_embedding)

            # Ensure exactly 1536 dimensions (trim any excess from the last repetition)
            embedding = embedding[:1536]

            points = [
                models.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "source_id": source_id,
                        "summary": summary,
                        "total_word_count": word_count,
                        "created_at": timestamp,
                        "updated_at": timestamp,
                        "enabled": True,
                        "url_count": 1,
                    },
                ),
            ]

            await loop.run_in_executor(
                None,
                self.client.upsert,
                self.SOURCES,
                points,
            )
        except Exception as e:
            print(f"Error creating new source: {e}", file=sys.stderr)
            raise
