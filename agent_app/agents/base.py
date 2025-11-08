"""Abstract base class for all specialized agents.

WHY THIS CLASS EXISTS:
=====================
The BaseAgent implements the Strategy Pattern at the agent level, providing:

1. **Uniform Interface**: All agents (SystemArchitect, APIData, Reviewer, WriterFormatter)
   implement the same `perform_action(state) -> AgentOutput` method, allowing the
   orchestrator to handle them polymorphically.

2. **Contract Enforcement**: The abstract method ensures all agents must implement
   their core functionality, preventing incomplete implementations.

3. **Common Functionality**: Shared logic (validation, tool checking, logging) is
   centralized here, reducing code duplication.

4. **Extensibility**: New agent types can be added by simply extending BaseAgent
   and implementing `perform_action()`.

5. **Testability**: The uniform interface makes it easy to mock agents for testing.

DESIGN PATTERN: Strategy Pattern
- Context: LangGraph Orchestrator
- Strategy: Each specialized agent (SystemArchitectAgent, APIDataAgent, etc.)
- Common Interface: BaseAgent.perform_action()
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from agent_app.schemas.agent_output import AgentOutput
from agent_app.schemas.document_state import DocumentState
from agent_app.utils.logging import setup_logging


class BaseAgent(ABC):
    """Abstract base class for all specialized agents.
    
    This class defines the contract that all agents must follow. It implements
    the Strategy Pattern, allowing different agent implementations to be used
    interchangeably by the orchestrator.
    
    Example usage:
        class MyAgent(BaseAgent):
            def perform_action(self, state: DocumentState) -> AgentOutput:
                # Implement agent logic
                return AgentOutput(content="...", ...)
        
        agent = MyAgent(config, tools)
        output = agent.perform_action(state)
    """
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        """
        Initialize agent with configuration and tools.
        
        Args:
            config: Agent-specific configuration (model, temperature, etc.)
            tools: Dictionary of available tools (RAG, MCP, etc.)
            
        Raises:
            ValueError: If required tools are missing
        """
        self.config = config or {}
        self.tools = tools or {}
        self.name = self.__class__.__name__
        self.logger = setup_logging()
        
        # Validate required tools are available
        self._validate_tools()
    
    @abstractmethod
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Execute the agent's primary action.
        
        This is the core method that each agent must implement. It defines
        what the agent does when invoked by the orchestrator.
        
        Args:
            state: Current document state (read from and write to)
            
        Returns:
            AgentOutput with generated content and metadata
            
        Raises:
            ValueError: If state validation fails
            RuntimeError: If agent execution fails
        """
        pass
    
    def get_required_tools(self) -> List[str]:
        """
        Return list of required tool names.
        
        Subclasses should override this to declare which tools they need.
        The orchestrator can use this to validate tool availability before
        agent execution.
        
        Returns:
            List of tool names this agent needs (e.g., ['rag_tool', 'mcp_tools'])
        """
        return []
    
    def validate_state(self, state: DocumentState) -> Tuple[bool, List[str]]:
        """
        Validate that state has required inputs for this agent.
        
        Subclasses should override this to check for agent-specific requirements.
        For example, APIDataAgent might require hld_draft to be present.
        
        Args:
            state: Document state to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
            - is_valid: True if state is valid for this agent
            - list_of_errors: List of error messages if validation fails
        """
        errors = []
        
        # Base validation: project_brief is always required
        if not state.project_brief or len(state.project_brief.strip()) < 10:
            errors.append("project_brief is required and must be at least 10 characters")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _validate_tools(self) -> None:
        """
        Validate that all required tools are available.
        
        Raises:
            ValueError: If a required tool is missing
        """
        required_tools = self.get_required_tools()
        missing_tools = [
            tool for tool in required_tools
            if tool not in self.tools or self.tools[tool] is None
        ]
        
        if missing_tools:
            raise ValueError(
                f"{self.name} requires the following tools that are not available: "
                f"{', '.join(missing_tools)}. Available tools: {list(self.tools.keys())}"
            )
    
    def _get_tool(self, tool_name: str) -> Any:
        """
        Get a tool by name with error handling.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            The tool object
            
        Raises:
            ValueError: If tool is not available
        """
        if tool_name not in self.tools:
            raise ValueError(
                f"{self.name} requires '{tool_name}' tool, but it's not available. "
                f"Available tools: {list(self.tools.keys())}"
            )
        
        tool = self.tools[tool_name]
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' is None")
        
        return tool
    
    def _validate_and_execute(self, state: DocumentState) -> AgentOutput:
        """
        Validate state and execute agent action.
        
        This is a convenience method that combines validation and execution.
        The orchestrator can use this instead of calling validate_state() and
        perform_action() separately.
        
        Args:
            state: Document state to process
            
        Returns:
            AgentOutput with results
            
        Raises:
            ValueError: If state validation fails
        """
        # Validate state
        is_valid, errors = self.validate_state(state)
        if not is_valid:
            error_msg = f"{self.name} state validation failed: {', '.join(errors)}"
            self.logger.error(error_msg, agent=self.name, errors=errors)
            raise ValueError(error_msg)
        
        # Log execution start
        self.logger.info(
            f"{self.name} starting execution",
            agent=self.name,
            revision_count=state.revision_count
        )
        
        try:
            # Execute agent action
            output = self.perform_action(state)
            
            # Log execution completion
            self.logger.info(
                f"{self.name} completed execution",
                agent=self.name,
                content_length=len(output.content),
                confidence=output.confidence,
                has_sources=output.has_sources()
            )
            
            return output
            
        except Exception as e:
            self.logger.error(
                f"{self.name} execution failed",
                agent=self.name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    def _check_clarification_needed(self, state: DocumentState) -> Optional[Dict[str, Any]]:
        """
        Check if agent needs clarification from user.
        
        Agents can override this to detect missing information and request
        clarifications before proceeding.
        
        Args:
            state: Current document state
            
        Returns:
            Clarification request dict if needed, None otherwise
            
        Format:
            {
                "question": "What is the expected traffic volume?",
                "priority": "high",
                "context": "Need this to determine scaling strategy"
            }
        """
        return None
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with default fallback.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
    
    def __repr__(self) -> str:
        """String representation of agent."""
        return f"{self.name}(config_keys={list(self.config.keys())}, tools={self.get_required_tools()})"

