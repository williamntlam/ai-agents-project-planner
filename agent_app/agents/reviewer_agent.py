"""Reviewer Agent - Quality assurance and validation."""

from typing import Dict, Any, List, Tuple
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput
from agent_app.schemas.review_feedback import ReviewFeedback


class ReviewerAgent(BaseAgent):
    """Agent responsible for quality assurance and validation.
    
    This agent reviews the generated HLD and LLD, validates against JSON Schema,
    and provides structured feedback. It sets the needs_revision flag which
    controls workflow routing.
    """
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
        # TODO: Load validation schema and rubric
        # self.schema = self._load_validation_schema()
        # self.rubric = config.get('rubric', {})
        # self.llm = self._initialize_llm()
    
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Review document and generate structured feedback.
        
        Steps:
        1. Validate against JSON Schema
        2. Review content quality using rubric
        3. Generate structured feedback
        4. Set needs_revision flag
        
        Args:
            state: Document state with hld_draft and lld_draft
            
        Returns:
            AgentOutput with ReviewFeedback JSON
        """
        # TODO: Implement full review logic
        # See IMPLEMENTATION_GUIDE.md Phase 6.3 for details
        
        review_feedback = ReviewFeedback(
            overall_score=0.5,
            passes_validation=False,
            issues=[],
            strengths=[],
            needs_revision=True
        )
        
        return AgentOutput(
            content=review_feedback.model_dump_json(),
            reasoning="ReviewerAgent - Implementation in progress",
            metadata={
                "needs_revision": review_feedback.needs_revision,
                "validation_passed": review_feedback.passes_validation
            }
        )
    
    def validate_state(self, state: DocumentState) -> Tuple[bool, List[str]]:
        """
        Validate state for ReviewerAgent.
        
        Requires:
        - project_brief (always required)
        - hld_draft (required)
        - lld_draft (required)
        """
        is_valid, errors = super().validate_state(state)
        
        # ReviewerAgent requires both drafts
        if not state.hld_draft or len(state.hld_draft.strip()) < 100:
            errors.append("hld_draft is required and must be at least 100 characters")
            is_valid = False
        
        if not state.lld_draft or len(state.lld_draft.strip()) < 100:
            errors.append("lld_draft is required and must be at least 100 characters")
            is_valid = False
        
        return is_valid, errors

