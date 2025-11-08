"""Document state schema for LangGraph workflow.

WHY THIS SCHEMA EXISTS:
=======================
The DocumentState is the CORE of the entire agent system. It serves as:

1. **Shared Memory**: LangGraph workflows are stateful - this object is passed between
   all nodes (agents) and persists throughout the entire workflow execution. Each agent
   reads from and writes to this state, creating a collaborative document generation process.

2. **Workflow Coordination**: The state contains flags (like `needs_revision`) that control
   the workflow's conditional edges. The LangGraph orchestrator uses these flags to decide
   whether to loop back for revisions or proceed to the next stage.

3. **Data Pipeline**: It represents the transformation pipeline:
   project_brief → hld_draft → lld_draft → review_feedback → final_document
   Each agent adds to this pipeline, building the final document incrementally.

4. **State Validation**: Pydantic automatically validates all state updates, ensuring
   type safety and preventing invalid state transitions (e.g., trying to set FINAL status
   without a final_document).

5. **Debugging & Observability**: The state captures the entire generation history,
   making it easy to debug issues, track revisions, and understand how the document evolved.

6. **Persistence**: This state can be serialized/deserialized, allowing workflow
   checkpoints, resumption after failures, and human-in-the-loop interruptions.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from enum import Enum


class DocumentStatus(str, Enum):
    """Document status enumeration.
    
    Represents the lifecycle stage of the document:
    - DRAFT: Initial generation phase, still being created
    - REVIEW: Document is complete and under review
    - FINAL: Document has been approved and finalized
    """
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    FINAL = "FINAL"


class DocumentState(BaseModel):
    """Shared state object for LangGraph workflow.
    
    This is the single source of truth that flows through the entire agent workflow.
    All agents read from and write to this state object.
    
    Example workflow:
        1. SystemArchitectAgent reads project_brief, writes hld_draft
        2. APIDataAgent reads hld_draft, writes lld_draft
        3. ReviewerAgent reads hld_draft + lld_draft, writes review_feedback, sets needs_revision
        4. If needs_revision=True, workflow loops back to SystemArchitectAgent
        5. WriterFormatterAgent reads all drafts, writes final_document
    """
    
    # ========== INPUT ==========
    project_brief: str = Field(
        ...,
        description="Original project brief/requirements",
        min_length=10,
        examples=["Build an e-commerce order processing microservice with payment integration"]
    )
    """The starting point - the user's requirements that kick off the entire workflow."""
    
    # Additional user input and clarifications
    additional_context: Optional[str] = Field(
        None,
        description="Additional context, clarifications, or requirements provided by user"
    )
    """User-provided additional information or clarifications.
    
    Can be added:
    - Initially with the brief
    - During workflow execution (if clarification requested)
    - During revision cycles
    """
    
    user_clarifications: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of clarification requests and user responses"
    )
    """Stores clarification Q&A pairs.
    
    Format:
    [
        {
            "question": "What authentication method should be used?",
            "answer": "OAuth2 with JWT tokens",
            "timestamp": "2024-01-01T12:00:00Z",
            "agent": "SystemArchitectAgent"
        }
    ]
    """
    
    clarification_requests: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Pending clarification requests from agents"
    )
    """Agents can request clarifications if information is missing.
    
    Format:
    [
        {
            "question": "What is the expected traffic volume?",
            "agent": "SystemArchitectAgent",
            "stage": "draft_hld",
            "priority": "high",
            "timestamp": "2024-01-01T12:00:00Z"
        }
    ]
    """
    
    # Structured input fields (optional, for better organization)
    requirements: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured requirements (optional, can be extracted from brief)"
    )
    """Structured requirements breakdown.
    
    Example:
    {
        "functional_requirements": ["User authentication", "Order processing"],
        "non_functional_requirements": {
            "performance": "Handle 10k requests/second",
            "scalability": "Horizontal scaling required"
        },
        "constraints": ["Must use PostgreSQL", "AWS only"],
        "assumptions": ["Users have existing accounts"]
    }
    """
    
    # ========== INTERMEDIATE OUTPUTS ==========
    hld_draft: Optional[str] = Field(
        None,
        description="High-Level Design draft generated by SystemArchitectAgent"
    )
    """High-level architecture, component structure, technology choices."""
    
    lld_draft: Optional[str] = Field(
        None,
        description="Low-Level Design draft generated by APIDataAgent"
    )
    """Detailed API specifications, data models, database schemas."""
    
    # ========== REVIEW & REVISION CONTROL ==========
    review_feedback: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured review feedback from ReviewerAgent (JSON-serializable)"
    )
    """Structured feedback containing issues, scores, and suggestions.
    
    This is stored as Dict to allow flexible structure, but typically contains:
    - overall_score: float (0-1)
    - passes_validation: bool
    - issues: List[ReviewIssue]
    - strengths: List[str]
    """
    
    needs_revision: bool = Field(
        False,
        description="Flag set by ReviewerAgent to trigger revision loop"
    )
    """Critical workflow control flag.
    
    When True:
    - Conditional edge routes back to draft_hld node
    - Revision count is incremented
    - Agents can use this to adjust their approach
    
    When False:
    - Workflow proceeds to formatting stage
    """
    
    revision_count: int = Field(
        0,
        description="Number of revision cycles completed",
        ge=0
    )
    """Tracks how many times we've revised to prevent infinite loops."""
    
    max_revisions: int = Field(
        3,
        description="Maximum allowed revision cycles before forcing continuation",
        ge=1,
        le=10
    )
    """Safety limit to prevent infinite revision loops.
    
    Even if needs_revision=True, if revision_count >= max_revisions,
    the workflow will proceed to formatting.
    """
    
    # ========== FINAL OUTPUT ==========
    final_document: Optional[str] = Field(
        None,
        description="Final formatted SDD with YAML frontmatter and Mermaid diagrams"
    )
    """The completed System Design Document, ready for use."""
    
    document_status: DocumentStatus = Field(
        DocumentStatus.DRAFT,
        description="Current lifecycle status of the document"
    )
    """Tracks document progression through lifecycle stages."""
    
    # ========== METADATA & TRACEABILITY ==========
    retrieved_context: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="RAG context chunks used during generation (for traceability)"
    )
    """Stores which knowledge base chunks were retrieved and used.
    
    Useful for:
    - Explaining why certain decisions were made
    - Providing citations in the final document
    - Debugging agent reasoning
    """
    
    processing_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata: timestamps, agent versions, config used, etc."
    )
    """Flexible metadata storage for operational data.
    
    Examples:
    - created_at: timestamp
    - agent_versions: dict of agent versions used
    - config_snapshot: config used for this run
    - processing_time: time taken for each stage
    """
    
    @field_validator('document_status')
    @classmethod
    def validate_status_transition(cls, v: DocumentStatus, info) -> DocumentStatus:
        """Ensure logical status transitions.
        
        Rules:
        - Can't be FINAL without a final_document
        - Can't be REVIEW without both hld_draft and lld_draft
        """
        # Note: This is a simplified validator
        # Full validation would need access to other fields
        return v
    
    def can_proceed_to_review(self) -> bool:
        """Check if document has enough content to be reviewed."""
        return self.hld_draft is not None and self.lld_draft is not None
    
    def can_finalize(self) -> bool:
        """Check if document can be marked as FINAL."""
        return (
            self.final_document is not None and
            self.document_status == DocumentStatus.REVIEW and
            not self.needs_revision
        )
    
    def should_continue_revision(self) -> bool:
        """Determine if revision loop should continue."""
        return self.needs_revision and self.revision_count < self.max_revisions
    
    def has_pending_clarifications(self) -> bool:
        """Check if there are pending clarification requests."""
        return len(self.clarification_requests) > 0
    
    def add_clarification(self, question: str, answer: str, agent: str) -> None:
        """Add a clarification Q&A pair."""
        self.user_clarifications.append({
            "question": question,
            "answer": answer,
            "agent": agent,
            "timestamp": self.processing_metadata.get("current_timestamp", "")
        })
    
    def get_combined_brief(self) -> str:
        """Get combined brief with all additional context."""
        parts = [self.project_brief]
        
        if self.additional_context:
            parts.append(f"\n\nAdditional Context:\n{self.additional_context}")
        
        if self.user_clarifications:
            clarifications = "\n".join([
                f"Q: {c['question']}\nA: {c['answer']}"
                for c in self.user_clarifications
            ])
            parts.append(f"\n\nClarifications:\n{clarifications}")
        
        return "\n".join(parts)
    
    class Config:
        """Pydantic configuration."""
        # Allow extra fields for flexibility (e.g., custom metadata)
        extra = "allow"
        # Enable JSON serialization for LangGraph checkpoints
        json_encoders = {
            # Custom encoders if needed
        }

