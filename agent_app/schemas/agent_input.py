"""Standard input format for agents.

WHY THIS SCHEMA EXISTS:
=======================
While agents currently receive `DocumentState` directly, having an `AgentInput` schema provides:

1. **Explicit Dependencies**: Makes it clear what each agent needs from the state,
   rather than having agents dig through the entire DocumentState object.

2. **Input Validation**: Validates that required inputs are present before agent execution,
   providing better error messages than generic state validation.

3. **Input Transformation**: Allows agents to define how to extract/transform data from
   DocumentState into their specific input format (e.g., combining hld_draft + lld_draft).

4. **Type Safety**: Provides type hints and validation for agent-specific inputs,
   catching errors at the input stage rather than during execution.

5. **Documentation**: Serves as documentation for what each agent expects, making
   the system more maintainable and easier to understand.

6. **Future Extensibility**: Enables features like:
   - Input caching
   - Input versioning
   - Input transformation pipelines
   - Agent-specific input formats

RELATIONSHIP TO DOCUMENTSTATE:
==============================
- `DocumentState` is the shared workflow state (the "database")
- `AgentInput` is a view/transformation of relevant parts of `DocumentState` for a specific agent
- Agents can extract `AgentInput` from `DocumentState` using `from_state()` method
- This maintains the single source of truth (DocumentState) while providing agent-specific interfaces
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Tuple
from agent_app.schemas.document_state import DocumentState


class AgentInput(BaseModel):
    """Base input schema for agents.
    
    This is the base class that all agent-specific inputs should inherit from.
    Each agent can define its own input schema by extending this class.
    
    Example:
        class SystemArchitectInput(AgentInput):
            project_brief: str  # Required
            revision_count: int = 0  # Optional, for revision context
        
        class APIDataInput(AgentInput):
            project_brief: str  # Required
            hld_draft: str  # Required - depends on SystemArchitectAgent output
    """
    
    # Common fields that all agents might need
    project_brief: str = Field(
        ...,
        description="Original project brief/requirements",
        min_length=10
    )
    """The project brief - available to all agents."""
    
    revision_count: int = Field(
        0,
        description="Number of revision cycles completed",
        ge=0
    )
    """Revision context - agents can use this to adjust their approach."""
    
    revision_feedback: Optional[Dict[str, Any]] = Field(
        None,
        description="Previous review feedback (if in revision loop)"
    )
    """Previous review feedback - helps agents understand what needs fixing."""
    
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context/metadata"
    )
    """Flexible context storage for agent-specific needs."""
    
    @classmethod
    def from_state(cls, state: DocumentState, **kwargs) -> "AgentInput":
        """
        Create AgentInput from DocumentState.
        
        This is the primary way to construct agent inputs.
        Subclasses should override this to extract their specific requirements.
        
        Args:
            state: DocumentState to extract from
            **kwargs: Additional parameters
            
        Returns:
            AgentInput instance
        """
        return cls(
            project_brief=state.project_brief,
            revision_count=state.revision_count,
            revision_feedback=state.review_feedback,
            context={
                "document_status": state.document_status.value,
                "max_revisions": state.max_revisions,
                **kwargs
            }
        )
    
    def validate_for_agent(self, agent_name: str) -> Tuple[bool, List[str]]:
        """
        Validate that input has all required fields for a specific agent.
        
        Args:
            agent_name: Name of the agent to validate for
            
        Returns:
            (is_valid, list_of_missing_fields)
        """
        errors = []
        
        # Base validation - project_brief is always required
        if not self.project_brief or len(self.project_brief) < 10:
            errors.append("project_brief is required and must be at least 10 characters")
        
        # Agent-specific validation can be added in subclasses
        return len(errors) == 0, errors
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"  # Allow agent-specific fields
        json_encoders = {}


# Agent-specific input schemas

class SystemArchitectInput(AgentInput):
    """Input schema for SystemArchitectAgent.
    
    This agent only needs the project brief to generate HLD.
    During revisions, it can use revision_feedback to understand what to fix.
    """
    
    # No additional required fields - project_brief is sufficient
    # Optional: can include previous hld_draft if revising
    previous_hld_draft: Optional[str] = Field(
        None,
        description="Previous HLD draft (if in revision loop)"
    )
    
    @classmethod
    def from_state(cls, state: DocumentState, **kwargs) -> "SystemArchitectInput":
        """Extract SystemArchitectAgent input from state."""
        return cls(
            project_brief=state.project_brief,
            revision_count=state.revision_count,
            revision_feedback=state.review_feedback,
            previous_hld_draft=state.hld_draft,  # Include previous draft for revision context
            context={
                "document_status": state.document_status.value,
                "max_revisions": state.max_revisions,
                **kwargs
            }
        )
    
    def validate_for_agent(self, agent_name: str = "SystemArchitectAgent") -> Tuple[bool, List[str]]:
        """Validate input for SystemArchitectAgent."""
        is_valid, errors = super().validate_for_agent(agent_name)
        
        # SystemArchitectAgent specific validation
        if self.revision_count > 0 and not self.revision_feedback:
            errors.append("revision_feedback is required when revision_count > 0")
        
        return len(errors) == 0, errors


class APIDataInput(AgentInput):
    """Input schema for APIDataAgent.
    
    This agent needs:
    - project_brief: Original requirements
    - hld_draft: High-level design to base LLD on (REQUIRED)
    """
    
    hld_draft: str = Field(
        ...,
        description="High-Level Design draft (required for LLD generation)",
        min_length=100
    )
    """The HLD draft that this agent will use to generate detailed LLD."""
    
    @classmethod
    def from_state(cls, state: DocumentState, **kwargs) -> "APIDataInput":
        """Extract APIDataAgent input from state."""
        if not state.hld_draft:
            raise ValueError("hld_draft is required for APIDataAgent but is None in state")
        
        return cls(
            project_brief=state.project_brief,
            hld_draft=state.hld_draft,
            revision_count=state.revision_count,
            revision_feedback=state.review_feedback,
            context={
                "document_status": state.document_status.value,
                "max_revisions": state.max_revisions,
                **kwargs
            }
        )
    
    def validate_for_agent(self, agent_name: str = "APIDataAgent") -> Tuple[bool, List[str]]:
        """Validate input for APIDataAgent."""
        is_valid, errors = super().validate_for_agent(agent_name)
        
        # APIDataAgent requires hld_draft
        if not self.hld_draft or len(self.hld_draft) < 100:
            errors.append("hld_draft is required and must be at least 100 characters")
        
        return len(errors) == 0, errors


class ReviewerInput(AgentInput):
    """Input schema for ReviewerAgent.
    
    This agent needs:
    - project_brief: Original requirements (for context)
    - hld_draft: High-level design to review (REQUIRED)
    - lld_draft: Low-level design to review (REQUIRED)
    """
    
    hld_draft: str = Field(
        ...,
        description="High-Level Design draft to review",
        min_length=100
    )
    
    lld_draft: str = Field(
        ...,
        description="Low-Level Design draft to review",
        min_length=100
    )
    
    @classmethod
    def from_state(cls, state: DocumentState, **kwargs) -> "ReviewerInput":
        """Extract ReviewerAgent input from state."""
        if not state.hld_draft:
            raise ValueError("hld_draft is required for ReviewerAgent but is None in state")
        if not state.lld_draft:
            raise ValueError("lld_draft is required for ReviewerAgent but is None in state")
        
        return cls(
            project_brief=state.project_brief,
            hld_draft=state.hld_draft,
            lld_draft=state.lld_draft,
            revision_count=state.revision_count,
            revision_feedback=state.review_feedback,
            context={
                "document_status": state.document_status.value,
                "max_revisions": state.max_revisions,
                **kwargs
            }
        )
    
    def validate_for_agent(self, agent_name: str = "ReviewerAgent") -> Tuple[bool, List[str]]:
        """Validate input for ReviewerAgent."""
        is_valid, errors = super().validate_for_agent(agent_name)
        
        # ReviewerAgent requires both drafts
        if not self.hld_draft or len(self.hld_draft) < 100:
            errors.append("hld_draft is required and must be at least 100 characters")
        if not self.lld_draft or len(self.lld_draft) < 100:
            errors.append("lld_draft is required and must be at least 100 characters")
        
        return len(errors) == 0, errors


class WriterFormatterInput(AgentInput):
    """Input schema for WriterFormatterAgent.
    
    This agent needs:
    - project_brief: Original requirements (for context)
    - hld_draft: High-level design to format (REQUIRED)
    - lld_draft: Low-level design to format (REQUIRED)
    - review_feedback: Review feedback (optional, for context)
    """
    
    hld_draft: str = Field(
        ...,
        description="High-Level Design draft to format",
        min_length=100
    )
    
    lld_draft: str = Field(
        ...,
        description="Low-Level Design draft to format",
        min_length=100
    )
    
    @classmethod
    def from_state(cls, state: DocumentState, **kwargs) -> "WriterFormatterInput":
        """Extract WriterFormatterAgent input from state."""
        if not state.hld_draft:
            raise ValueError("hld_draft is required for WriterFormatterAgent but is None in state")
        if not state.lld_draft:
            raise ValueError("lld_draft is required for WriterFormatterAgent but is None in state")
        
        return cls(
            project_brief=state.project_brief,
            hld_draft=state.hld_draft,
            lld_draft=state.lld_draft,
            revision_count=state.revision_count,
            revision_feedback=state.review_feedback,
            context={
                "document_status": state.document_status.value,
                "max_revisions": state.max_revisions,
                **kwargs
            }
        )
    
    def validate_for_agent(self, agent_name: str = "WriterFormatterAgent") -> Tuple[bool, List[str]]:
        """Validate input for WriterFormatterAgent."""
        is_valid, errors = super().validate_for_agent(agent_name)
        
        # WriterFormatterAgent requires both drafts
        if not self.hld_draft or len(self.hld_draft) < 100:
            errors.append("hld_draft is required and must be at least 100 characters")
        if not self.lld_draft or len(self.lld_draft) < 100:
            errors.append("lld_draft is required and must be at least 100 characters")
        
        return len(errors) == 0, errors

