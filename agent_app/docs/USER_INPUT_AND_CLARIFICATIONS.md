# Handling User Input and Clarifications

## Overview

The system supports multiple ways for users to provide additional information and clarifications:

1. **Initial Enhanced Input** - Provide detailed information upfront
2. **Agent-Driven Clarifications** - Agents request missing information
3. **Iterative Refinement** - Add information during workflow execution
4. **Revision with Context** - Provide additional context during revisions

## 1. Initial Enhanced Input

### CLI Usage

```bash
# Basic brief
python -m agent_app.main \
  --brief "Build an e-commerce microservice"

# With additional context
python -m agent_app.main \
  --brief "Build an e-commerce microservice" \
  --additional-context "Must handle 10k requests/second, use PostgreSQL, deploy on AWS"

# With structured requirements (JSON file)
python -m agent_app.main \
  --brief "Build an e-commerce microservice" \
  --requirements-file requirements.json
```

### Programmatic Usage

```python
from agent_app.schemas.document_state import DocumentState

# Create state with additional context
state = DocumentState(
    project_brief="Build an e-commerce microservice",
    additional_context="""
    Additional Requirements:
    - Must handle 10,000 requests per second
    - Use PostgreSQL for data persistence
    - Deploy on AWS infrastructure
    - Support OAuth2 authentication
    - Must comply with GDPR regulations
    """,
    requirements={
        "functional_requirements": [
            "User authentication",
            "Order processing",
            "Payment integration",
            "Inventory management"
        ],
        "non_functional_requirements": {
            "performance": "10k requests/second",
            "scalability": "Horizontal scaling required",
            "availability": "99.9% uptime"
        },
        "constraints": [
            "PostgreSQL database",
            "AWS infrastructure only",
            "Python backend"
        ],
        "assumptions": [
            "Users have existing accounts",
            "Payment gateway already integrated"
        ]
    }
)
```

## 2. Agent-Driven Clarifications

Agents can request clarifications when information is missing or ambiguous.

### How It Works

1. **Agent detects missing information** during execution
2. **Agent creates clarification request** and adds to state
3. **Workflow pauses** at clarification checkpoint
4. **User provides answer**
5. **Workflow resumes** with additional context

### Example: SystemArchitectAgent Requesting Clarification

```python
# In SystemArchitectAgent.perform_action()
def perform_action(self, state: DocumentState) -> AgentOutput:
    # Analyze brief for missing information
    missing_info = self._detect_missing_info(state)
    
    if missing_info:
        # Request clarification
        state.clarification_requests.append({
            "question": "What is the expected traffic volume?",
            "agent": self.name,
            "stage": "draft_hld",
            "priority": "high",
            "context": "Need this to determine scaling strategy"
        })
        
        # Return output indicating clarification needed
        return AgentOutput(
            content="",  # No content yet
            reasoning="Waiting for clarification on traffic volume",
            metadata={
                "needs_clarification": True,
                "clarification_question": "What is the expected traffic volume?"
            }
        )
    
    # Continue with normal generation...
```

### Handling Clarification Responses

```python
# User provides answer
def provide_clarification(
    state: DocumentState,
    question: str,
    answer: str
) -> DocumentState:
    """Add user clarification to state."""
    state.add_clarification(
        question=question,
        answer=answer,
        agent="user"  # or specific agent name
    )
    
    # Remove from pending requests
    state.clarification_requests = [
        req for req in state.clarification_requests
        if req["question"] != question
    ]
    
    return state

# Usage
state = provide_clarification(
    state,
    question="What is the expected traffic volume?",
    answer="10,000 requests per second peak load"
)
```

## 3. Using Combined Brief

Agents should use `get_combined_brief()` to access all context:

```python
# In agent implementation
def perform_action(self, state: DocumentState) -> AgentOutput:
    # Get combined brief with all context
    full_brief = state.get_combined_brief()
    
    # This includes:
    # - Original project_brief
    # - Additional context
    # - All clarifications (Q&A pairs)
    
    # Use in prompt
    prompt = f"""
    Generate HLD for:
    {full_brief}
    """
```

## 4. Workflow Integration

### Enhanced CLI with Interactive Mode

```python
# main.py enhancement
@click.command()
@click.option('--brief', required=True)
@click.option('--additional-context', help='Additional context')
@click.option('--interactive', is_flag=True, help='Interactive clarification mode')
def main(brief: str, additional_context: str, interactive: bool):
    state = DocumentState(
        project_brief=brief,
        additional_context=additional_context
    )
    
    # Run workflow
    workflow = create_workflow_graph(agents, config)
    
    # Check for clarifications
    while state.has_pending_clarifications():
        for request in state.clarification_requests:
            if interactive:
                # Prompt user
                answer = click.prompt(
                    f"\n{request['question']}",
                    type=str
                )
                state = provide_clarification(
                    state,
                    request['question'],
                    answer
                )
            else:
                # Non-interactive: log and exit
                click.echo(f"Clarification needed: {request['question']}")
                return
    
    # Continue workflow...
```

