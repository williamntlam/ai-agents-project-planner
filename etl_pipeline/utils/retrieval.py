"""Retrieval utilities for semantic search and best match queries."""

import logging
import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from etl_pipeline.models.chunk import Chunk
from etl_pipeline.loaders.vector_loader import PgVectorLoader
from etl_pipeline.transformers.embedder import Embedder
from etl_pipeline.utils.exceptions import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Container for search results with similarity score."""
    chunk: Chunk
    similarity_score: float
    rank: int


class RetrievalUtility:
    """
    High-level retrieval utility for semantic search.
    
    Features:
    - Top-K similarity search (best match)
    - Multiple similarity metrics (cosine, L2, inner product)
    - Metadata filtering
    - Hybrid search (semantic + keyword matching)
    - Query expansion
    - Optional reranking
    """
    
    def __init__(
        self,
        vector_loader: PgVectorLoader,
        embedder: Optional[Embedder] = None
    ):
        """
        Initialize retrieval utility.
        
        Args:
            vector_loader: Initialized PgVectorLoader instance
            embedder: Optional Embedder instance for query embedding (if None, must provide embeddings manually)
        """
        self.vector_loader = vector_loader
        self.embedder = embedder
    
    def get_best_matches(
        self,
        query_embedding: Optional[List[float]] = None,
        query_text: Optional[str] = None,
        top_k: int = 25,
        filters: Optional[Dict[str, Any]] = None,
        similarity_metric: str = "cosine",
        min_similarity: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Find top-K most similar chunks.
        
        Args:
            query_embedding: Vector embedding of the query (required if query_text not provided)
            query_text: Text query to embed (required if query_embedding not provided)
            top_k: Number of results to return (default: 25)
            filters: Optional metadata filters (e.g., {"category": "security", "document_type": "standards"})
            similarity_metric: Similarity metric to use ("cosine", "l2", "inner_product")
            min_similarity: Minimum similarity score threshold (0.0 to 1.0)
        
        Returns:
            List[SearchResult]: Top-K most similar chunks with similarity scores, sorted by similarity
        
        Raises:
            ValidationError: If neither query_embedding nor query_text provided
        """
        # Get query embedding
        if query_embedding is None:
            if query_text is None:
                raise ValidationError(
                    "Either query_embedding or query_text must be provided",
                    field="query"
                )
            if self.embedder is None:
                raise ValidationError(
                    "query_text provided but no embedder available. Provide query_embedding or initialize with embedder.",
                    field="embedder"
                )
            query_embedding = self.embedder.embed(query_text)
        
        # Get results from vector loader (uses cosine similarity)
        chunks = self.vector_loader.get_best_matches(
            query_embedding=query_embedding,
            top_k=top_k * 2 if min_similarity else top_k,  # Get more if filtering by similarity
            filters=filters
        )
        
        # Convert to SearchResult objects with similarity scores
        results = []
        for i, chunk in enumerate(chunks):
            # Calculate similarity score (vector_loader uses cosine)
            similarity = self._calculate_similarity(
                query_embedding,
                chunk.embedding,
                similarity_metric
            )
            
            # Filter by minimum similarity if specified
            if min_similarity is not None and similarity < min_similarity:
                continue
            
            results.append(SearchResult(
                chunk=chunk,
                similarity_score=similarity,
                rank=i + 1
            ))
            
            # Stop if we have enough results
            if len(results) >= top_k:
                break
        
        logger.info(f"Retrieved {len(results)} best matches (top_k={top_k}, min_similarity={min_similarity})")
        return results
    
    def hybrid_search(
        self,
        query_text: str,
        top_k: int = 25,
        filters: Optional[Dict[str, Any]] = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        min_similarity: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Hybrid search combining semantic similarity and keyword matching.
        
        Args:
            query_text: Text query
            top_k: Number of results to return
            filters: Optional metadata filters
            semantic_weight: Weight for semantic similarity (0.0 to 1.0)
            keyword_weight: Weight for keyword matching (0.0 to 1.0, should sum to 1.0 with semantic_weight)
            min_similarity: Minimum combined score threshold
        
        Returns:
            List[SearchResult]: Top-K results with combined scores
        """
        if self.embedder is None:
            raise ValidationError("embedder is required for hybrid search")
        
        # Normalize weights
        total_weight = semantic_weight + keyword_weight
        if total_weight > 0:
            semantic_weight /= total_weight
            keyword_weight /= total_weight
        
        # Get semantic results
        semantic_results = self.get_best_matches(
            query_text=query_text,
            top_k=top_k * 2,  # Get more candidates for reranking
            filters=filters,
            min_similarity=None  # Don't filter yet
        )
        
        # Extract keywords from query
        keywords = self._extract_keywords(query_text)
        
        # Calculate hybrid scores
        hybrid_results = []
        for result in semantic_results:
            # Semantic score (already normalized 0-1)
            semantic_score = result.similarity_score
            
            # Keyword score (0-1 based on keyword matches)
            keyword_score = self._calculate_keyword_score(
                result.chunk.content,
                keywords
            )
            
            # Combined score
            combined_score = (semantic_weight * semantic_score) + (keyword_weight * keyword_score)
            
            # Filter by minimum similarity if specified
            if min_similarity is not None and combined_score < min_similarity:
                continue
            
            # Update result with combined score
            result.similarity_score = combined_score
            hybrid_results.append(result)
        
        # Sort by combined score and limit
        hybrid_results.sort(key=lambda x: x.similarity_score, reverse=True)
        return hybrid_results[:top_k]
    
    def search_with_expansion(
        self,
        query_text: str,
        top_k: int = 25,
        filters: Optional[Dict[str, Any]] = None,
        expansion_terms: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Search with query expansion (adds related terms to query).
        
        Note: This is a simple implementation. For production, consider using
        LLM-based query expansion or synonym dictionaries.
        
        Args:
            query_text: Original query text
            top_k: Number of results to return
            filters: Optional metadata filters
            expansion_terms: Optional list of terms to add to query
        
        Returns:
            List[SearchResult]: Top-K results
        """
        if self.embedder is None:
            raise ValidationError("embedder is required for query expansion")
        
        # Expand query with additional terms
        expanded_query = self._expand_query(query_text, expansion_terms)
        logger.debug(f"Expanded query: '{query_text}' -> '{expanded_query}'")
        
        # Search with expanded query
        return self.get_best_matches(
            query_text=expanded_query,
            top_k=top_k,
            filters=filters
        )
    
    def rerank_results(
        self,
        results: List[SearchResult],
        query_text: str,
        top_k: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Rerank results using keyword matching (simple implementation).
        
        For production, consider using cross-encoders or LLM-based reranking.
        
        Args:
            results: Initial search results
            query_text: Query text for reranking
            top_k: Number of results to return after reranking (None = return all)
        
        Returns:
            List[SearchResult]: Reranked results
        """
        keywords = self._extract_keywords(query_text)
        
        # Calculate keyword scores and adjust similarity
        for result in results:
            keyword_score = self._calculate_keyword_score(result.chunk.content, keywords)
            # Boost similarity if keywords match
            result.similarity_score = result.similarity_score * 0.7 + keyword_score * 0.3
        
        # Resort by updated scores
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        if top_k:
            return results[:top_k]
        return results
    
    def _calculate_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
        metric: str = "cosine"
    ) -> float:
        """
        Calculate similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            metric: Similarity metric ("cosine", "l2", "inner_product")
        
        Returns:
            float: Similarity score (0.0 to 1.0 for cosine, varies for others)
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions must match: {len(vec1)} != {len(vec2)}")
        
        if metric == "cosine":
            # Cosine similarity
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(b * b for b in vec2) ** 0.5
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            return dot_product / (magnitude1 * magnitude2)
        
        elif metric == "l2":
            # L2 distance (convert to similarity: 1 / (1 + distance))
            distance = sum((a - b) ** 2 for a, b in zip(vec1, vec2)) ** 0.5
            return 1.0 / (1.0 + distance)
        
        elif metric == "inner_product":
            # Inner product (dot product)
            return sum(a * b for a, b in zip(vec1, vec2))
        
        else:
            raise ValueError(f"Unknown similarity metric: {metric}")
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text (simple implementation).
        
        Args:
            text: Input text
        
        Returns:
            List[str]: Extracted keywords (lowercased, no stop words)
        """
        # Simple stop words list (expand for production)
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "should", "could", "may", "might", "must", "can", "this",
            "that", "these", "those", "what", "which", "who", "whom", "whose"
        }
        
        # Extract words (alphanumeric, at least 3 characters)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter stop words
        keywords = [w for w in words if w not in stop_words]
        
        return keywords
    
    def _calculate_keyword_score(self, content: str, keywords: List[str]) -> float:
        """
        Calculate keyword matching score (0.0 to 1.0).
        
        Args:
            content: Content to score
            keywords: List of keywords to match
        
        Returns:
            float: Keyword match score (0.0 = no matches, 1.0 = all keywords found)
        """
        if not keywords:
            return 0.0
        
        content_lower = content.lower()
        matches = sum(1 for keyword in keywords if keyword in content_lower)
        
        # Score based on percentage of keywords found
        return matches / len(keywords) if keywords else 0.0
    
    def _expand_query(self, query: str, expansion_terms: Optional[List[str]] = None) -> str:
        """
        Expand query with additional terms.
        
        Args:
            query: Original query
            expansion_terms: Optional list of terms to add
        
        Returns:
            str: Expanded query
        """
        if not expansion_terms:
            # Simple expansion: add synonyms or related terms
            # For production, use LLM or synonym dictionary
            return query
        
        # Combine original query with expansion terms
        expanded = f"{query} {' '.join(expansion_terms)}"
        return expanded


# Convenience functions for easy usage
def get_best_matches(
    vector_loader: PgVectorLoader,
    query_embedding: Optional[List[float]] = None,
    query_text: Optional[str] = None,
    embedder: Optional[Embedder] = None,
    top_k: int = 25,
    filters: Optional[Dict[str, Any]] = None
) -> List[Chunk]:
    """
    Convenience function to get best matches (returns Chunk objects, not SearchResult).
    
    Args:
        vector_loader: Initialized PgVectorLoader
        query_embedding: Query embedding vector
        query_text: Query text (requires embedder)
        embedder: Embedder instance (required if using query_text)
        top_k: Number of results
        filters: Optional metadata filters
    
    Returns:
        List[Chunk]: Top-K most similar chunks
    """
    utility = RetrievalUtility(vector_loader, embedder)
    results = utility.get_best_matches(
        query_embedding=query_embedding,
        query_text=query_text,
        top_k=top_k,
        filters=filters
    )
    return [result.chunk for result in results]


def search_with_filters(
    vector_loader: PgVectorLoader,
    query_embedding: List[float],
    top_k: int = 25,
    document_type: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    **kwargs
) -> List[Chunk]:
    """
    Convenience function for common filtering patterns.
    
    Args:
        vector_loader: Initialized PgVectorLoader
        query_embedding: Query embedding vector
        top_k: Number of results
        document_type: Filter by document type
        category: Filter by category
        tags: Filter by tags (any of the provided tags)
        **kwargs: Additional metadata filters
    
    Returns:
        List[Chunk]: Filtered results
    """
    filters = {}
    if document_type:
        filters["document_type"] = document_type
    if category:
        filters["category"] = category
    if tags:
        # For tags, we'd need to handle array matching in the vector loader
        # For now, just use the first tag
        filters["tags"] = tags[0] if tags else None
    filters.update(kwargs)
    
    return vector_loader.get_best_matches(
        query_embedding=query_embedding,
        top_k=top_k,
        filters=filters if filters else None
    )

