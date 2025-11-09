"""LangGraph state definition."""

from agent_app.schemas.document_state import DocumentState
from typing import TypedDict, Annotated
import operator


class GraphState(TypedDict):
    """LangGraph state definition."""
    
    # Use DocumentState as the core state
    # LangGraph will serialize/deserialize this
    state: DocumentState
    
    # Additional graph metadata
    current_node: str
    iteration_count: int

