"""LangGraph workflow definition."""

from typing import Dict
import json
from langgraph.graph import StateGraph, END
from agent_app.orchestration.graph_state import GraphState
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentStatus


def _run_agent(agent: BaseAgent, graph_state: GraphState) -> GraphState:
    """
    Helper to run agent and update state.
    
    This function:
    1. Extracts DocumentState from GraphState
    2. Runs the agent's perform_action method
    3. Updates DocumentState based on agent output and type
    4. Updates GraphState metadata (current_node, iteration_count)
    5. Returns updated GraphState
    """
    document_state = graph_state['state']
    output = agent.perform_action(document_state)
    
    # Update state based on agent type
    agent_name = agent.__class__.__name__
    
    if agent_name == "SystemArchitectAgent":
        # Update HLD draft
        document_state.hld_draft = output.content
        # Store sources if available
        if output.sources:
            document_state.retrieved_context = output.sources
        
    elif agent_name == "APIDataAgent":
        # Update LLD draft
        document_state.lld_draft = output.content
        # Store sources if available
        if output.sources:
            document_state.retrieved_context = output.sources
        
    elif agent_name == "ReviewerAgent":
        # Parse review feedback JSON
        try:
            review_data = json.loads(output.content)
            document_state.review_feedback = review_data
            # Update needs_revision flag from metadata or review feedback
            needs_revision = output.metadata.get('needs_revision', False)
            if 'needs_revision' in review_data:
                needs_revision = review_data['needs_revision']
            document_state.needs_revision = needs_revision
            
            # Increment revision count if revision is needed
            if needs_revision:
                document_state.revision_count += 1
        except json.JSONDecodeError:
            # Fallback: try to extract from metadata
            document_state.needs_revision = output.metadata.get('needs_revision', False)
            if document_state.needs_revision:
                document_state.revision_count += 1
        
    elif agent_name == "WriterFormatterAgent":
        # Update final document
        document_state.final_document = output.content
        document_state.document_status = DocumentStatus.REVIEW
    
    # Update graph metadata
    graph_state['current_node'] = agent_name
    graph_state['iteration_count'] = graph_state.get('iteration_count', 0) + 1
    
    # Update state in graph_state
    graph_state['state'] = document_state
    
    return graph_state


def create_workflow_graph(agents: Dict[str, BaseAgent], config: Dict) -> StateGraph:
    """
    Create the LangGraph workflow.
    
    Workflow:
    1. draft_hld (SystemArchitectAgent)
    2. draft_lld (APIDataAgent)
    3. review_doc (ReviewerAgent)
    4. should_revise? (conditional edge)
       - Yes → draft_hld (loop back)
       - No → format_doc (WriterFormatterAgent)
    5. human_review (HITL checkpoint)
    6. END
    
    Args:
        agents: Dictionary of agent instances keyed by name
        config: Configuration dictionary
    
    Returns:
        Compiled LangGraph workflow
    """
    from agent_app.orchestration.graph_edges import should_revise, check_hitl
    
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("draft_hld", lambda state: _run_agent(agents['system_architect'], state))
    workflow.add_node("draft_lld", lambda state: _run_agent(agents['api_data'], state))
    workflow.add_node("review_doc", lambda state: _run_agent(agents['reviewer'], state))
    workflow.add_node("format_doc", lambda state: _run_agent(agents['writer_formatter'], state))
    
    # Add edges
    workflow.set_entry_point("draft_hld")
    workflow.add_edge("draft_hld", "draft_lld")
    workflow.add_edge("draft_lld", "review_doc")
    
    # Conditional edge: should we revise?
    workflow.add_conditional_edges(
        "review_doc",
        should_revise,  # Decision function
        {
            "revise": "draft_hld",  # Loop back
            "continue": "format_doc"  # Proceed
        }
    )
    
    # Human-in-the-Loop checkpoint
    workflow.add_node("human_review", check_hitl)
    workflow.add_edge("format_doc", "human_review")
    workflow.add_conditional_edges(
        "human_review",
        lambda state: "approved" if state.get('state', {}).get('approved', False) else "revise",
        {
            "approved": END,
            "revise": "draft_hld"
        }
    )
    
    return workflow.compile()

