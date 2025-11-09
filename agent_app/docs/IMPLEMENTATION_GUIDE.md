# Agent Application Implementation Guide

## Overview
This guide outlines the step-by-step implementation order for the Agent Application (`agent_app`). This module houses the logic for reasoning, planning, and generation of System Design Documents (SDDs) using specialized AI agents orchestrated by LangGraph.

**Start at Phase 1 and work sequentially.**

---

## Phase 1: Foundation & Setup (Start Here)

### 1.1 Dependencies (`requirements.txt`)
Start by defining your dependencies. Here's a suggested starter:

```txt
# Core orchestration
langgraph>=0.2.0          # Workflow orchestration (stateful graphs)
langchain>=0.1.0          # LLM framework and tooling
langchain-openai>=0.1.0  # OpenAI integration
langchain-community>=0.0.20  # Additional LangChain integrations

# LLM & Embeddings
openai>=1.0.0             # OpenAI API client
tiktoken>=0.5.0           # Token counting

# Data validation & models
pydantic>=2.0.0           # Data validation & models (DocumentState, Agent schemas)
pyyaml>=6.0.0             # Load YAML config files

# Database & RAG
psycopg2-binary>=2.9.0    # PostgreSQL adapter (for vector DB queries)
pgvector>=0.3.0          # PostgreSQL vector extension client
sqlalchemy>=2.0.0        # ORM/database toolkit

# Document processing
markdown>=3.4.0           # Markdown parsing and rendering
pyyaml>=6.0.0             # YAML frontmatter parsing
jsonschema>=4.0.0        # JSON Schema validation (for ReviewerAgent)

# MCP (Model Context Protocol) tools
# Note: MCP tools can be implemented as LangChain tools
# or custom Python functions that query the vector database

# Utilities
python-dotenv>=1.0.0      # Load .env file (API keys, database credentials)
tenacity>=8.2.0           # Retry decorators (automatic retries for API calls)
structlog>=23.0.0         # Structured logging

# CLI
click>=8.1.0              # Command-line interface framework
rich>=13.0.0              # Rich terminal output (progress bars, tables)

# Diagram generation (optional)
mermaid>=0.1.0            # Mermaid diagram rendering (if needed)
```

### 1.2 Environment Setup
- Ensure `.env` file exists in project root with:
  - `OPENAI_API_KEY` - Required for LLM calls
  - `DATABASE_URL` - PostgreSQL connection string for vector DB
- Ensure ETL pipeline has been run to populate the vector database
- Verify vector database is accessible and contains standards data

### 1.3 Project Structure
Create the following directory structure:

```
agent_app/
├── __init__.py
├── main.py                 # CLI entrypoint
├── agents/                 # Specialized agent classes
│   ├── __init__.py
│   ├── base.py            # BaseAgent abstract class
│   ├── system_architect_agent.py
│   ├── api_data_agent.py
│   ├── reviewer_agent.py
│   └── writer_formatter_agent.py
├── orchestration/          # LangGraph workflow
│   ├── __init__.py
│   ├── graph.py           # LangGraph definition
│   ├── state.py           # DocumentState schema
│   └── edges.py           # Conditional edge logic
├── tools/                  # MCP-style tools for agents
│   ├── __init__.py
│   ├── rag_tool.py        # Vector DB retrieval
│   └── mcp_tools.py       # Database schema queries
├── schemas/                # Pydantic models
│   ├── __init__.py
│   ├── document_state.py
│   ├── agent_output.py
│   └── review_feedback.py
├── utils/                  # Utilities
│   ├── __init__.py
│   ├── logging.py
│   ├── retry.py
│   └── validation.py
├── config/                 # Configuration files
│   ├── base.yaml
│   ├── local.yaml
│   └── prod.yaml
└── docs/                   # Documentation
    └── IMPLEMENTATION_GUIDE.md
```

---

## Phase 2: Data Models & Schemas (Foundation)

### 2.1 Define Core Schemas
**Start with:** `schemas/document_state.py`, `schemas/agent_output.py`, `schemas/review_feedback.py`

**Why first?** The LangGraph state and agent outputs depend on these data structures.

#### `schemas/document_state.py`
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum

class DocumentStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    FINAL = "FINAL"

class DocumentState(BaseModel):
    """Shared state object for LangGraph workflow."""
    
    # Input
    project_brief: str = Field(..., description="Original project brief/requirements")
    
    # Intermediate outputs
    hld_draft: Optional[str] = Field(None, description="High-Level Design draft")
    lld_draft: Optional[str] = Field(None, description="Low-Level Design draft")
    
    # Review & revision
    review_feedback: Optional[Dict[str, Any]] = Field(None, description="Structured review feedback")
    needs_revision: bool = Field(False, description="Flag set by ReviewerAgent")
    revision_count: int = Field(0, description="Number of revision cycles")
    max_revisions: int = Field(3, description="Maximum allowed revisions")
    
    # Final output
    final_document: Optional[str] = Field(None, description="Final formatted SDD")
    document_status: DocumentStatus = Field(DocumentStatus.DRAFT, description="Document status")
    
    # Metadata
    retrieved_context: Optional[list] = Field(None, description="RAG context chunks used")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict)
```

#### `schemas/agent_output.py`
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class AgentOutput(BaseModel):
    """Standard output format for all agents."""
    
    content: str = Field(..., description="Generated content")
    reasoning: Optional[str] = Field(None, description="Agent's reasoning process")
    sources: Optional[list] = Field(None, description="Sources/context used")
    confidence: Optional[float] = Field(None, description="Confidence score (0-1)")
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

#### `schemas/review_feedback.py`
```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from enum import Enum

class ReviewSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

class ReviewIssue(BaseModel):
    """Individual review issue/feedback item."""
    
    category: str = Field(..., description="Issue category (e.g., 'architecture', 'security')")
    severity: ReviewSeverity = Field(..., description="Issue severity")
    description: str = Field(..., description="Detailed description of the issue")
    suggestion: Optional[str] = Field(None, description="Suggested fix")
    location: Optional[str] = Field(None, description="Where in document (section, line)")

class ReviewFeedback(BaseModel):
    """Structured review feedback from ReviewerAgent."""
    
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    passes_validation: bool = Field(..., description="Whether document passes JSON Schema validation")
    issues: List[ReviewIssue] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    needs_revision: bool = Field(..., description="Whether revision is required")
```

---

## Phase 3: Base Classes & Interfaces

### 3.1 Base Agent Class
**Implement:** `agents/base.py`

**Why?** This defines the uniform API (`perform_action`) that all specialized agents must implement. This implements the **Strategy Pattern** at the agent level.

```python
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
```

**Key design principles:**
- All agents inherit from `BaseAgent`
- Uniform `perform_action(state) -> AgentOutput` interface
- Agents can declare required tools
- State validation before execution

---

## Phase 4: Utilities

### 4.1 Essential Utilities
**Implement:** `utils/logging.py`, `utils/retry.py`, `utils/validation.py`

**Why?** Used throughout the agent app for:
- Consistent structured logging
- Retry logic for LLM API calls
- JSON Schema validation for documents

#### `utils/logging.py`
```python
import structlog
import logging
from typing import Dict, Any

