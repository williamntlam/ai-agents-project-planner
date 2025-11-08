from typing import List, Dict, Optional
import os
import time
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

from etl_pipeline.transformers.base import BaseEmbedder
from etl_pipeline.utils.exceptions import EmbeddingError
from etl_pipeline.utils.retry import retry_api_call
from etl_pipeline.utils.hashing import content_hash

# OpenAI client
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

# Optional: sentence-transformers (for future use)
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None


class Embedder(BaseEmbedder):
    """Generates vector embeddings for text using OpenAI or sentence-transformers."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        # Extract configuration
        self.provider = config.get("provider", "openai")
        self.model = config.get("model", "text-embedding-3-small")
        self.dimension = int(config.get("dimension", 1536))
        self.batch_size = int(config.get("batch_size", 100))
        self.max_retries = int(config.get("max_retries", 3))
        self.timeout_seconds = int(config.get("timeout_seconds", 30))
        self.enabled = config.get("enabled", True)
        
        # Parallel processing configuration
        self.parallel_processing = config.get("parallel_processing", False)
        self.max_workers = int(config.get("max_workers", 5))
        
        # Get API key
        api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key or api_key.startswith("${"):
            # Try to get from environment
            api_key = os.getenv("OPENAI_API_KEY")
        self.api_key = api_key
        
        # Initialize client based on provider
        self._client = None
        self._sentence_transformer = None
        self._initialize_client()
        
        # Optional: Embedding cache (simple in-memory cache)
        self._cache: Dict[str, List[float]] = {}
        self._use_cache = config.get("cache_enabled", False)
        
        # Validate configuration
        self.validate_config()
    
    def _initialize_client(self):
        """Initialize the embedding client based on provider."""
        if self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ValueError(
                    "OpenAI provider requires 'openai' library. "
                    "Install with: pip install openai"
                )
            if not self.api_key:
                raise ValueError(
                    "OpenAI API key is required. "
                    "Set OPENAI_API_KEY environment variable or provide in config."
                )
            self._client = OpenAI(api_key=self.api_key, timeout=self.timeout_seconds)
        
        elif self.provider == "sentence-transformers":
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ValueError(
                    "sentence-transformers provider requires 'sentence-transformers' library. "
                    "Install with: pip install sentence-transformers"
                )
            try:
                self._sentence_transformer = SentenceTransformer(self.model)
            except Exception as e:
                raise ValueError(f"Failed to load sentence-transformer model {self.model}: {e}")
        
        else:
            raise ValueError(f"Unknown provider: {self.provider}. Supported: 'openai', 'sentence-transformers'")
    
    def validate_config(self) -> bool:
        """Validate embedder configuration."""
        if not self.enabled:
            return True
        
        if self.dimension <= 0:
            raise ValueError("dimension must be > 0")
        
        if self.batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        
        return True
    
    @retry_api_call(max_attempts=3, wait_seconds=1.0)
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
        
        Returns:
            List[float]: Embedding vector
        
        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not self.enabled:
            raise EmbeddingError("Embedder is disabled")
        
        if not text or not text.strip():
            raise EmbeddingError("Text cannot be empty")
        
        # Check cache first
        if self._use_cache:
            text_hash = content_hash(text)
            if text_hash in self._cache:
                return self._cache[text_hash]
        
        try:
            if self.provider == "openai":
                embedding = self._embed_openai(text)
            elif self.provider == "sentence-transformers":
                embedding = self._embed_sentence_transformers(text)
            else:
                raise EmbeddingError(f"Unknown provider: {self.provider}")
            
            # Cache the embedding
            if self._use_cache:
                text_hash = content_hash(text)
                self._cache[text_hash] = embedding
            
            # Validate dimension
            if len(embedding) != self.dimension:
                raise EmbeddingError(
                    f"Embedding dimension mismatch: expected {self.dimension}, got {len(embedding)}",
                    model=self.model
                )
            
            return embedding
            
        except EmbeddingError:
            raise
        except Exception as e:
            raise EmbeddingError(
                f"Failed to generate embedding: {e}",
                model=self.model
            )
    
    def _embed_openai(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        try:
            response = self._client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimension
            )
            
            # Extract embedding from response
            embedding = response.data[0].embedding
            
            return embedding
            
        except Exception as e:
            # Handle specific OpenAI errors
            error_msg = str(e)
            if "rate limit" in error_msg.lower():
                raise EmbeddingError(
                    f"OpenAI rate limit exceeded: {e}",
                    model=self.model,
                    error_code="RATE_LIMIT"
                )
            elif "invalid" in error_msg.lower() or "401" in error_msg:
                raise EmbeddingError(
                    f"OpenAI API error: {e}",
                    model=self.model,
                    error_code="API_ERROR"
                )
            else:
                raise EmbeddingError(
                    f"OpenAI embedding failed: {e}",
                    model=self.model
                )
    
    def _embed_sentence_transformers(self, text: str) -> List[float]:
        """Generate embedding using sentence-transformers."""
        try:
            embedding = self._sentence_transformer.encode(text, convert_to_numpy=False)
            return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
        except Exception as e:
            raise EmbeddingError(
                f"sentence-transformers embedding failed: {e}",
                model=self.model
            )
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with batch optimization.
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List[List[float]]: List of embedding vectors
        """
        if not texts:
            return []
        
        if self.provider == "openai":
            return self._embed_batch_openai(texts)
        elif self.provider == "sentence-transformers":
            return self._embed_batch_sentence_transformers(texts)
        else:
            # Fallback to individual embeddings
            return [self.embed(text) for text in texts]
    
    def _embed_batch_openai(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batches using OpenAI API."""
        if self.parallel_processing:
            return self._embed_batch_openai_parallel(texts)
        else:
            return self._embed_batch_openai_sequential(texts)
    
    def _embed_batch_openai_sequential(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batches sequentially (original implementation)."""
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            try:
                response = self._client.embeddings.create(
                    model=self.model,
                    input=batch,
                    dimensions=self.dimension
                )
                
                # Extract embeddings from response
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
                # Small delay between batches to avoid rate limits
                if i + self.batch_size < len(texts):
                    time.sleep(0.1)
                    
            except Exception as e:
                # If batch fails, fall back to individual embeddings
                for text in batch:
                    try:
                        embedding = self.embed(text)
                        all_embeddings.append(embedding)
                    except Exception as individual_error:
                        # Log error but continue with other texts
                        raise EmbeddingError(
                            f"Failed to embed text in batch: {individual_error}",
                            model=self.model
                        )
        
        return all_embeddings
    
    def _embed_batch_openai_parallel(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batches using parallel processing."""
        # Split texts into batches with indices
        batches = {}
        batch_idx = 0
        for i in range(0, len(texts), self.batch_size):
            batches[batch_idx] = texts[i:i + self.batch_size]
            batch_idx += 1
        
        # Store results with their original indices to maintain order
        results = {}
        
        # Process batches in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batch tasks
            future_to_batch = {
                executor.submit(self._process_single_batch, batch_texts, idx): idx
                for idx, batch_texts in batches.items()
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_embeddings = future.result()
                    results[batch_idx] = batch_embeddings
                except Exception as e:
                    # If batch fails, fall back to individual embeddings for that batch
                    batch_texts = batches[batch_idx]
                    individual_embeddings = []
                    for text in batch_texts:
                        try:
                            embedding = self.embed(text)
                            individual_embeddings.append(embedding)
                        except Exception:
                            raise EmbeddingError(
                                f"Failed to embed batch {batch_idx}: {e}",
                                model=self.model
                            )
                    results[batch_idx] = individual_embeddings
        
        # Reconstruct embeddings in original order
        all_embeddings = []
        for batch_idx in sorted(results.keys()):
            all_embeddings.extend(results[batch_idx])
        
        return all_embeddings
    
    def _process_single_batch(self, batch_texts: List[str], batch_idx: int) -> List[List[float]]:
        """
        Process a single batch of texts.
        Used by parallel processing.
        
        Args:
            batch_texts: List of texts in this batch
            batch_idx: Batch index (for ordering)
        
        Returns:
            List[List[float]]: Embeddings for this batch
        """
        try:
            response = self._client.embeddings.create(
                model=self.model,
                input=batch_texts,
                dimensions=self.dimension
            )
            
            # Extract embeddings from response
            batch_embeddings = [item.embedding for item in response.data]
            return batch_embeddings
            
        except Exception as e:
            # Re-raise to be handled by caller
            raise EmbeddingError(
                f"Failed to process batch {batch_idx}: {e}",
                model=self.model
            )
    
    def _embed_batch_sentence_transformers(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batches using sentence-transformers."""
        try:
            embeddings = self._sentence_transformer.encode(
                texts,
                batch_size=self.batch_size,
                convert_to_numpy=False,
                show_progress_bar=False
            )
            
            # Convert to list of lists
            if hasattr(embeddings, 'tolist'):
                return [emb.tolist() if hasattr(emb, 'tolist') else list(emb) for emb in embeddings]
            else:
                return [list(emb) for emb in embeddings]
                
        except Exception as e:
            raise EmbeddingError(
                f"sentence-transformers batch embedding failed: {e}",
                model=self.model
            )
    
    def embed_chunks(self, chunks: List) -> List:
        """
        Embed a list of Chunk objects (convenience method).
        
        Args:
            chunks: List of Chunk objects (with content but empty embedding)
        
        Returns:
            List[Chunk]: Chunks with embeddings filled in
        """
        if not chunks:
            return []
        
        # Extract texts
        texts = [chunk.content for chunk in chunks]
        
        # Generate embeddings in batch
        embeddings = self.embed_batch(texts)
        
        # Update chunks with embeddings
        embedded_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            # Create new chunk with embedding
            from models.chunk import Chunk
            embedded_chunk = Chunk(
                id=chunk.id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=embedding,
                metadata=chunk.metadata,
                content_hash=chunk.content_hash,
                created_at=chunk.created_at,
            )
            embedded_chunks.append(embedded_chunk)
        
        return embedded_chunks
    
    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()
    
    def get_cache_size(self) -> int:
        """Get the number of cached embeddings."""
        return len(self._cache)
