"""
Supabase adapter implementation for VectorDatabase protocol.
Extracts and refactors existing Supabase functionality.
"""
import os
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from supabase import create_client, Client
import time


class SupabaseAdapter:
    """
    Supabase implementation of the VectorDatabase protocol.
    Uses PostgreSQL with pgvector extension for vector similarity search.
    """
    
    def __init__(self):
        """Initialize Supabase adapter with environment configuration"""
        self.client: Optional[Client] = None
        self.batch_size = 20  # Default batch size for operations
        self.max_retries = 3
        self.retry_delay = 1.0  # Initial retry delay in seconds
    
    async def initialize(self) -> None:
        """Initialize Supabase client connection"""
        if self.client is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_KEY")
            
            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
            
            self.client = create_client(url, key)
    
    async def add_documents(
        self,
        urls: List[str],
        chunk_numbers: List[int],
        contents: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: List[List[float]],
        source_ids: List[str]
    ) -> None:
        """Add documents to Supabase with batch processing"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        # Get unique URLs to delete existing records
        unique_urls = list(set(urls))
        
        # Delete existing records for these URLs
        await self._delete_documents_batch(unique_urls)
        
        # Process in batches to avoid memory issues
        for i in range(0, len(contents), self.batch_size):
            batch_end = min(i + self.batch_size, len(contents))
            
            # Prepare batch data
            batch_data = []
            for j in range(i, batch_end):
                # Extract source_id from URL if not provided
                if j < len(source_ids) and source_ids[j]:
                    source_id = source_ids[j]
                else:
                    parsed_url = urlparse(urls[j])
                    source_id = parsed_url.netloc or parsed_url.path
                
                data = {
                    "url": urls[j],
                    "chunk_number": chunk_numbers[j],
                    "content": contents[j],
                    "metadata": {
                        "chunk_size": len(contents[j]),
                        **(metadatas[j] if j < len(metadatas) else {})
                    },
                    "source_id": source_id,
                    "embedding": embeddings[j]
                }
                batch_data.append(data)
            
            # Insert batch with retry logic
            await self._insert_with_retry("crawled_pages", batch_data)
    
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
        
        try:
            # Build parameters for RPC call
            params = {
                'query_embedding': query_embedding,
                'match_count': match_count
            }
            
            # Add optional filters
            if filter_metadata:
                params['filter'] = filter_metadata
            if source_filter:
                params['source_filter'] = source_filter
            
            # Execute search using Supabase RPC function
            result = self.client.rpc('match_crawled_pages', params).execute()
            
            return result.data
        except Exception as e:
            print(f"Error searching documents: {e}")
            return []
    
    async def delete_documents_by_url(self, urls: List[str]) -> None:
        """Delete documents by URL"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        await self._delete_documents_batch(urls)
    
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
        """Add code examples to Supabase"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        if not urls:
            return
        
        # Delete existing records for these URLs
        unique_urls = list(set(urls))
        for url in unique_urls:
            try:
                self.client.table('code_examples').delete().eq('url', url).execute()
            except Exception as e:
                print(f"Error deleting existing code examples for {url}: {e}")
        
        # Process in batches
        for i in range(0, len(urls), self.batch_size):
            batch_end = min(i + self.batch_size, len(urls))
            
            # Prepare batch data
            batch_data = []
            for j in range(i, batch_end):
                # Extract source_id from URL
                parsed_url = urlparse(urls[j])
                source_id = parsed_url.netloc or parsed_url.path
                
                batch_data.append({
                    'url': urls[j],
                    'chunk_number': chunk_numbers[j],
                    'content': code_examples[j],
                    'summary': summaries[j],
                    'metadata': metadatas[j] if j < len(metadatas) else {},
                    'source_id': source_id,
                    'embedding': embeddings[j]
                })
            
            # Insert batch with retry logic
            await self._insert_with_retry('code_examples', batch_data)
    
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
        
        try:
            # Build parameters for RPC call
            params = {
                'query_embedding': query_embedding,
                'match_count': match_count
            }
            
            # Add optional filters
            if filter_metadata:
                params['filter'] = filter_metadata
            if source_filter:
                params['source_filter'] = source_filter
            
            # Execute search using Supabase RPC function
            result = self.client.rpc('match_code_examples', params).execute()
            
            return result.data
        except Exception as e:
            print(f"Error searching code examples: {e}")
            return []
    
    async def delete_code_examples_by_url(self, urls: List[str]) -> None:
        """Delete code examples by URL"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        for url in urls:
            try:
                self.client.table('code_examples').delete().eq('url', url).execute()
            except Exception as e:
                print(f"Error deleting code examples for {url}: {e}")
    
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
            # Try to update existing source
            result = self.client.table('sources').update({
                'summary': summary,
                'total_word_count': word_count,
                'updated_at': 'now()'
            }).eq('source_id', source_id).execute()
            
            # If no rows were updated, insert new source
            if not result.data:
                self.client.table('sources').insert({
                    'source_id': source_id,
                    'summary': summary,
                    'total_word_count': word_count
                }).execute()
                print(f"Created new source: {source_id}")
            else:
                print(f"Updated source: {source_id}")
                
        except Exception as e:
            print(f"Error updating source {source_id}: {e}")
    
    async def get_documents_by_url(self, url: str) -> List[Dict[str, Any]]:
        """Get all document chunks for a specific URL"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        try:
            result = self.client.table('crawled_pages').select('*').eq('url', url).execute()
            return result.data
        except Exception as e:
            print(f"Error getting documents by URL: {e}")
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
            query = self.client.table('crawled_pages')\
                .select('id, url, chunk_number, content, metadata, source_id')\
                .ilike('content', f'%{keyword}%')
            
            if source_filter:
                query = query.eq('source_id', source_filter)
            
            result = query.limit(match_count).execute()
            return result.data
        except Exception as e:
            print(f"Error searching documents by keyword: {e}")
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
            query = self.client.table('code_examples')\
                .select('id, url, chunk_number, content, summary, metadata, source_id')\
                .or_(f'content.ilike.%{keyword}%,summary.ilike.%{keyword}%')
            
            if source_filter:
                query = query.eq('source_id', source_filter)
            
            result = query.limit(match_count).execute()
            return result.data
        except Exception as e:
            print(f"Error searching code examples by keyword: {e}")
            return []

    async def get_sources(self) -> List[Dict[str, Any]]:
        """Get all available sources"""
        if not self.client:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        try:
            result = self.client.table('sources').select('*').order('source_id').execute()
            return result.data
        except Exception as e:
            print(f"Error getting sources: {e}")
            return []
    
    # Private helper methods
    
    async def _delete_documents_batch(self, urls: List[str]) -> None:
        """Delete documents in batch with fallback to individual deletion"""
        try:
            if urls:
                # Try batch deletion
                self.client.table("crawled_pages").delete().in_("url", urls).execute()
        except Exception as e:
            print(f"Batch delete failed: {e}. Trying one-by-one deletion as fallback.")
            # Fallback: delete records one by one
            for url in urls:
                try:
                    self.client.table("crawled_pages").delete().eq("url", url).execute()
                except Exception as inner_e:
                    print(f"Error deleting record for URL {url}: {inner_e}")
    
    async def _insert_with_retry(self, table_name: str, batch_data: List[Dict[str, Any]]) -> None:
        """Insert data with retry logic"""
        retry_delay = self.retry_delay
        
        for retry in range(self.max_retries):
            try:
                self.client.table(table_name).insert(batch_data).execute()
                # Success - break out of retry loop
                break
            except Exception as e:
                if retry < self.max_retries - 1:
                    print(f"Error inserting batch into {table_name} (attempt {retry + 1}/{self.max_retries}): {e}")
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    # Final attempt failed
                    print(f"Failed to insert batch after {self.max_retries} attempts: {e}")
                    # Try inserting records one by one as a last resort
                    print("Attempting to insert records individually...")
                    successful_inserts = 0
                    for record in batch_data:
                        try:
                            self.client.table(table_name).insert(record).execute()
                            successful_inserts += 1
                        except Exception as individual_error:
                            print(f"Failed to insert individual record: {individual_error}")
                    
                    if successful_inserts > 0:
                        print(f"Successfully inserted {successful_inserts}/{len(batch_data)} records individually")