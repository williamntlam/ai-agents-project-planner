"""Review feedback schema for ReviewerAgent."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any
from enum import Enum


class ReviewSeverity(str, Enum):
    """Review issue severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ReviewIssue(BaseModel):
    """Individual review issue/feedback item."""
    
    category: str = Field(..., description="Issue category (e.g., 'architecture', 'security')")
    severity: ReviewSeverity = Field(..., description="Issue severity")
    description: str = Field(..., description="Detailed description of the issue")
    suggestion: Optional[str] = Field(None, description="Suggested fix")
    location: Optional[str] = Field(None, description="Where in document (section, line)")


class ReviewFeedback(BaseModel):
    """Structured review feedback from ReviewerAgent."""
    
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    passes_validation: bool = Field(..., description="Whether document passes JSON Schema validation")
    issues: List[ReviewIssue] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    needs_revision: bool = Field(..., description="Whether revision is required")

