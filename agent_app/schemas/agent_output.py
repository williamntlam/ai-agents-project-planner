"""Standard output format for all agents."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class AgentOutput(BaseModel):
    """Standard output format for all agents."""
    
    content: str = Field(..., description="Generated content")
    reasoning: Optional[str] = Field(None, description="Agent's reasoning process")
    sources: Optional[list] = Field(None, description="Sources/context used")
    confidence: Optional[float] = Field(None, description="Confidence score (0-1)")
    metadata: Dict[str, Any] = Field(default_factory=dict)

