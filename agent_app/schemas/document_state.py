"""Document state schema for LangGraph workflow."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum


class DocumentStatus(str, Enum):
    """Document status enumeration."""
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    FINAL = "FINAL"


class DocumentState(BaseModel):
    """Shared state object for LangGraph workflow."""
    
    # Input
    project_brief: str = Field(..., description="Original project brief/requirements")
    
    # Intermediate outputs
    hld_draft: Optional[str] = Field(None, description="High-Level Design draft")
    lld_draft: Optional[str] = Field(None, description="Low-Level Design draft")
    
    # Review & revision
    review_feedback: Optional[Dict[str, Any]] = Field(None, description="Structured review feedback")
    needs_revision: bool = Field(False, description="Flag set by ReviewerAgent")
    revision_count: int = Field(0, description="Number of revision cycles")
    max_revisions: int = Field(3, description="Maximum allowed revisions")
    
    # Final output
    final_document: Optional[str] = Field(None, description="Final formatted SDD")
    document_status: DocumentStatus = Field(DocumentStatus.DRAFT, description="Document status")
    
    # Metadata
    retrieved_context: Optional[list] = Field(None, description="RAG context chunks used")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)

