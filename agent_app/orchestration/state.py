"""LangGraph state definition."""

from typing import TypedDict
from agent_app.schemas.document_state import DocumentState


class GraphState(TypedDict):
    """LangGraph state definition."""
    
    # Use DocumentState as the core state
    # LangGraph will serialize/deserialize this
    state: DocumentState
    
    # Additional graph metadata
    current_node: str
    iteration_count: int