def setup_logging(config: Dict[str, Any] = None) -> structlog.BoundLogger:
    """Set up structured logging."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger()
```

#### `utils/retry.py`
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from openai import RateLimitError, APIError

def retry_llm_call(max_attempts: int = 3):
    """Decorator for retrying LLM API calls."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((RateLimitError, APIError)),
        reraise=True
    )
```

#### `utils/validation.py`
```python
import jsonschema
from typing import Dict, Any
import yaml
import re

def extract_yaml_frontmatter(markdown_content: str) -> Dict[str, Any]:
    """Extract YAML frontmatter from markdown document."""
    pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.match(pattern, markdown_content, re.DOTALL)
    if match:
        return yaml.safe_load(match.group(1))
    return {}

def validate_document_schema(document: str, schema: Dict[str, Any]) -> tuple[bool, list]:
    """
    Validate document against JSON Schema.
    
    Args:
        document: Markdown document with YAML frontmatter
        schema: JSON Schema definition
        
    Returns:
        (is_valid, list_of_errors)
    """
    try:
        frontmatter = extract_yaml_frontmatter(document)
        jsonschema.validate(instance=frontmatter, schema=schema)
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Validation error: {str(e)}"]
```

---

## Phase 5: Tools (RAG & MCP)

### 5.1 RAG Tool
**Implement:** `tools/rag_tool.py`

**Purpose:** Query the vector database to retrieve relevant context chunks for agents.

**Features:**
- Semantic search using embeddings
- Top-K retrieval (e.g., "best match 25")
- Metadata filtering
- Context formatting for LLM prompts

```python
from typing import List, Dict, Any, Optional
from agent_app.utils.logging import setup_logging

