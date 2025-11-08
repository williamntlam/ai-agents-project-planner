"""Abstract base class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import Dict, Any
from agent_app.schemas.agent_output import AgentOutput
from agent_app.schemas.document_state import DocumentState


class BaseAgent(ABC):
    """Abstract base class for all specialized agents."""
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        """
        Initialize agent with configuration and tools.
        
        Args:
            config: Agent-specific configuration
            tools: Dictionary of available tools (RAG, MCP, etc.)
        """
        self.config = config
        self.tools = tools or {}
        self.name = self.__class__.__name__
    
    @abstractmethod
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Execute the agent's primary action.
        
        Args:
            state: Current document state
            
        Returns:
            AgentOutput with generated content and metadata
        """
        pass
    
    def get_required_tools(self) -> list:
        """
        Return list of required tool names.
        
        Returns:
            List of tool names this agent needs
        """
        return []
    
    def validate_state(self, state: DocumentState) -> bool:
        """
        Validate that state has required inputs for this agent.
        
        Args:
            state: Document state to validate
            
        Returns:
            True if state is valid for this agent
        """
        return True

