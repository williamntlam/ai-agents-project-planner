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
│   ├── system_architect.py
│   ├── api_data.py
│   ├── reviewer.py
│   └── writer_formatter.py
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
**Implement:** `agents/system_architect.py`

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
**Implement:** `agents/api_data.py`

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
**Implement:** `agents/reviewer.py`

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
**Implement:** `agents/writer_formatter.py`

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
from agent_app.agents.system_architect import SystemArchitectAgent
from agent_app.agents.api_data import APIDataAgent
from agent_app.agents.reviewer import ReviewerAgent
from agent_app.agents.writer_formatter import WriterFormatterAgent
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
from agent_app.agents.system_architect import SystemArchitectAgent
from agent_app.agents.api_data import APIDataAgent
from agent_app.agents.reviewer import ReviewerAgent
from agent_app.agents.writer_formatter import WriterFormatterAgent
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
from agent_app.agents.system_architect import SystemArchitectAgent
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

## Next Steps After Basic Implementation

- Add streaming responses for real-time feedback
- Implement agent memory/context windows
- Add metrics and monitoring
- Optimize RAG retrieval (reranking, query expansion)
- Add support for multiple LLM providers
- Implement agent collaboration patterns
- Add document versioning and history