### LangGraph Checkpoint for Clarifications

```python
# In orchestration/graph.py
def check_clarifications(graph_state: GraphState) -> GraphState:
    """Checkpoint for handling clarifications."""
    state = graph_state['state']
    
    if state.has_pending_clarifications():
        # Pause workflow - wait for user input
        # In production, this would use LangGraph's interrupt mechanism
        return graph_state
    
    return graph_state

# Add to workflow
workflow.add_node("check_clarifications", check_clarifications)
workflow.add_edge("draft_hld", "check_clarifications")
```

## 5. Revision with Additional Context

Users can provide additional context during revisions:

```python
# During revision cycle
def revise_with_context(
    state: DocumentState,
    additional_context: str
) -> DocumentState:
    """Add context during revision."""
    if state.additional_context:
        state.additional_context += f"\n\nRevision Context:\n{additional_context}"
    else:
        state.additional_context = f"Revision Context:\n{additional_context}"
    
    return state

# Usage
state = revise_with_context(
    state,
    "Please ensure the design includes Redis caching layer for session management"
)
```

## 6. Structured Input File Format

For complex requirements, use a structured JSON/YAML file:

```json
// requirements.json
{
  "project_brief": "Build an e-commerce microservice",
  "additional_context": "Must handle high traffic",
  "functional_requirements": [
    "User authentication",
    "Order processing",
    "Payment integration"
  ],
  "non_functional_requirements": {
    "performance": "10k requests/second",
    "scalability": "Horizontal scaling",
    "availability": "99.9% uptime",
    "security": "GDPR compliant"
  },
  "constraints": [
    "PostgreSQL database",
    "AWS infrastructure",
    "Python backend"
  ],
  "assumptions": [
    "Users have existing accounts",
    "Payment gateway integrated"
  ],
  "clarifications": [
    {
      "question": "What authentication method?",
      "answer": "OAuth2 with JWT"
    }
  ]
}
```

```python
# Load from file
import json

def load_requirements(file_path: str) -> DocumentState:
    with open(file_path) as f:
        data = json.load(f)
    
    return DocumentState(
        project_brief=data["project_brief"],
        additional_context=data.get("additional_context"),
        requirements={
            "functional": data.get("functional_requirements", []),
            "non_functional": data.get("non_functional_requirements", {}),
            "constraints": data.get("constraints", []),
            "assumptions": data.get("assumptions", [])
        },
        user_clarifications=data.get("clarifications", [])
    )
```

## 7. Best Practices

### For Users

1. **Be specific upfront** - Provide detailed brief initially
2. **Use structured format** - Use JSON/YAML for complex requirements
3. **Respond to clarifications** - Answer agent questions promptly
4. **Add context during revisions** - Provide additional info during revision cycles

### For Agents

1. **Detect missing info early** - Check for required information at start
2. **Ask specific questions** - Request clarifications with context
3. **Use combined brief** - Always use `get_combined_brief()` for full context
4. **Prioritize clarifications** - Mark high-priority questions

### For Workflow

1. **Check clarifications early** - Validate input before starting
2. **Pause at checkpoints** - Use LangGraph interrupts for clarifications
3. **Resume with context** - Continue workflow after clarifications provided
4. **Track all input** - Store all user input in state for traceability

## 8. Example: Complete Flow

```python
# 1. Initial state with basic brief
state = DocumentState(
    project_brief="Build an e-commerce microservice"
)

# 2. Agent requests clarification
state.clarification_requests.append({
    "question": "What is the expected traffic volume?",
    "agent": "SystemArchitectAgent",
    "priority": "high"
})

# 3. User provides answer
state.add_clarification(
    question="What is the expected traffic volume?",
    answer="10,000 requests per second",
    agent="user"
)

# 4. Agent uses combined brief
full_context = state.get_combined_brief()
# Includes: brief + clarifications

# 5. During revision, add more context
state.additional_context = "Please add Redis caching layer"

# 6. Final combined brief includes everything
final_context = state.get_combined_brief()
# Includes: brief + additional_context + all clarifications
```

## Summary

The system supports flexible input through:
- ✅ **Additional context** field for extra information
- ✅ **Clarification requests** from agents
- ✅ **User clarifications** Q&A pairs
- ✅ **Structured requirements** for complex inputs
- ✅ **Combined brief** method to access all context
- ✅ **Revision context** for iterative refinement

This allows users to provide information incrementally while agents can request what they need.

