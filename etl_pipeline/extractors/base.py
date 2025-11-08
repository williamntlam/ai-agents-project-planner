from abc import ABC, abstractmethod
from typing import Iterator
from etl_pipeline.models.document import RawDocument

class BaseExtractor(ABC):
    """Abstract base class for all extractors (E in ETL)."""

    def __init__(self, config: dict):
        """
        Initialize extractor with configuration.
        
        Args:
            config: Configuration dictionary specific to the extractor type
        """
        self.config = config

    @abstractmethod
    def extract(self) -> Iterator[RawDocument]:
        """
        Extract raw documents from the source.
        
        Yields:
            RawDocument: Extracted raw document (not yet transformed)
        
        Raises:
            ExtractionError: If extraction fails
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate that the extractor configuration is valid.
        
        Returns:
            bool: True if configuration is valid
        
        Raises:
            ValueError: If configuration is invalid
        """
        pass
    
    def __iter__(self):
        """Make extractor iterable."""
        return self.extract()