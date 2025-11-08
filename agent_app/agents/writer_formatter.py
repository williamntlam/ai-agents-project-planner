"""Writer Formatter Agent - Final document assembly and formatting."""

from typing import Dict, Any
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput


class WriterFormatterAgent(BaseAgent):
    """Agent responsible for final document formatting and assembly."""
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
        # TODO: Initialize RAG tool and LLM
        # self.rag_tool = tools.get('rag_tool')
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
        """
        # TODO: Implement full formatting logic
        # See IMPLEMENTATION_GUIDE.md Phase 6.4 for details
        
        return AgentOutput(
            content="# System Design Document\n\n(TODO: Implement document formatting)",
            reasoning="WriterFormatterAgent - Implementation in progress",
            metadata={"agent": self.name}
        )
    
    def get_required_tools(self) -> list:
        return ['rag_tool']