class RAGTool:
    """Tool for retrieving context from vector database."""
    
    def __init__(self, vector_db_connection, embedder, config: Dict[str, Any]):
        """
        Initialize RAG tool.
        
        Args:
            vector_db_connection: Database connection (from etl_pipeline or shared)
            embedder: Embedding model (same as used in ETL)
            config: Tool configuration (top_k, similarity_threshold, etc.)
        """
        self.db = vector_db_connection
        self.embedder = embedder
        self.config = config
        self.logger = setup_logging()
    
    def retrieve_context(
        self, 
        query: str, 
        top_k: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context chunks for a query.
        
        Args:
            query: Search query text
            top_k: Number of chunks to retrieve
            filters: Optional metadata filters (e.g., {"document_type": "standards"})
            
        Returns:
            List of chunk dictionaries with content, metadata, similarity score
        """
        # 1. Generate query embedding
        query_embedding = self.embedder.embed(query)
        
        # 2. Build SQL query with optional filters
        # 3. Execute similarity search
        # 4. Return formatted results
        
        # Example SQL (adjust based on your vector DB setup):
        # SELECT content, metadata, 1 - (embedding <=> %s::vector) as similarity
        # FROM document_chunks
        # WHERE ... (filters)
        # ORDER BY embedding <=> %s::vector
        # LIMIT %s
        
        pass
    
    def format_context_for_prompt(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into prompt-friendly context."""
        formatted = []
        for i, chunk in enumerate(chunks, 1):
            formatted.append(
                f"[Context {i}] (Similarity: {chunk.get('similarity', 0):.3f})\n"
                f"Source: {chunk.get('metadata', {}).get('source', 'unknown')}\n"
                f"Content: {chunk['content']}\n"
            )
        return "\n---\n".join(formatted)
```

### 5.2 MCP Tools
**Implement:** `tools/mcp_tools.py`

**Purpose:** Model Context Protocol tools for database schema queries and other structured data access.

**Features:**
- Query database schemas
- Access structured standards data
- Format results for LLM consumption

```python
from typing import Dict, Any, List

class MCPTools:
    """MCP-style tools for structured data access."""
    
    def __init__(self, db_connection, config: Dict[str, Any]):
        self.db = db_connection
        self.config = config
    
    def query_schema_standards(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Query database schema standards.
        
        Args:
            table_name: Optional specific table to query
            
        Returns:
            Schema standards information
        """
        # Query standards database for schema patterns
        pass
    
    def get_technology_list(self, category: Optional[str] = None) -> List[str]:
        """Get approved technology list for a category."""
        pass
```

---

## Phase 6: Specialized Agents

### 6.1 System Architect Agent
**Implement:** `agents/system_architect_agent.py`

**Responsibility:** High-Level Design (HLD), Component structure, Technology Rationale.

**Reasoning Approach:** Uses ReAct (Thought → Action → Observation) to research patterns via the RAG tool.

```python
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput
from agent_app.tools.rag_tool import RAGTool

class SystemArchitectAgent(BaseAgent):
    """Agent responsible for high-level system architecture design."""
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
        self.rag_tool: RAGTool = tools.get('rag_tool')
        self.llm = self._initialize_llm()
    
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Generate high-level design based on project brief.
        
        Uses ReAct pattern:
        1. Thought: Analyze requirements
        2. Action: Query RAG for relevant patterns
        3. Observation: Review retrieved context
        4. Thought: Synthesize architecture
        5. Action: Generate HLD
        """
        # 1. Retrieve relevant architectural patterns
        context = self.rag_tool.retrieve_context(
            query=f"System architecture patterns for: {state.project_brief}",
            top_k=25,
            filters={"document_type": "system_design"}
        )
        
        # 2. Format context for prompt
        formatted_context = self.rag_tool.format_context_for_prompt(context)
        
        # 3. Generate HLD using LLM with context
        prompt = self._build_hld_prompt(state.project_brief, formatted_context)
        hld_content = self._generate_with_llm(prompt)
        
        return AgentOutput(
            content=hld_content,
            reasoning="Researched architectural patterns via RAG, synthesized HLD",
            sources=[chunk.get('metadata', {}).get('source') for chunk in context],
            metadata={"context_chunks_used": len(context)}
        )
    
    def _build_hld_prompt(self, brief: str, context: str) -> str:
        """Build prompt for HLD generation."""
        return f"""
You are a senior system architect. Generate a High-Level Design (HLD) document.

Project Brief:
{brief}

Relevant Architectural Patterns and Standards:
{context}

Generate a comprehensive HLD including:
1. System Overview
2. Component Architecture
3. Technology Stack (with rationale)
4. High-level Data Flow
5. Scalability and Performance Considerations
6. Security Considerations

Format as structured markdown.
"""
    
    def get_required_tools(self) -> list:
        return ['rag_tool']
```

### 6.2 API Data Agent
**Implement:** `agents/api_data_agent.py`

**Responsibility:** Low-Level Design (LLD), Data Models, API Endpoints, Database Schemas.

**Reasoning Approach:** Uses MCP Tool to interact with the database (querying schema standards).

```python
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput
from agent_app.tools.mcp_tools import MCPTools

class APIDataAgent(BaseAgent):
    """Agent responsible for low-level design: APIs, data models, schemas."""
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
        self.mcp_tools: MCPTools = tools.get('mcp_tools')
        self.rag_tool = tools.get('rag_tool')
        self.llm = self._initialize_llm()
    
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Generate low-level design based on HLD.
        
        Uses:
        - MCP tools to query schema standards
        - RAG to retrieve API design patterns
        - LLM to generate detailed LLD
        """
        # 1. Query schema standards via MCP
        schema_standards = self.mcp_tools.query_schema_standards()
        
        # 2. Retrieve API design patterns via RAG
        api_context = self.rag_tool.retrieve_context(
            query=f"API design patterns and data modeling for: {state.hld_draft}",
            top_k=20,
            filters={"document_type": "standards", "category": "api_design"}
        )
        
        # 3. Generate LLD
        prompt = self._build_lld_prompt(
            state.hld_draft,
            schema_standards,
            self.rag_tool.format_context_for_prompt(api_context)
        )
        lld_content = self._generate_with_llm(prompt)
        
        return AgentOutput(
            content=lld_content,
            reasoning="Queried schema standards via MCP, retrieved API patterns via RAG",
            sources=[chunk.get('metadata', {}).get('source') for chunk in api_context],
            metadata={"schema_standards_used": True}
        )
    
    def get_required_tools(self) -> list:
        return ['mcp_tools', 'rag_tool']
```

### 6.3 Reviewer Agent
**Implement:** `agents/reviewer_agent.py`

**Responsibility:** Quality Assurance, Validation, and Self-Correction loop initiation.

**Reasoning Approach:** Uses JSON Schema validation and the Rubric to set the `needs_revision` flag in the LangGraph state.

```python
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput
from agent_app.schemas.review_feedback import ReviewFeedback, ReviewIssue, ReviewSeverity
from agent_app.utils.validation import validate_document_schema, extract_yaml_frontmatter
import json

class ReviewerAgent(BaseAgent):
    """Agent responsible for quality assurance and validation."""
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
        self.schema = self._load_validation_schema()
        self.rubric = config.get('rubric', {})
        self.llm = self._initialize_llm()
    
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Review document and generate structured feedback.
        
        Steps:
        1. Validate against JSON Schema
        2. Review content quality using rubric
        3. Generate structured feedback
        4. Set needs_revision flag
        """
        # Combine HLD and LLD for review
        combined_doc = self._combine_documents(state)
        
        # 1. Schema validation
        is_valid, validation_errors = validate_document_schema(
            combined_doc, 
            self.schema
        )
        
        # 2. Quality review using LLM + rubric
        quality_feedback = self._review_quality(combined_doc)
        
        # 3. Build structured review feedback
        review_feedback = ReviewFeedback(
            overall_score=quality_feedback.get('score', 0.0),
            passes_validation=is_valid,
            issues=self._build_issues(validation_errors, quality_feedback),
            strengths=quality_feedback.get('strengths', []),
            needs_revision=not is_valid or quality_feedback.get('score', 0.0) < 0.7
        )
        
        return AgentOutput(
            content=review_feedback.model_dump_json(),
            reasoning=f"Validated schema (pass: {is_valid}), reviewed quality (score: {review_feedback.overall_score})",
            metadata={
                "needs_revision": review_feedback.needs_revision,
                "validation_passed": is_valid
            }
        )
    
    def _review_quality(self, document: str) -> Dict[str, Any]:
        """Review document quality using LLM and rubric."""
        prompt = f"""
Review this System Design Document against the following rubric:

Rubric:
{json.dumps(self.rubric, indent=2)}

Document:
{document}

Provide:
1. Overall quality score (0-1)
2. List of strengths
3. List of issues with severity
4. Specific suggestions for improvement

Return as JSON.
"""
        # Call LLM and parse response
        pass
    
    def _build_issues(self, validation_errors: list, quality_feedback: Dict) -> List[ReviewIssue]:
        """Build list of ReviewIssue objects."""
        issues = []
        
        # Add validation errors
        for error in validation_errors:
            issues.append(ReviewIssue(
                category="validation",
                severity=ReviewSeverity.CRITICAL,
                description=error
            ))
        
        # Add quality issues from LLM review
        for issue in quality_feedback.get('issues', []):
            issues.append(ReviewIssue(
                category=issue.get('category', 'quality'),
                severity=ReviewSeverity(issue.get('severity', 'MEDIUM')),
                description=issue.get('description', ''),
                suggestion=issue.get('suggestion')
            ))
        
        return issues
```

### 6.4 Writer Formatter Agent
**Implement:** `agents/writer_formatter_agent.py`

**Responsibility:** Final document assembly, Markdown formatting, and rendering Mermaid code blocks.

**Reasoning Approach:** Ensures final output adheres to the document style guide retrieved via RAG.

```python
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput
from agent_app.tools.rag_tool import RAGTool

class WriterFormatterAgent(BaseAgent):
    """Agent responsible for final document formatting and assembly."""
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
        self.rag_tool: RAGTool = tools.get('rag_tool')
        self.llm = self._initialize_llm()
    
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
        # 1. Retrieve style guide
        style_guide = self.rag_tool.retrieve_context(
            query="document style guide formatting standards",
            top_k=10,
            filters={"document_type": "standards", "category": "style_guide"}
        )
        
        # 2. Combine documents
        combined = self._combine_documents(state)
        
        # 3. Format with style guide
        formatted = self._format_document(combined, style_guide)
        
        # 4. Generate Mermaid diagrams
        formatted = self._add_mermaid_diagrams(formatted, state)
        
        return AgentOutput(
            content=formatted,
            reasoning="Retrieved style guide, formatted markdown, added Mermaid diagrams",
            sources=[chunk.get('metadata', {}).get('source') for chunk in style_guide]
        )
    
    def _format_document(self, content: str, style_guide: List[Dict]) -> str:
        """Format document according to style guide."""
        # Apply formatting rules from style guide
        # Ensure proper markdown structure
        # Add YAML frontmatter
        pass
    
    def _add_mermaid_diagrams(self, content: str, state: DocumentState) -> str:
        """Add Mermaid diagram code blocks to document."""
        # Generate architecture diagrams
        # Generate data flow diagrams
        # Insert as code blocks
        pass
    
    def get_required_tools(self) -> list:
        return ['rag_tool']
```

---

## Phase 7: LangGraph Orchestration

### 7.1 State Schema
**Implement:** `orchestration/state.py`

**Purpose:** Define the shared state object that flows through the graph.

```python
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
```

### 7.2 Graph Definition
**Implement:** `orchestration/graph.py`

**Purpose:** Define the LangGraph workflow with nodes and edges.

```python
from langgraph.graph import StateGraph, END
from agent_app.orchestration.state import GraphState
from agent_app.agents.system_architect_agent import SystemArchitectAgent
from agent_app.agents.api_data_agent import APIDataAgent
from agent_app.agents.reviewer_agent import ReviewerAgent
from agent_app.agents.writer_formatter_agent import WriterFormatterAgent
from agent_app.orchestration.edges import should_revise, check_hitl

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
    """
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
        lambda state: "approved" if state.get('approved') else "revise",
        {
            "approved": END,
            "revise": "draft_hld"
        }
    )
    
    return workflow.compile()

def _run_agent(agent: BaseAgent, graph_state: GraphState) -> GraphState:
    """Helper to run agent and update state."""
    document_state = graph_state['state']
    output = agent.perform_action(document_state)
    
    # Update state based on agent output
    # (This varies by agent type)
    
    return graph_state
```

### 7.3 Conditional Edges
**Implement:** `orchestration/edges.py`

**Purpose:** Decision functions for conditional routing.

```python
from agent_app.orchestration.state import GraphState
from agent_app.schemas.review_feedback import ReviewFeedback
import json

def should_revise(graph_state: GraphState) -> str:
    """
    Decide whether to revise or continue.
    
    Returns:
        "revise" or "continue"
    """
    state = graph_state['state']
    
    # Check if reviewer set needs_revision flag
    if state.needs_revision:
        # Check if we've exceeded max revisions
        if state.revision_count >= state.max_revisions:
            # Force continue even if needs revision
            return "continue"
        return "revise"
    
    return "continue"

def check_hitl(graph_state: GraphState) -> GraphState:
    """
    Human-in-the-Loop checkpoint.
    
    Pauses workflow for human approval.
    """
    # In LangGraph, this would use a checkpoint/interrupt
    # For now, return state (implementation depends on LangGraph version)
    return graph_state
```

---

## Phase 8: Configuration

### 8.1 Config Files
**Set up:** `config/base.yaml`, `config/local.yaml`, `config/prod.yaml`

**Structure:**
```yaml
# config/base.yaml
agents:
  system_architect:
    model: "gpt-4"
    temperature: 0.7
    max_tokens: 4000
    reasoning_mode: "react"
  
  api_data:
    model: "gpt-4"
    temperature: 0.7
    max_tokens: 4000
  
  reviewer:
    model: "gpt-4"
    temperature: 0.3  # Lower for more consistent reviews
    validation_schema_path: "./schemas/sdd_schema.json"
    rubric_path: "./config/rubric.yaml"
    min_score_threshold: 0.7
  
  writer_formatter:
    model: "gpt-4"
    temperature: 0.5

tools:
  rag_tool:
    top_k: 25
    similarity_threshold: 0.7
    enable_reranking: false
  
  mcp_tools:
    db_connection_string: "${DATABASE_URL}"

orchestration:
  max_revisions: 3
  enable_hitl: true
  checkpoint_storage: "memory"  # or "file" for persistence

logging:
  level: "INFO"
  format: "json"
```

---

## Phase 9: Main Entrypoint

### 9.1 CLI Entrypoint
**Implement:** `main.py`

**Features:**
- Load configuration
- Initialize agents and tools
- Create LangGraph workflow
- Run workflow with project brief
- Handle output and errors

```python
import click
import yaml
from pathlib import Path
from agent_app.orchestration.graph import create_workflow_graph
from agent_app.agents.system_architect_agent import SystemArchitectAgent
from agent_app.agents.api_data_agent import APIDataAgent
from agent_app.agents.reviewer_agent import ReviewerAgent
from agent_app.agents.writer_formatter_agent import WriterFormatterAgent
from agent_app.tools.rag_tool import RAGTool
from agent_app.tools.mcp_tools import MCPTools
from agent_app.schemas.document_state import DocumentState
from agent_app.utils.logging import setup_logging

@click.command()
@click.option('--brief', required=True, help='Project brief/requirements')
@click.option('--config', default='config/local.yaml', help='Config file path')
@click.option('--output', default='output/sdd.md', help='Output file path')
@click.option('--verbose', is_flag=True, help='Verbose logging')
def main(brief: str, config: str, output: str, verbose: bool):
    """Generate System Design Document from project brief."""
    
    # 1. Load config
    config_path = Path(config)
    with open(config_path) as f:
        config_data = yaml.safe_load(f)
    
    # 2. Initialize logging
    logger = setup_logging()
    if verbose:
        logger.setLevel("DEBUG")
    
    # 3. Initialize tools
    rag_tool = RAGTool(...)  # Initialize with DB connection, embedder
    mcp_tools = MCPTools(...)  # Initialize with DB connection
    
    tools = {
        'rag_tool': rag_tool,
        'mcp_tools': mcp_tools
    }
    
    # 4. Initialize agents
    agents = {
        'system_architect': SystemArchitectAgent(
            config_data['agents']['system_architect'],
            tools
        ),
        'api_data': APIDataAgent(
            config_data['agents']['api_data'],
            tools
        ),
        'reviewer': ReviewerAgent(
            config_data['agents']['reviewer'],
            tools
        ),
        'writer_formatter': WriterFormatterAgent(
            config_data['agents']['writer_formatter'],
            tools
        )
    }
    
    # 5. Create workflow graph
    workflow = create_workflow_graph(agents, config_data)
    
    # 6. Initialize state
    initial_state = DocumentState(project_brief=brief)
    graph_state = {'state': initial_state}
    
    # 7. Run workflow
    logger.info("Starting SDD generation workflow", brief=brief)
    final_state = workflow.invoke(graph_state)
    
    # 8. Save output
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(final_state['state'].final_document)
    
    logger.info("SDD generated successfully", output=str(output_path))

if __name__ == '__main__':
    main()
```

---

## Phase 10: Testing

### 10.1 Unit Tests
- Test each agent in isolation
- Mock LLM calls and tools
- Test state validation

### 10.2 Integration Tests
- Test full workflow with sample brief
- Test revision loops
- Test error scenarios

### 10.3 Example Test
```python
import pytest
from agent_app.agents.system_architect_agent import SystemArchitectAgent
from agent_app.schemas.document_state import DocumentState

def test_system_architect_agent():
    """Test SystemArchitectAgent generates HLD."""
    config = {
        'model': 'gpt-4',
        'temperature': 0.7
    }
    
    # Mock RAG tool
    mock_rag = MockRAGTool()
    tools = {'rag_tool': mock_rag}
    
    agent = SystemArchitectAgent(config, tools)
    state = DocumentState(project_brief="E-commerce order processing microservice")
    
    output = agent.perform_action(state)
    
    assert output.content is not None
    assert len(output.content) > 0
    assert output.sources is not None
```

---

## Phase 11: Evaluations (Evals)

### 11.1 Why Evaluations Matter

**Evaluations (evals) are critical for:**
- **Quality Assurance**: Measure how well agents generate high-quality SDDs
- **Continuous Improvement**: Track performance over time and identify regressions
- **Prompt Engineering**: Test different prompts and configurations to find optimal settings
- **Agent Comparison**: Compare different agent implementations or model versions
- **Confidence Building**: Provide metrics that demonstrate system reliability
- **Debugging**: Identify which agents or stages are failing and why

**Types of Evaluations:**
1. **Functional Evals**: Does the agent produce the expected output structure?
2. **Quality Evals**: Is the content high-quality, accurate, and complete?
3. **Correctness Evals**: Does the output follow standards and requirements?
4. **End-to-End Evals**: Does the full workflow produce a valid, useful SDD?

### 11.2 Eval Framework Setup

**Dependencies to add:**
```txt
# Evaluation frameworks
langsmith>=0.1.0          # LangSmith for eval tracking and monitoring
pytest>=7.4.0             # Testing framework
pytest-asyncio>=0.21.0    # Async test support
pytest-cov>=4.1.0         # Coverage reporting

# Quality metrics
rouge-score>=0.1.2        # ROUGE scores for text quality
nltk>=3.8.1               # NLP utilities for evaluation
sentence-transformers>=2.2.0  # Semantic similarity (if not already included)
```

**Project structure:**
```
agent_app/
├── evals/                 # Evaluation suite
│   ├── __init__.py
│   ├── base.py           # Base eval classes
│   ├── functional/        # Functional evals
│   │   ├── __init__.py
│   │   ├── structure_eval.py
│   │   ├── schema_eval.py
│   │   └── completeness_eval.py
│   ├── quality/          # Quality evals
│   │   ├── __init__.py
│   │   ├── coherence_eval.py
│   │   ├── accuracy_eval.py
│   │   └── standards_compliance_eval.py
│   ├── end_to_end/       # Full workflow evals
│   │   ├── __init__.py
│   │   ├── workflow_eval.py
│   │   └── revision_loop_eval.py
│   ├── datasets/          # Test datasets
│   │   ├── test_briefs.yaml
│   │   └── golden_outputs/
│   └── metrics/           # Custom metrics
│       ├── __init__.py
│       └── sdd_metrics.py
└── tests/                 # Unit/integration tests (existing)
```

### 11.3 Base Eval Framework

**Implement:** `evals/base.py`

```python
"""Base evaluation framework."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from agent_app.schemas.agent_output import AgentOutput
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.review_feedback import ReviewFeedback
import json


class BaseEval(ABC):
    """Abstract base class for all evaluations."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize evaluator.
        
        Args:
            config: Evaluation configuration
        """
        self.config = config or {}
        self.name = self.__class__.__name__
    
    @abstractmethod
    def evaluate(
        self,
        output: AgentOutput,
        expected: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate agent output.
        
        Args:
            output: Agent output to evaluate
            expected: Expected output (for comparison)
            context: Additional context (state, inputs, etc.)
            
        Returns:
            Dictionary with:
            - score: float (0.0 to 1.0)
            - passed: bool
            - details: Dict with specific metrics
            - feedback: str (human-readable feedback)
        """
        pass
    
    def batch_evaluate(
        self,
        outputs: List[AgentOutput],
        expected: Optional[List[Any]] = None,
        contexts: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate multiple outputs and return aggregate metrics.
        
        Returns:
            Dictionary with:
            - mean_score: float
            - std_score: float
            - pass_rate: float
            - individual_results: List[Dict]
        """
        results = []
        for i, output in enumerate(outputs):
            exp = expected[i] if expected else None
            ctx = contexts[i] if contexts else None
            result = self.evaluate(output, exp, ctx)
            results.append(result)
        
        scores = [r['score'] for r in results]
        return {
            'mean_score': sum(scores) / len(scores) if scores else 0.0,
            'std_score': self._std_dev(scores),
            'pass_rate': sum(1 for r in results if r['passed']) / len(results) if results else 0.0,
            'individual_results': results
        }
    
    def _std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
```

### 11.4 Functional Evaluations

**Purpose:** Verify agents produce structurally correct outputs.

#### `evals/functional/structure_eval.py`

```python
"""Evaluate output structure and format."""

from agent_app.evals.base import BaseEval
from agent_app.schemas.agent_output import AgentOutput
import re
from typing import Dict, Any, Optional


class StructureEval(BaseEval):
    """Evaluate if output has correct structure (markdown, sections, etc.)."""
    
    def evaluate(
        self,
        output: AgentOutput,
        expected: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check output structure.
        
        Expected format:
        {
            "required_sections": ["Overview", "Architecture", "Components"],
            "min_length": 500,
            "max_length": 10000,
            "require_markdown": True
        }
        """
        content = output.content
        expected = expected or {}
        
        checks = {
            'has_content': len(content) > 0,
            'min_length': len(content) >= expected.get('min_length', 100),
            'max_length': len(content) <= expected.get('max_length', 50000),
            'has_markdown': self._has_markdown(content) if expected.get('require_markdown', True) else True,
            'has_required_sections': self._has_sections(content, expected.get('required_sections', []))
        }
        
        score = sum(checks.values()) / len(checks)
        passed = score >= 0.8  # 80% of checks must pass
        
        return {
            'score': score,
            'passed': passed,
            'details': checks,
            'feedback': self._generate_feedback(checks, content)
        }
    
    def _has_markdown(self, content: str) -> bool:
        """Check if content contains markdown formatting."""
        markdown_patterns = [
            r'^#+\s',  # Headers
            r'\*\*.*?\*\*',  # Bold
            r'\*.*?\*',  # Italic
            r'```',  # Code blocks
            r'\[.*?\]\(.*?\)'  # Links
        ]
        return any(re.search(pattern, content, re.MULTILINE) for pattern in markdown_patterns)
    
    def _has_sections(self, content: str, required_sections: List[str]) -> bool:
        """Check if content contains required sections."""
        if not required_sections:
            return True
        
        content_lower = content.lower()
        found = sum(1 for section in required_sections if section.lower() in content_lower)
        return found >= len(required_sections) * 0.8  # 80% of sections must be present
    
    def _generate_feedback(self, checks: Dict[str, bool], content: str) -> str:
        """Generate human-readable feedback."""
        failed = [k for k, v in checks.items() if not v]
        if not failed:
            return "✓ Structure is correct"
        return f"✗ Issues found: {', '.join(failed)}"
```

#### `evals/functional/schema_eval.py`

```python
"""Evaluate JSON Schema validation."""

from agent_app.evals.base import BaseEval
from agent_app.schemas.agent_output import AgentOutput
from agent_app.utils.validation import validate_document_schema, extract_yaml_frontmatter
from typing import Dict, Any, Optional


class SchemaEval(BaseEval):
    """Evaluate if output passes JSON Schema validation."""
    
    def __init__(self, schema: Dict[str, Any], config: Dict[str, Any] = None):
        """
        Initialize schema evaluator.
        
        Args:
            schema: JSON Schema to validate against
            config: Evaluation configuration
        """
        super().__init__(config)
        self.schema = schema
    
    def evaluate(
        self,
        output: AgentOutput,
        expected: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate output against JSON Schema."""
        content = output.content
        
        # Extract YAML frontmatter if present
        frontmatter = extract_yaml_frontmatter(content)
        
        # Validate
        is_valid, errors = validate_document_schema(content, self.schema)
        
        score = 1.0 if is_valid else max(0.0, 1.0 - (len(errors) * 0.2))  # Penalize per error
        passed = is_valid
        
        return {
            'score': score,
            'passed': passed,
            'details': {
                'is_valid': is_valid,
                'errors': errors,
                'frontmatter_present': bool(frontmatter)
            },
            'feedback': f"{'✓' if passed else '✗'} Schema validation: {len(errors)} errors"
        }
```

#### `evals/functional/completeness_eval.py`

```python
"""Evaluate output completeness."""

from agent_app.evals.base import BaseEval
from agent_app.schemas.agent_output import AgentOutput
from typing import Dict, Any, Optional, List
import re


class CompletenessEval(BaseEval):
    """Evaluate if output is complete (all required elements present)."""
    
    def evaluate(
        self,
        output: AgentOutput,
        expected: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check completeness.
        
        Expected format:
        {
            "required_elements": {
                "sections": ["Architecture", "Components"],
                "diagrams": ["architecture", "data_flow"],
                "tables": 1,
                "code_examples": 0
            }
        }
        """
        content = output.content
        expected = expected or {}
        required = expected.get('required_elements', {})
        
        checks = {
            'sections': self._check_sections(content, required.get('sections', [])),
            'diagrams': self._check_diagrams(content, required.get('diagrams', [])),
            'tables': self._check_tables(content, required.get('tables', 0)),
            'code_examples': self._check_code_blocks(content, required.get('code_examples', 0))
        }
        
        # Calculate score (weighted average)
        weights = {'sections': 0.4, 'diagrams': 0.3, 'tables': 0.2, 'code_examples': 0.1}
        score = sum(checks[k] * weights.get(k, 0.25) for k in checks)
        passed = score >= 0.8
        
        return {
            'score': score,
            'passed': passed,
            'details': checks,
            'feedback': f"Completeness: {score:.1%}"
        }
    
    def _check_sections(self, content: str, required: List[str]) -> float:
        """Check if required sections are present."""
        if not required:
            return 1.0
        content_lower = content.lower()
        found = sum(1 for section in required if section.lower() in content_lower)
        return found / len(required)
    
    def _check_diagrams(self, content: str, required: List[str]) -> float:
        """Check if required diagrams are present."""
        if not required:
            return 1.0
        # Look for mermaid code blocks or diagram references
        mermaid_blocks = len(re.findall(r'```mermaid', content, re.IGNORECASE))
        diagram_refs = sum(1 for d in required if d.lower() in content.lower())
        return min(1.0, (mermaid_blocks + diagram_refs) / len(required))
    
    def _check_tables(self, content: str, min_count: int) -> float:
        """Check if minimum number of tables present."""
        table_count = len(re.findall(r'\|.*\|', content))
        if min_count == 0:
            return 1.0
        return min(1.0, table_count / min_count)
    
    def _check_code_blocks(self, content: str, min_count: int) -> float:
        """Check if minimum number of code blocks present."""
        code_blocks = len(re.findall(r'```', content)) // 2  # Each block has opening and closing
        if min_count == 0:
            return 1.0
        return min(1.0, code_blocks / min_count)
```

### 11.5 Quality Evaluations

**Purpose:** Measure content quality, accuracy, and adherence to standards.

#### `evals/quality/coherence_eval.py`

```python
"""Evaluate content coherence and quality."""

from agent_app.evals.base import BaseEval
from agent_app.schemas.agent_output import AgentOutput
from typing import Dict, Any, Optional, List
from sentence_transformers import SentenceTransformer
import numpy as np


class CoherenceEval(BaseEval):
    """Evaluate content coherence using semantic similarity."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        # Load embedding model for semantic similarity
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    def evaluate(
        self,
        output: AgentOutput,
        expected: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate coherence by:
        1. Semantic similarity between sections
        2. Consistency of terminology
        3. Logical flow
        """
        content = output.content
        
        # Split into sections (by headers)
        sections = self._extract_sections(content)
        
        if len(sections) < 2:
            return {
                'score': 0.5,
                'passed': False,
                'details': {'reason': 'Not enough sections to evaluate coherence'},
                'feedback': 'Content too short for coherence evaluation'
            }
        
        # Calculate semantic similarity between adjacent sections
        similarities = []
        for i in range(len(sections) - 1):
            emb1 = self.embedder.encode(sections[i])
            emb2 = self.embedder.encode(sections[i + 1])
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            similarities.append(similarity)
        
        mean_similarity = np.mean(similarities)
        # Good coherence: similarity between 0.3-0.7 (related but distinct)
        score = 1.0 - abs(mean_similarity - 0.5) * 2  # Penalize if too similar or too different
        
        return {
            'score': max(0.0, min(1.0, score)),
            'passed': score >= 0.6,
            'details': {
                'mean_similarity': float(mean_similarity),
                'section_count': len(sections)
            },
            'feedback': f"Coherence score: {score:.2f} (similarity: {mean_similarity:.2f})"
        }
    
    def _extract_sections(self, content: str) -> List[str]:
        """Extract sections from markdown content."""
        import re
        # Split by headers (## or ###)
        sections = re.split(r'^##+\s', content, flags=re.MULTILINE)
        return [s.strip() for s in sections if s.strip() and len(s.strip()) > 50]
```

#### `evals/quality/standards_compliance_eval.py`

```python
"""Evaluate adherence to standards."""

from agent_app.evals.base import BaseEval
from agent_app.schemas.agent_output import AgentOutput
from agent_app.tools.rag_tool import RAGTool
from typing import Dict, Any, Optional, List


class StandardsComplianceEval(BaseEval):
    """Evaluate if output adheres to organizational standards."""
    
    def __init__(self, rag_tool: RAGTool, config: Dict[str, Any] = None):
        """
        Initialize standards compliance evaluator.
        
        Args:
            rag_tool: RAG tool to retrieve standards
            config: Evaluation configuration
        """
        super().__init__(config)
        self.rag_tool = rag_tool
    
    def evaluate(
        self,
        output: AgentOutput,
        expected: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check compliance by:
        1. Retrieving relevant standards
        2. Comparing output against standards
        3. Identifying violations
        """
        content = output.content
        project_brief = context.get('project_brief', '') if context else ''
        
        # Retrieve relevant standards
        standards = self.rag_tool.retrieve_context(
            query=f"Standards and guidelines for: {project_brief}",
            top_k=10,
            filters={"document_type": "standards"}
        )
        
        if not standards:
            return {
                'score': 0.5,
                'passed': False,
                'details': {'reason': 'No standards found'},
                'feedback': 'Could not retrieve standards for comparison'
            }
        
        # Check compliance (simplified - would use LLM for actual comparison)
        violations = []
        compliance_score = 1.0
        
        # Example: Check for required patterns
        required_patterns = self._extract_required_patterns(standards)
        for pattern in required_patterns:
            if pattern.lower() not in content.lower():
                violations.append(f"Missing required pattern: {pattern}")
                compliance_score -= 0.1
        
        score = max(0.0, compliance_score)
        passed = score >= 0.7
        
        return {
            'score': score,
            'passed': passed,
            'details': {
                'violations': violations,
                'standards_checked': len(standards)
            },
            'feedback': f"Standards compliance: {score:.1%} ({len(violations)} violations)"
        }
    
    def _extract_required_patterns(self, standards: List[Dict[str, Any]]) -> List[str]:
        """Extract required patterns from standards (simplified)."""
        # In practice, would use LLM to extract requirements
        patterns = []
        for std in standards:
            content = std.get('content', '')
            # Look for "must", "required", "shall" patterns
            # This is simplified - real implementation would be more sophisticated
            if 'must' in content.lower() or 'required' in content.lower():
                patterns.append(std.get('metadata', {}).get('title', ''))
        return patterns[:5]  # Limit to top 5
```

### 11.6 End-to-End Evaluations

**Purpose:** Test the full workflow with realistic scenarios.

#### `evals/end_to_end/workflow_eval.py`

```python
"""End-to-end workflow evaluation."""

from agent_app.evals.base import BaseEval
from agent_app.schemas.document_state import DocumentState
from agent_app.orchestration.graph import create_workflow_graph
from typing import Dict, Any, List, Optional
import json


class WorkflowEval(BaseEval):
    """Evaluate the complete workflow from brief to final document."""
    
    def __init__(self, agents: Dict, config: Dict[str, Any] = None):
        """
        Initialize workflow evaluator.
        
        Args:
            agents: Dictionary of initialized agents
            config: Evaluation configuration
        """
        super().__init__(config)
        self.agents = agents
        self.workflow = create_workflow_graph(agents, config)
    
    def evaluate(
        self,
        project_brief: str,
        expected_output: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run full workflow and evaluate result.
        
        Args:
            project_brief: Input project brief
            expected_output: Expected output characteristics
            
        Returns:
            Evaluation results
        """
        # Initialize state
        initial_state = DocumentState(project_brief=project_brief)
        graph_state = {'state': initial_state}
        
        # Run workflow
        try:
            final_state = self.workflow.invoke(graph_state)
            document_state = final_state['state']
        except Exception as e:
            return {
                'score': 0.0,
                'passed': False,
                'details': {'error': str(e)},
                'feedback': f'Workflow failed: {str(e)}'
            }
        
        # Evaluate final document
        checks = {
            'has_final_document': document_state.final_document is not None,
            'document_complete': len(document_state.final_document or '') > 1000,
            'no_critical_errors': document_state.revision_count < document_state.max_revisions,
            'status_final': document_state.document_status.value == 'FINAL'
        }
        
        score = sum(checks.values()) / len(checks)
        passed = score >= 0.75
        
        return {
            'score': score,
            'passed': passed,
            'details': {
                **checks,
                'revision_count': document_state.revision_count,
                'document_length': len(document_state.final_document or ''),
                'status': document_state.document_status.value
            },
            'feedback': f"Workflow {'passed' if passed else 'failed'}: {score:.1%}"
        }
```

### 11.7 Eval Dataset and Test Suite

**Create:** `evals/datasets/test_briefs.yaml`

```yaml
# Test dataset for evaluations
test_cases:
  - name: "ecommerce_microservice"
    brief: "Build an e-commerce order processing microservice with payment integration, inventory management, and order tracking"
    expected:
      required_sections:
        - "Architecture"
        - "Components"
        - "API Design"
        - "Data Models"
      min_length: 2000
      required_patterns:
        - "microservices"
        - "API"
        - "database"
  
  - name: "data_pipeline"
    brief: "Design a real-time data processing pipeline for IoT sensor data with 1M events/second throughput"
    expected:
      required_sections:
        - "Architecture"
        - "Data Flow"
        - "Scalability"
      min_length: 1500
      required_patterns:
        - "streaming"
        - "scalability"
        - "throughput"
  
  - name: "api_gateway"
    brief: "Create an API gateway for routing requests to multiple backend services with authentication and rate limiting"
    expected:
      required_sections:
        - "Architecture"
        - "Security"
        - "Rate Limiting"
      min_length: 1000
      required_patterns:
        - "authentication"
        - "rate limiting"
        - "routing"
```

**Create:** `evals/run_evals.py`

```python
"""Run evaluation suite."""

import yaml
from pathlib import Path
from agent_app.evals.functional.structure_eval import StructureEval
from agent_app.evals.functional.schema_eval import SchemaEval
from agent_app.evals.quality.coherence_eval import CoherenceEval
from agent_app.evals.end_to_end.workflow_eval import WorkflowEval
from agent_app.agents.system_architect_agent import SystemArchitectAgent
from agent_app.schemas.agent_output import AgentOutput
from agent_app.schemas.document_state import DocumentState
import json


def load_test_dataset(path: str = "evals/datasets/test_briefs.yaml"):
    """Load test dataset."""
    with open(path) as f:
        return yaml.safe_load(f)


def run_eval_suite(agents: Dict, tools: Dict, config: Dict):
    """Run complete evaluation suite."""
    
    # Load test dataset
    dataset = load_test_dataset()
    test_cases = dataset['test_cases']
    
    # Initialize evaluators
    structure_eval = StructureEval()
    coherence_eval = CoherenceEval()
    workflow_eval = WorkflowEval(agents, config)
    
    results = []
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {test_case['name']}")
        print(f"{'='*60}")
        
        # Test individual agents
        state = DocumentState(project_brief=test_case['brief'])
        
        # Test SystemArchitectAgent
        architect_agent = agents['system_architect']
        architect_output = architect_agent.perform_action(state)
        
        structure_result = structure_eval.evaluate(
            architect_output,
            expected=test_case.get('expected', {})
        )
        
        coherence_result = coherence_eval.evaluate(architect_output)
        
        # Test full workflow
        workflow_result = workflow_eval.evaluate(
            test_case['brief'],
            expected_output=test_case.get('expected', {})
        )
        
        # Aggregate results
        test_result = {
            'test_case': test_case['name'],
            'structure': structure_result,
            'coherence': coherence_result,
            'workflow': workflow_result,
            'overall_score': (
                structure_result['score'] * 0.3 +
                coherence_result['score'] * 0.3 +
                workflow_result['score'] * 0.4
            )
        }
        
        results.append(test_result)
        
        # Print summary
        print(f"Structure: {structure_result['score']:.2f} ({'✓' if structure_result['passed'] else '✗'})")
        print(f"Coherence: {coherence_result['score']:.2f} ({'✓' if coherence_result['passed'] else '✗'})")
        print(f"Workflow: {workflow_result['score']:.2f} ({'✓' if workflow_result['passed'] else '✗'})")
        print(f"Overall: {test_result['overall_score']:.2f}")
    
    # Generate report
    generate_report(results)
    
    return results


def generate_report(results: List[Dict]):
    """Generate evaluation report."""
    print(f"\n{'='*60}")
    print("EVALUATION REPORT")
    print(f"{'='*60}")
    
    overall_scores = [r['overall_score'] for r in results]
    mean_score = sum(overall_scores) / len(overall_scores) if overall_scores else 0.0
    
    print(f"\nMean Overall Score: {mean_score:.2f}")
    print(f"Tests Passed: {sum(1 for r in results if r['overall_score'] >= 0.7)}/{len(results)}")
    
    # Save detailed report
    report_path = Path("evals/reports/latest_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed report saved to: {report_path}")


if __name__ == '__main__':
    # Initialize agents and tools (from main.py)
    # Then run:
    # results = run_eval_suite(agents, tools, config)
    pass
```

### 11.8 Continuous Evaluation with LangSmith

**LangSmith Integration:**

```python
"""LangSmith integration for continuous evaluation."""

from langsmith import Client, traceable
from agent_app.agents.base import BaseAgent
from agent_app.schemas.agent_output import AgentOutput


class LangSmithEval:
    """LangSmith-based evaluation and monitoring."""
    
    def __init__(self, api_key: str = None):
        self.client = Client(api_key=api_key)
    
    @traceable(name="agent_perform_action")
    def trace_agent_execution(
        self,
        agent: BaseAgent,
        state: DocumentState
    ) -> AgentOutput:
        """Trace agent execution in LangSmith."""
        output = agent.perform_action(state)
        
        # Log to LangSmith
        self.client.create_run(
            name=agent.name,
            run_type="chain",
            inputs={"state": state.model_dump()},
            outputs={"output": output.model_dump()},
            metadata={
                "agent": agent.name,
                "confidence": output.confidence,
                "sources_count": len(output.sources or [])
            }
        )
        
        return output
    
    def create_eval_dataset(self, test_cases: List[Dict]):
        """Create LangSmith dataset from test cases."""
        dataset = self.client.create_dataset("sdd_generation_evals")
        
        for test_case in test_cases:
            self.client.create_example(
                dataset_name="sdd_generation_evals",
                inputs={"project_brief": test_case['brief']},
                outputs={"expected": test_case.get('expected', {})}
            )
        
        return dataset
```

### 11.9 Metrics Dashboard

**Key Metrics to Track:**
1. **Functional Metrics:**
   - Structure compliance rate
   - Schema validation pass rate
   - Completeness score

2. **Quality Metrics:**
   - Average coherence score
   - Standards compliance rate
   - Accuracy (vs golden outputs)

3. **Workflow Metrics:**
   - Average revision count
   - Workflow success rate
   - Average processing time

4. **Agent-Specific Metrics:**
   - SystemArchitectAgent: HLD quality, pattern usage
   - APIDataAgent: LLD completeness, schema correctness
   - ReviewerAgent: Review accuracy, false positive rate
   - WriterFormatterAgent: Formatting compliance

---

## Quick Start Checklist

- [ ] Phase 1: Set up `requirements.txt` and environment
- [ ] Phase 2: Implement core schemas (`document_state.py`, `agent_output.py`, `review_feedback.py`)
- [ ] Phase 3: Implement `BaseAgent` abstract class
- [ ] Phase 4: Implement utility functions (logging, retry, validation)
- [ ] Phase 5: Implement RAG tool and MCP tools
- [ ] Phase 6: Implement specialized agents (start with SystemArchitectAgent)
- [ ] Phase 7: Implement LangGraph orchestration (state, graph, edges)
- [ ] Phase 8: Set up configuration files
- [ ] Phase 9: Implement main entrypoint
- [ ] Phase 10: Test with sample project brief
- [ ] Phase 11: Set up evaluation framework and run evals

---

## Pro Tips

1. **Start with one agent:** Get `SystemArchitectAgent` working end-to-end first
2. **Mock external dependencies:** Use mocks for LLM calls and DB queries during development
3. **Test incrementally:** After each phase, test with a simple project brief
4. **Log everything:** Structured logging helps debug complex agent interactions
5. **Handle errors gracefully:** Use retry utilities for LLM API calls
6. **Validate state:** Ensure agents validate state before execution
7. **Iterate on prompts:** Agent performance heavily depends on prompt quality

---

## Integration with ETL Pipeline

The agent app depends on the ETL pipeline:

1. **Vector Database:** Must be populated with standards documents
2. **Embedding Model:** Should use the same model as ETL for consistency
3. **Database Connection:** Share connection configuration with ETL

**Recommended approach:**
- Create a `shared_core` module for shared utilities (DB connection, config loading)
- Or import utilities from `etl_pipeline` (if in same monorepo)

---

## Frontend Development Plans

### Overview

While the current implementation focuses on the backend (CLI-based), there are plans to develop a **web frontend using Angular** to provide a user-friendly interface for the SDD generation workflow.

### Frontend Architecture

**Technology Stack:**
- **Framework:** Angular (TypeScript)
- **State Management:** NgRx or Angular Services
- **UI Components:** Angular Material or PrimeNG
- **Real-time Updates:** WebSockets or Server-Sent Events (SSE)
- **Markdown Rendering:** Marked.js or similar
- **Diagram Rendering:** Mermaid.js for architecture diagrams

**Planned Features:**
1. **Project Brief Input Form**
   - Rich text editor for project brief
   - Structured requirements input (functional, non-functional, constraints)
   - File upload for requirements JSON/YAML
   - Additional context field

2. **Workflow Progress Dashboard**
   - Real-time workflow status visualization
   - Agent execution progress (SystemArchitect → APIData → Reviewer → WriterFormatter)
   - Revision loop indicators
   - Estimated time remaining

3. **Document Viewer/Editor**
   - Live preview of generated SDD (HLD, LLD, Final)
   - Markdown rendering with syntax highlighting
   - Mermaid diagram visualization
   - Side-by-side comparison (before/after revisions)
   - Export options (Markdown, PDF, HTML)

4. **Clarification Interface**
   - Display agent clarification requests
   - Input form for user responses
   - Clarification history/Q&A log
   - Context-aware suggestions

5. **Review Feedback Display**
   - Review score visualization
   - Issues list with severity indicators
   - Strengths and suggestions
   - Revision decision interface (Approve/Request Changes)

6. **Human-in-the-Loop (HITL) Checkpoint**
   - Final approval interface
   - Request changes with comments
   - Document status management

### Backend API Requirements

To support the Angular frontend, the backend will need:

**REST API Endpoints:**
```python
# Workflow Management
POST   /api/workflows/start          # Start workflow with brief
GET    /api/workflows/{id}           # Get workflow status
GET    /api/workflows/{id}/state     # Get current DocumentState
POST   /api/workflows/{id}/clarify   # Provide clarification answer
POST   /api/workflows/{id}/approve   # HITL approval
POST   /api/workflows/{id}/revise    # Request revision with context

# Document Access
GET    /api/workflows/{id}/document  # Get current document
GET    /api/workflows/{id}/hld       # Get HLD draft
GET    /api/workflows/{id}/lld       # Get LLD draft
GET    /api/workflows/{id}/final     # Get final document

# Review & Feedback
GET    /api/workflows/{id}/feedback  # Get review feedback
GET    /api/workflows/{id}/issues    # Get review issues

# Real-time Updates
WS     /ws/workflows/{id}            # WebSocket for live updates
```

**API Implementation Approach:**
- Add FastAPI or Flask REST API layer on top of existing agent_app
- Use existing CLI functions as service layer
- WebSocket/SSE for real-time workflow progress
- LangGraph checkpoints for HITL integration

### Development Phases

**Phase 1: Backend API Layer** (Current Focus)
- Complete agent implementation
- Add REST API wrapper
- Implement WebSocket/SSE for real-time updates
- Add workflow state persistence

**Phase 2: Angular Frontend Foundation**
- Set up Angular project structure
- Implement authentication (if needed)
- Create base components and routing
- Set up state management

**Phase 3: Core Features**
- Project brief input form
- Workflow progress dashboard
- Document viewer
- Basic clarification interface

**Phase 4: Advanced Features**
- Real-time updates via WebSocket
- Review feedback visualization
- HITL checkpoint interface
- Document export functionality

**Phase 5: Polish & Optimization**
- UI/UX improvements
- Performance optimization
- Error handling and user feedback
- Documentation and help system

### Integration Points

The Angular frontend will integrate with the backend through:

1. **REST API:** Standard HTTP requests for workflow control
2. **WebSocket/SSE:** Real-time workflow progress updates
3. **LangGraph Checkpoints:** For HITL pause/resume functionality
4. **State Synchronization:** Keep frontend state in sync with backend DocumentState

### Benefits of Angular Frontend

- **Better UX:** Visual workflow progress vs. CLI output
- **Interactive Clarifications:** Real-time Q&A interface
- **Document Preview:** Live preview of generated SDD
- **Collaboration:** Multiple users can view/review documents
- **Accessibility:** Web-based access from any device
- **Professional Interface:** Polished UI for production use

### Current Status

**Backend:** ✅ In development (CLI-based, fully functional)
**Frontend:** 📋 Planned (Angular implementation to follow)

The backend is designed to be API-ready, making frontend integration straightforward once the core agent functionality is complete.

---

## Next Steps After Basic Implementation

- Add streaming responses for real-time feedback
- Implement agent memory/context windows
- Add metrics and monitoring
- Optimize RAG retrieval (reranking, query expansion)
- Add support for multiple LLM providers
- Implement agent collaboration patterns
- Add document versioning and history

