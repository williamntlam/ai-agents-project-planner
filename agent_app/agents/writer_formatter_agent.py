"""Writer Formatter Agent - Final document assembly and formatting."""

from typing import Dict, Any, List, Tuple
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput


class WriterFormatterAgent(BaseAgent):
    """Agent responsible for final document formatting and assembly.
    
    This agent combines the HLD and LLD into a final formatted SDD document.
    It retrieves the document style guide via RAG and ensures the output
    adheres to formatting standards.
    """
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
        # TODO: Initialize RAG tool and LLM
        # self.rag_tool = self._get_tool('rag_tool')
        # self.llm = self._initialize_llm()
    
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Assemble and format final SDD document.
        
        Steps:
        1. Retrieve document style guide via RAG
        2. Combine HLD and LLD
        3. Add YAML frontmatter
        4. Format markdown
        5. Generate Mermaid diagrams
        6. Apply style guide
        
        Args:
            state: Document state with hld_draft and lld_draft
            
        Returns:
            AgentOutput with final formatted SDD
        """
        # TODO: Implement full formatting logic
        # See IMPLEMENTATION_GUIDE.md Phase 6.4 for details
        
        return AgentOutput(
            content="# System Design Document\n\n(TODO: Implement document formatting)",
            reasoning="WriterFormatterAgent - Implementation in progress",
            metadata={"agent": self.name}
        )
    
    def get_required_tools(self) -> List[str]:
        """Return list of required tools."""
        return ['rag_tool']
    
    def validate_state(self, state: DocumentState) -> Tuple[bool, List[str]]:
        """
        Validate state for WriterFormatterAgent.
        
        Requires:
        - project_brief (always required)
        - hld_draft (required)
        - lld_draft (required)
        """
        is_valid, errors = super().validate_state(state)
        
        # WriterFormatterAgent requires both drafts
        if not state.hld_draft or len(state.hld_draft.strip()) < 100:
            errors.append("hld_draft is required and must be at least 100 characters")
            is_valid = False
        
        if not state.lld_draft or len(state.lld_draft.strip()) < 100:
            errors.append("lld_draft is required and must be at least 100 characters")
            is_valid = False
        
        return is_valid, errors

