"""System Architect Agent - High-Level Design generation."""

from typing import Dict, Any, List, Tuple
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput


class SystemArchitectAgent(BaseAgent):
    """Agent responsible for high-level system architecture design.
    
    This agent generates the High-Level Design (HLD) based on the project brief.
    It uses the ReAct (Reasoning + Acting) pattern to research architectural
    patterns via RAG and synthesize a comprehensive HLD.
    """
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
        # TODO: Initialize RAG tool and LLM
        # self.rag_tool = self._get_tool('rag_tool')
        # self.llm = self._initialize_llm()
    
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Generate high-level design based on project brief.
        
        Uses ReAct pattern:
        1. Thought: Analyze requirements
        2. Action: Query RAG for relevant patterns
        3. Observation: Review retrieved context
        4. Thought: Synthesize architecture
        5. Action: Generate HLD
        
        Args:
            state: Document state with project_brief
            
        Returns:
            AgentOutput with HLD content
        """
        # TODO: Implement full HLD generation logic
        # See IMPLEMENTATION_GUIDE.md Phase 6.1 for details
        
        # Use combined brief to include all context
        full_brief = state.get_combined_brief()
        
        return AgentOutput(
            content="# High-Level Design\n\n(TODO: Implement HLD generation)",
            reasoning="SystemArchitectAgent - Implementation in progress",
            metadata={"agent": self.name}
        )
    
    def get_required_tools(self) -> List[str]:
        """Return list of required tools."""
        return ['rag_tool']
    
    def validate_state(self, state: DocumentState) -> Tuple[bool, List[str]]:
        """
        Validate state for SystemArchitectAgent.
        
        Requires:
        - project_brief (always required)
        - revision_feedback (if revision_count > 0)
        """
        is_valid, errors = super().validate_state(state)
        
        # Additional validation: if revising, need feedback
        if state.revision_count > 0 and not state.review_feedback:
            errors.append("revision_feedback is required when revision_count > 0")
            is_valid = False
        
        return is_valid, errors

