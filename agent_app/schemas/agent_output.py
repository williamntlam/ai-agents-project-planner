"""Standard output format for all agents.

WHY THIS SCHEMA EXISTS:
=======================
The AgentOutput provides a UNIFORM INTERFACE for all agents, regardless of their
specific function. This is critical for:

1. **Polymorphism**: All agents (SystemArchitect, APIData, Reviewer, WriterFormatter)
   return the same type, allowing the orchestrator to handle them uniformly. This is
   the Strategy Pattern in action - different strategies (agents) with the same interface.

2. **Consistency**: Every agent must provide at minimum a `content` field, ensuring
   the workflow always has something to work with. Optional fields allow agents to
   provide additional context when available.

3. **Observability**: The `reasoning` and `sources` fields enable transparency into
   how each agent made its decisions, which is crucial for debugging and trust.

4. **Quality Control**: The `confidence` score allows the workflow to make decisions
   (e.g., "if confidence < 0.5, request human review").

5. **Extensibility**: The `metadata` dict allows agents to include custom information
   without changing the core schema (e.g., token counts, processing time, model used).

6. **State Updates**: The orchestrator uses AgentOutput to update DocumentState:
   - SystemArchitectAgent.output.content → DocumentState.hld_draft
   - ReviewerAgent.output.metadata['needs_revision'] → DocumentState.needs_revision
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List


class AgentOutput(BaseModel):
    """Standard output format for all agents.
    
    This is the return type for every agent's `perform_action()` method.
    It ensures all agents follow the same contract, making the system composable.
    
    Example usage:
        agent = SystemArchitectAgent(config, tools)
        output = agent.perform_action(state)
        # output.content contains the HLD
        # output.reasoning explains how it was generated
        # output.sources lists which RAG chunks were used
    """
    
    content: str = Field(
        ...,
        description="Generated content - the primary output of the agent",
        min_length=1
    )
    """The main output from the agent.
    
    For different agents:
    - SystemArchitectAgent: HLD markdown text
    - APIDataAgent: LLD markdown text
    - ReviewerAgent: JSON string of ReviewFeedback
    - WriterFormatterAgent: Complete formatted SDD
    """
    
    reasoning: Optional[str] = Field(
        None,
        description="Agent's reasoning process - how it arrived at this output"
    )
    """Explains the agent's thought process.
    
    This is especially important for:
    - Debugging: Why did the agent make this decision?
    - Transparency: Building trust in AI-generated content
    - Learning: Understanding agent behavior patterns
    
    Example: "Researched architectural patterns via RAG, found microservices
    pattern matches requirements, selected event-driven architecture based on
    scalability needs identified in brief."
    """
    
    sources: Optional[List[str]] = Field(
        None,
        description="Sources/context used - file paths, RAG chunk IDs, etc."
    )
    """Tracks provenance of the generated content.
    
    Enables:
    - Citations in final document
    - Traceability: "This design decision came from standard X"
    - Quality assurance: Verify sources are authoritative
    - Debugging: Check if wrong sources were used
    
    Example: ["data/standards/microservices-patterns.md", "data/standards/security-guidelines.md"]
    """
    
    confidence: Optional[float] = Field(
        None,
        description="Confidence score (0.0 to 1.0) in the quality/correctness of output",
        ge=0.0,
        le=1.0
    )
    """Agent's self-assessment of output quality.
    
    Uses:
    - Low confidence (< 0.5) → trigger human review
    - Medium confidence (0.5-0.7) → proceed with caution
    - High confidence (> 0.7) → proceed normally
    
    Different agents may calculate this differently:
    - SystemArchitectAgent: Based on how well RAG results match requirements
    - ReviewerAgent: Based on validation score
    - WriterFormatterAgent: Based on style guide compliance
    """
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional agent-specific metadata"
    )
    """Flexible storage for agent-specific information.
    
    Common metadata fields:
    - agent: Agent name/version
    - tokens_used: LLM token count
    - processing_time: Time taken
    - model: LLM model used
    - context_chunks_used: Number of RAG chunks retrieved
    - needs_revision: (ReviewerAgent) Whether revision is needed
    
    This allows agents to pass custom information without schema changes.
    """
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v: Optional[float]) -> Optional[float]:
        """Ensure confidence is in valid range."""
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v
    
    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        """Check if output has high confidence."""
        return self.confidence is not None and self.confidence >= threshold
    
    def is_low_confidence(self, threshold: float = 0.5) -> bool:
        """Check if output has low confidence."""
        return self.confidence is not None and self.confidence < threshold
    
    def has_sources(self) -> bool:
        """Check if sources are available."""
        return self.sources is not None and len(self.sources) > 0
    
    class Config:
        """Pydantic configuration."""
        # Allow extra fields for backward compatibility
        extra = "allow"
        # Enable JSON serialization
        json_encoders = {
            # Custom encoders if needed
        }

