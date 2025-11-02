from datetime import datetime
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4

class RawDocument(BaseModel):
    """Extracted document before transformation (E in ETL)."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the raw document")
    source: str = Field(..., description="Source path/URL (filesystem path, GitHub URL, S3 key, etc.)")
    content: str = Field(..., description="Raw text content extracted from the file")
    content_type: str = Field(..., description="MIME type or file extension (e.g., 'text/markdown', '.pdf')")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Source-specific metadata (file size, last modified, etc.)")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when document was extracted")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "source": "/data/standards/security.md",
                "content": "# Security Standards\n\nAlways use HTTPS...",
                "content_type": "text/markdown",
                "metadata": {
                    "file_size": 1024,
                    "last_modified": "2024-01-15T10:30:00Z"
                },
                "extracted_at": "2024-01-15T12:00:00Z"
            }
        }
    )

class Document(BaseModel):
    """Normalized document after transformation (ready for chunking)."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the document")
    source: str = Field(..., description="Source path/URL")
    content: str = Field(..., description="Cleaned and normalized text content")
    content_type: str = Field(..., description="Document type after normalization")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Enriched metadata (tags, categories, etc.)")
    extracted_at: datetime = Field(..., description="Original extraction timestamp")
    normalized_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when document was normalized")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "source": "/data/standards/security.md",
                "content": "# Security Standards\n\nAlways use HTTPS...",
                "content_type": "markdown",
                "metadata": {
                    "category": "security",
                    "tags": ["security", "standards"],
                    "title": "Security Standards"
                },
                "extracted_at": "2024-01-15T12:00:00Z",
                "normalized_at": "2024-01-15T12:01:00Z"
            }
        }
    )

    def get_content_length(self) -> int:
        """Get character count of content."""
        return len(self.content)

    def has_tag(self, tag: str) -> bool:
        """Check if document has a specific tag."""
        tags = self.metadata.get("tags", [])
        return tag.lower() in [t.lower() for t in tags]