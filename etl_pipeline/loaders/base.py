from abc import ABC, abstractmethod
from typing import List, Optional
from etl_pipeline.models.chunk import Chunk
from etl_pipeline.models.document import Document


class BaseLoader(ABC):
    """Abstract base class for all loaders (L in ETL)."""
    
    def __init__(self, config: dict):
        """
        Initialize loader with configuration.
        
        Args:
            config: Configuration dictionary specific to the loader type
        """
        self.config = config
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate that the loader configuration is valid.
        
        Returns:
            bool: True if configuration is valid
        
        Raises:
            ValueError: If configuration is invalid
        """
        pass
    
    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to the target (database, file, etc.).
        
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the target."""
        pass
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class BaseVectorLoader(BaseLoader):
    """Base class for vector database loaders."""
    
    @abstractmethod
    def load_chunks(self, chunks: List[Chunk]) -> None:
        """
        Load chunks into vector database.
        
        Args:
            chunks: List of chunks to load (must have embeddings)
        
        Raises:
            LoadingError: If loading fails
        """
        pass
    
    @abstractmethod
    def upsert_chunks(self, chunks: List[Chunk]) -> None:
        """
        Upsert chunks (insert or update if exists).
        
        Args:
            chunks: List of chunks to upsert
        """
        pass
    
    @abstractmethod
    def get_best_matches(
        self, 
        query_embedding: List[float], 
        top_k: int = 25,
        filters: Optional[dict] = None
    ) -> List[Chunk]:
        """
        Retrieve top-K most similar chunks.
        
        Args:
            query_embedding: Query vector embedding
            top_k: Number of results to return
            filters: Optional metadata filters (e.g., {"category": "security"})
        
        Returns:
            List[Chunk]: Top-K most similar chunks, sorted by similarity
        """
        pass
    
    @abstractmethod
    def create_index_if_not_exists(self) -> None:
        """Create vector index if it doesn't exist."""
        pass


class BaseAuditLoader(BaseLoader):
    """Base class for audit/logging loaders."""
    
    @abstractmethod
    def log_extraction(
        self, 
        source_path: str, 
        status: str, 
        error: Optional[str] = None
    ) -> None:
        """
        Log document extraction event.
        
        Args:
            source_path: Path/URL of extracted document
            status: 'success', 'failed', 'skipped'
            error: Error message if status is 'failed'
        """
        pass
    
    @abstractmethod
    def log_transformation(
        self,
        document_id: str,
        chunks_created: int,
        status: str,
        error: Optional[str] = None
    ) -> None:
        """
        Log document transformation event.
        
        Args:
            document_id: ID of transformed document
            chunks_created: Number of chunks created
            status: 'success', 'failed'
            error: Error message if status is 'failed'
        """
        pass
    
    @abstractmethod
    def log_loading(
        self,
        chunks_loaded: int,
        status: str,
        error: Optional[str] = None
    ) -> None:
        """
        Log chunk loading event.
        
        Args:
            chunks_loaded: Number of chunks loaded
            status: 'success', 'failed'
            error: Error message if status is 'failed'
        """
        pass
    
    def get_last_processed(self, source_path: str) -> Optional[str]:
        """
        Get last processed timestamp for a source path (for incremental updates).
        
        Args:
            source_path: Path to check
        
        Returns:
            Optional[str]: ISO timestamp string or None if never processed
        """
        # Default implementation - override if needed
        return None