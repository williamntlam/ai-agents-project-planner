from abc import ABC, abstractmethod
from typing import List
from models.document import RawDocument, Document
from models.chunk import Chunk


class BaseTransformer(ABC):
    """Abstract base class for all transformers (T in ETL)."""
    
    def __init__(self, config: dict):
        """
        Initialize transformer with configuration.
        
        Args:
            config: Configuration dictionary specific to the transformer type
        """
        self.config = config
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate that the transformer configuration is valid.
        
        Returns:
            bool: True if configuration is valid
        
        Raises:
            ValueError: If configuration is invalid
        """
        pass


class BaseNormalizer(BaseTransformer):
    """Base class for document normalization."""
    
    @abstractmethod
    def normalize(self, raw_document: RawDocument) -> Document:
        """
        Normalize a raw document (convert to clean Document).
        
        Args:
            raw_document: Raw document from extractor
        
        Returns:
            Document: Normalized and cleaned document
        
        Raises:
            TransformationError: If normalization fails
        """
        pass


class BaseChunker(BaseTransformer):
    """Base class for text chunking."""
    
    @abstractmethod
    def chunk(self, document: Document) -> List[Chunk]:
        """
        Split a document into chunks.
        
        Args:
            document: Normalized document to chunk
        
        Returns:
            List[Chunk]: List of chunks (without embeddings yet)
        
        Raises:
            TransformationError: If chunking fails
        """
        pass


class BaseEmbedder(BaseTransformer):
    """Base class for generating embeddings."""
    
    @abstractmethod
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
        pass
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (may be overridden for batch optimization).
        
        Args:
            texts: List of texts to embed
        
        Returns:
            List[List[float]]: List of embedding vectors
        
        Default implementation calls embed() for each text.
        Override this method if your embedder supports batch operations.
        """
        return [self.embed(text) for text in texts]


class BaseMetadataEnricher(BaseTransformer):
    """Base class for metadata enrichment."""
    
    @abstractmethod
    def enrich(self, document: Document) -> Document:
        """
        Enrich document metadata with additional information.
        
        Args:
            document: Document to enrich
        
        Returns:
            Document: Document with enriched metadata
        """
        pass
    
    @abstractmethod
    def enrich_chunk(self, chunk: Chunk, document: Document) -> Chunk:
        """
        Enrich chunk metadata.
        
        Args:
            chunk: Chunk to enrich
            document: Source document for context
        
        Returns:
            Chunk: Chunk with enriched metadata
        """
        pass