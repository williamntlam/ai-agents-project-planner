from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator, ValidationInfo, ConfigDict
from uuid import UUID, uuid4

class Chunk(BaseModel):
    """Final chunk with embedding, ready for vector database storage."""
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the chunk")
    document_id: str = Field(..., description="Reference to the source document (can be UUID as string or path)")
    chunk_index: int = Field(..., ge=0, description="Zero-based index indicating position in document")
    content: str = Field(..., min_length=1, description="Text content of this chunk")
    embedding: List[float] = Field(..., description="Vector embedding of the chunk content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk-specific metadata")
    content_hash: Optional[str] = Field(default=None, description="Hash of content for deduplication")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when chunk was created")
    

    @field_validator('embedding')
    @classmethod
    def validate_embedding_dimension(cls, v: List[float], info: ValidationInfo) -> List[float]:
        """Validate embedding is not empty and contains only numbers."""
        if not v:
            raise ValueError("Embedding cannot be empty")
        if not all(isinstance(x, (int, float)) for x in v):
            raise ValueError("Embedding must contain only numbers")
        return v

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Ensure content is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Chunk content cannot be empty or whitespace")
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "chunk_index": 0,
                "content": "# Security Standards\n\nAlways use HTTPS for all API communications...",
                "embedding": [0.1, 0.2, -0.3, 0.4, ...],  # 1536 dimensions for OpenAI
                "metadata": {
                    "document_type": "standards",
                    "category": "security",
                    "tags": ["security", "api"],
                    "chunk_size": 512,
                    "overlap": 0
                },
                "content_hash": "abc123def456...",
                "created_at": "2024-01-15T12:02:00Z"
            }
        }
    )

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vector."""
        return len(self.embedding)

    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Safely get metadata value."""
        return self.metadata.get(key, default)