"""Documentation Agent - Code and API documentation generation."""

from typing import Dict, Any, List, Tuple
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput


class DocumentationAgent(BaseAgent):
    """Agent responsible for generating code and API documentation.
    
    This agent creates comprehensive documentation for the system design,
    including API documentation, code examples, integration guides, and
    developer documentation. It ensures all code and APIs are well-documented.
    """
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
        # TODO: Initialize RAG tool for documentation standards
        # self.rag_tool = self._get_tool('rag_tool')
        # self.llm = self._initialize_llm()
    
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Generate code and API documentation.
        
        Creates:
        - API endpoint documentation (OpenAPI/Swagger specs)
        - Code examples and snippets
        - Integration guides
        - Developer setup instructions
        - Error handling documentation
        - Data model documentation
        
        Args:
            state: Document state with hld_draft and lld_draft
            
        Returns:
            AgentOutput with documentation content
        """
        # TODO: Implement full documentation generation logic
        # See IMPLEMENTATION_GUIDE.md for details
        
        return AgentOutput(
            content="# Documentation\n\n(TODO: Implement documentation generation)",
            reasoning="DocumentationAgent - Implementation in progress",
            metadata={"agent": self.name}
        )
    
    def get_required_tools(self) -> List[str]:
        """Return list of required tools."""
        return ['rag_tool']
    
    def validate_state(self, state: DocumentState) -> Tuple[bool, List[str]]:
        """
        Validate state for DocumentationAgent.
        
        Requires:
        - project_brief (always required)
        - hld_draft (required)
        - lld_draft (required - needs API details for documentation)
        """
        is_valid, errors = super().validate_state(state)
        
        # DocumentationAgent requires both drafts for complete documentation
        if not state.hld_draft or len(state.hld_draft.strip()) < 100:
            errors.append("hld_draft is required and must be at least 100 characters")
            is_valid = False
        
        if not state.lld_draft or len(state.lld_draft.strip()) < 100:
            errors.append("lld_draft is required and must be at least 100 characters")
            is_valid = False
        
        return is_valid, errors

