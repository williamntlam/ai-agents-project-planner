"""RAG Tool - Vector database retrieval for context."""

from typing import List, Dict, Any, Optional
from agent_app.utils.logging import setup_logging


class RAGTool:
    """Tool for retrieving context from vector database."""
    
    def __init__(self, vector_db_connection, embedder, config: Dict[str, Any]):
        """
        Initialize RAG tool.
        
        Args:
            vector_db_connection: Database connection (from etl_pipeline or shared)
            embedder: Embedding model (same as used in ETL)
            config: Tool configuration (top_k, similarity_threshold, etc.)
        """
        self.db = vector_db_connection
        self.embedder = embedder
        self.config = config
        self.logger = setup_logging()
    
    def retrieve_context(
        self, 
        query: str, 
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context chunks for a query.
        
        Args:
            query: Search query text
            top_k: Number of chunks to retrieve (defaults to config value)
            filters: Optional metadata filters (e.g., {"document_type": "standards"})
            
        Returns:
            List of chunk dictionaries with content, metadata, similarity score
        """
        try:
            # Use top_k from parameter or config
            if top_k is None:
                top_k = self.config.get("top_k", 25)
            
            # Get similarity threshold from config
            similarity_threshold = self.config.get("similarity_threshold", 0.0)
            
            # 1. Generate query embedding
            self.logger.debug("Generating query embedding", query_length=len(query))
            query_embedding = self.embedder.embed(query)
            
            # 2. Execute similarity search using vector DB connection
            # The vector_db_connection should be a PgVectorLoader instance with get_best_matches method
            if not hasattr(self.db, 'get_best_matches'):
                self.logger.error(
                    "Vector DB connection does not have get_best_matches method",
                    connection_type=type(self.db).__name__
                )
                return []
            
            # Ensure database is connected
            if hasattr(self.db, 'connect') and not hasattr(self.db, '_connection'):
                self.db.connect()
            elif hasattr(self.db, 'connect') and self.db._connection is None:
                self.db.connect()
            
            # 3. Retrieve best matches (returns tuples of (Chunk, similarity_score))
            self.logger.debug(
                "Retrieving context chunks",
                top_k=top_k,
                filters=filters
            )
            chunk_results = self.db.get_best_matches(
                query_embedding=query_embedding,
                top_k=top_k,
                filters=filters
            )
            
            # 4. Convert (Chunk, similarity) tuples to dictionaries
            # Similarity is already calculated in SQL and returned by get_best_matches
            results = []
            for chunk, similarity in chunk_results:
                # Apply similarity threshold filter
                if similarity < similarity_threshold:
                    continue
                
                # Convert Chunk to dictionary format
                result = {
                    "content": chunk.content,
                    "metadata": chunk.metadata,
                    "similarity": similarity,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "id": str(chunk.id) if chunk.id else None,
                }
                results.append(result)
            
            self.logger.info(
                "Retrieved context chunks",
                query_length=len(query),
                chunks_found=len(chunk_results),
                chunks_after_threshold=len(results),
                similarity_threshold=similarity_threshold
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "Error retrieving context",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            return []
    
    def format_context_for_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into prompt-friendly context."""
        if not chunks:
            return ""
        
        formatted = []
        for i, chunk in enumerate(chunks, 1):
            formatted.append(
                f"[Context {i}] (Similarity: {chunk.get('similarity', 0):.3f})\n"
                f"Source: {chunk.get('metadata', {}).get('source', 'unknown')}\n"
                f"Content: {chunk['content']}\n"
            )
        return "\n---\n".join(formatted)

