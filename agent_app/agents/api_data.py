"""API Data Agent - Low-Level Design generation."""

from typing import Dict, Any, List, Tuple
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput


class APIDataAgent(BaseAgent):
    """Agent responsible for low-level design: APIs, data models, schemas.
    
    This agent generates the Low-Level Design (LLD) based on the HLD from
    SystemArchitectAgent. It uses MCP tools to query schema standards and
    RAG to retrieve API design patterns.
    """
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
        # TODO: Initialize MCP tools, RAG tool, and LLM
        # self.mcp_tools = self._get_tool('mcp_tools')
        # self.rag_tool = self._get_tool('rag_tool')
        # self.llm = self._initialize_llm()
    
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Generate low-level design based on HLD.
        
        Uses:
        - MCP tools to query schema standards
        - RAG to retrieve API design patterns
        - LLM to generate detailed LLD
        
        Args:
            state: Document state with hld_draft
            
        Returns:
            AgentOutput with LLD content
        """
        # TODO: Implement full LLD generation logic
        # See IMPLEMENTATION_GUIDE.md Phase 6.2 for details
        
        return AgentOutput(
            content="# Low-Level Design\n\n(TODO: Implement LLD generation)",
            reasoning="APIDataAgent - Implementation in progress",
            metadata={"agent": self.name}
        )
    
    def get_required_tools(self) -> List[str]:
        """Return list of required tools."""
        return ['mcp_tools', 'rag_tool']
    
    def validate_state(self, state: DocumentState) -> Tuple[bool, List[str]]:
        """
        Validate state for APIDataAgent.
        
        Requires:
        - project_brief (always required)
        - hld_draft (required - depends on SystemArchitectAgent output)
        """
        is_valid, errors = super().validate_state(state)
        
        # APIDataAgent requires hld_draft
        if not state.hld_draft or len(state.hld_draft.strip()) < 100:
            errors.append("hld_draft is required and must be at least 100 characters")
            is_valid = False
        
        return is_valid, errors

