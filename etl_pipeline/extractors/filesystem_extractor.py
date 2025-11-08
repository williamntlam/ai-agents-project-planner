from pathlib import Path
from typing import Iterator, Set
from datetime import datetime
import os

from etl_pipeline.models.document import RawDocument
from etl_pipeline.extractors.base import BaseExtractor
from etl_pipeline.utils.exceptions import ExtractionError


class FilesystemExtractor(BaseExtractor):
    """Extracts documents from local filesystem."""
    
    def __init__(self, config: dict):
        """
        Initialize filesystem extractor.
        
        Args:
            config: Configuration dictionary with keys:
                - base_path: Root directory to scan
                - extensions: List of file extensions to include
                - recursive: Whether to scan subdirectories
                - max_file_size_mb: Maximum file size in MB
                - enabled: Whether extractor is enabled
        """
        super().__init__(config)
        
        # Extract configuration
        base_path_str = config.get("base_path", "./data")
        self.base_path = Path(base_path_str)
        
        # If path is relative, try to resolve it relative to project root
        # Project root is parent of etl_pipeline directory
        if not self.base_path.is_absolute():
            # Try to find project root (parent of etl_pipeline)
            current_file = Path(__file__).resolve()
            etl_pipeline_dir = current_file.parent.parent  # Go up from extractors/ to etl_pipeline/
            project_root = etl_pipeline_dir.parent  # Go up from etl_pipeline/ to project root
            # Resolve path relative to project root
            resolved_path = (project_root / self.base_path).resolve()
            if resolved_path.exists():
                self.base_path = resolved_path
            # Otherwise, keep original path (will be resolved relative to current working directory)
        self.extensions: Set[str] = {
            ext.lower() for ext in config.get("extensions", [".md", ".txt"])
        }
        self.recursive = config.get("recursive", True)
        self.max_file_size_mb = config.get("max_file_size_mb", 50)
        self.enabled = config.get("enabled", True)
        
        # Validate configuration if enabled
        if self.enabled:
            self.validate_config()
    
    def validate_config(self) -> bool:
        """
        Validate that the extractor configuration is valid.
        
        Returns:
            bool: True if configuration is valid
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Check base_path exists
        if not self.base_path.exists():
            raise ValueError(
                f"Base path does not exist: {self.base_path}. "
                f"Please create the directory or update the config."
            )
        
        # Check base_path is a directory
        if not self.base_path.is_dir():
            raise ValueError(
                f"Base path is not a directory: {self.base_path}. "
                f"Please provide a directory path."
            )
        
        # Check extensions list is not empty
        if not self.extensions:
            raise ValueError(
                "Extensions list cannot be empty. "
                "Please specify at least one file extension."
            )
        
        # Check max_file_size_mb is positive
        if self.max_file_size_mb <= 0:
            raise ValueError(
                f"max_file_size_mb must be positive, got {self.max_file_size_mb}"
            )
        
        return True
    
    def extract(self) -> Iterator[RawDocument]:
        """
        Extract raw documents from filesystem.
        
        Yields:
            RawDocument: Extracted raw document
        
        Raises:
            ExtractionError: If extraction fails
        """
        if not self.enabled:
            return
        
        try:
            # Walk directory tree
            if self.recursive:
                # Use rglob to search recursively
                files = self.base_path.rglob("*")
            else:
                # Use glob to search only top level
                files = self.base_path.glob("*")
            
            # Process each file
            for file_path in files:
                try:
                    # Check if file should be processed
                    if not self._should_process_file(file_path):
                        continue
                    
                    # Read file and create RawDocument
                    raw_doc = self._read_file(file_path)
                    yield raw_doc
                    
                except ExtractionError as e:
                    # Log extraction errors but continue processing other files
                    # This allows the pipeline to continue even if individual files fail
                    print(f"Warning: Extraction failed for {file_path}: {e}")
                    continue
                except Exception as e:
                    # Log and skip other errors
                    # In production, you'd want to log this
                    print(f"Warning: Skipping file {file_path}: {e}")
                    continue
                    
        except Exception as e:
            raise ExtractionError(
                f"Failed to extract from filesystem: {e}",
                source_path=str(self.base_path),
                error_code="EXTRACTION_FAILED"
            )
    
    def _should_process_file(self, file_path: Path) -> bool:
        """
        Check if a file should be processed.
        
        Args:
            file_path: Path to file to check
        
        Returns:
            bool: True if file should be processed
        """
        # Skip if not a file (might be a directory)
        if not file_path.is_file():
            return False
        
        # Check extension matches
        file_ext = file_path.suffix.lower()
        if file_ext not in self.extensions:
            return False
        
        # Check file size
        try:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                return False
        except OSError:
            # Can't read file stats, skip it
            return False
        
        return True
    
    def _read_file(self, file_path: Path) -> RawDocument:
        """
        Read file and create RawDocument.
        
        Args:
            file_path: Path to file to read
        
        Returns:
            RawDocument: Document created from file
        
        Raises:
            ExtractionError: If file cannot be read
        """
        try:
            # Read file content
            # Try UTF-8 first, then try other encodings
            content = self._read_file_content(file_path)
            
            # Get file metadata
            file_stat = file_path.stat()
            file_size_mb = file_stat.st_size / (1024 * 1024)
            
            metadata = {
                "file_size": file_stat.st_size,
                "file_size_mb": round(file_size_mb, 2),
                "last_modified": datetime.fromtimestamp(
                    file_stat.st_mtime
                ).isoformat(),
                "file_name": file_path.name,
                "file_path": str(file_path),
                "file_extension": file_path.suffix,
            }
            
            # Determine content type
            content_type = self._get_content_type(file_path.suffix)
            
            # Create RawDocument
            raw_doc = RawDocument(
                source=str(file_path),
                content=content,
                content_type=content_type,
                metadata=metadata
            )
            
            return raw_doc
            
        except UnicodeDecodeError as e:
            raise ExtractionError(
                f"Failed to decode file {file_path}: {e}",
                source_path=str(file_path),
                error_code="DECODE_ERROR"
            )
        except Exception as e:
            raise ExtractionError(
                f"Failed to read file {file_path}: {e}",
                source_path=str(file_path),
                error_code="FILE_READ_ERROR"
            )
    
    def _read_file_content(self, file_path: Path) -> str:
        """
        Read file content, trying multiple encodings.
        
        Args:
            file_path: Path to file
        
        Returns:
            str: File content as string
        
        Raises:
            UnicodeDecodeError: If file cannot be decoded
        """
        # List of encodings to try
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        
        # If all encodings fail, raise error
        raise UnicodeDecodeError(
            'utf-8',
            b'',
            0,
            1,
            f"Could not decode file {file_path} with any encoding"
        )
    
    def _get_content_type(self, extension: str) -> str:
        """
        Map file extension to MIME content type.
        
        Args:
            extension: File extension (e.g., ".md", ".pdf")
        
        Returns:
            str: MIME content type
        """
        mapping = {
            ".md": "text/markdown",
            ".markdown": "text/markdown",
            ".txt": "text/plain",
            ".text": "text/plain",
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".py": "text/x-python",
            ".js": "text/javascript",
            ".json": "application/json",
            ".yaml": "text/yaml",
            ".yml": "text/yaml",
            ".xml": "application/xml",
            ".html": "text/html",
            ".css": "text/css",
        }
        
        return mapping.get(extension.lower(), "application/octet-stream")