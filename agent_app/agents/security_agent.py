"""Security Agent - Security analysis and recommendations."""

from typing import Dict, Any, List, Tuple
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput


class SecurityAgent(BaseAgent):
    """Agent responsible for security analysis and recommendations.
    
    This agent analyzes the system design for security vulnerabilities,
    compliance requirements, and best practices. It reviews authentication,
    authorization, data protection, and security patterns.
    """
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
        # TODO: Initialize RAG tool for security standards
        # self.rag_tool = self._get_tool('rag_tool')
        # self.llm = self._initialize_llm()
    
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Analyze security aspects of the system design.
        
        Reviews:
        - Authentication and authorization mechanisms
        - Data encryption and protection
        - API security (rate limiting, input validation)
        - Compliance requirements (GDPR, SOC2, etc.)
        - Security patterns and best practices
        - Threat modeling considerations
        
        Args:
            state: Document state with hld_draft and/or lld_draft
            
        Returns:
            AgentOutput with security analysis and recommendations
        """
        # TODO: Implement full security analysis logic
        # See IMPLEMENTATION_GUIDE.md for details
        
        # Use combined brief to understand security requirements
        full_brief = state.get_combined_brief()
        
        return AgentOutput(
            content="# Security Analysis\n\n(TODO: Implement security analysis)",
            reasoning="SecurityAgent - Implementation in progress",
            metadata={"agent": self.name}
        )
    
    def get_required_tools(self) -> List[str]:
        """Return list of required tools."""
        return ['rag_tool']
    
    def validate_state(self, state: DocumentState) -> Tuple[bool, List[str]]:
        """
        Validate state for SecurityAgent.
        
        Requires:
        - project_brief (always required)
        - hld_draft (preferred) or lld_draft (minimum)
        """
        is_valid, errors = super().validate_state(state)
        
        # SecurityAgent needs at least HLD or LLD to analyze
        if not state.hld_draft and not state.lld_draft:
            errors.append("Either hld_draft or lld_draft is required for security analysis")
            is_valid = False
        
        return is_valid, errors

