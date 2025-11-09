# 🤖 Project: Autonomous System Design Document (SDD) Generator Agent

This document outlines the architecture and components of a powerful, self-correcting AI agent system designed to automate the creation of high-quality, standards-compliant System Design Documents (SDDs).

## 1. Project Goal and Core Architecture

The primary goal is to transform a simple project brief into a fully structured SDD by coordinating multiple specialized AI agents. The core architecture relies on **Agentic Retrieval-Augmented Generation (RAG)** and **Model Context Protocol (MCP)** principles, orchestrated by **LangGraph** and powered by **LangChain**.

### 1.1 Architectural Pillars

**Orchestration (LangGraph):** Manages the multi-step, cyclical workflow using stateful graphs with conditional edges. Implements automated review and revision loops with Human-in-the-Loop (HITL) checkpoints. The workflow is defined as a `StateGraph` with typed state management via Pydantic models.

**Modularity (Object-Oriented Agents):** Uses specialized, highly focused agents that inherit from a `BaseAgent` abstract base class. Each agent implements the Strategy Pattern with a uniform `perform_action(state: DocumentState) -> AgentOutput` interface, allowing polymorphic agent execution by the orchestrator.

**Knowledge Base (RAG/ETL):** Grounds all generated content in a PostgreSQL vector database (pgvector) containing internal software engineering standards. The ETL pipeline processes documents through extraction, transformation (chunking, embedding), and loading phases.

**LLM Integration (LangChain):** All agents use LangChain's `ChatOpenAI` for LLM interactions, with structured message handling via `SystemMessage` and `HumanMessage` classes. Agents leverage LangChain's tooling ecosystem for RAG and MCP operations.

### 1.2 Repository Structure (Monorepo)

To balance maintainability and ease of setup, the project uses a monorepo structure with strict module boundaries:

```
/ai-agents-project-planner
|-- /agent_app/                 # Real-time Logic & Orchestration (LangGraph)
|   |-- /agents/                # Specialized agent implementations
|   |   |-- base.py             # BaseAgent abstract class (Strategy Pattern)
|   |   |-- system_architect_agent.py
|   |   |-- api_data_agent.py
|   |   |-- reviewer_agent.py
|   |   |-- writer_formatter_agent.py
|   |   |-- security_agent.py  # (Optional, partially implemented)
|   |   |-- performance_agent.py  # (Optional, partially implemented)
|   |   |-- documentation_agent.py  # (Optional, partially implemented)
|   |-- /orchestration/         # LangGraph workflow definition
|   |   |-- graph.py            # StateGraph creation and node/edge definitions
|   |   |-- graph_state.py      # TypedDict for LangGraph state
|   |   |-- graph_edges.py      # Conditional edge decision functions
|   |-- /tools/                 # RAG and MCP tool implementations
|   |   |-- rag_tool.py         # Vector database retrieval tool
|   |   |-- mcp_tools.py       # Model Context Protocol tools for structured queries
|   |-- /schemas/                 # Pydantic models for type safety
|   |   |-- document_state.py   # Core DocumentState (shared memory)
|   |   |-- agent_output.py     # AgentOutput schema
|   |   |-- review_feedback.py  # ReviewFeedback schema
|   |-- main.py                 # CLI entrypoint (Click-based)
|-- /etl_pipeline/              # Batch Data Ingestion (RAG Prep)
|   |-- /extractors/            # Document extraction (filesystem, future: S3, GitHub)
|   |-- /transformers/          # Chunking, embedding, metadata enrichment
|   |-- /loaders/               # Vector DB loader (pgvector), audit loader
|   |-- /models/                # Pydantic models (Document, Chunk, RawDocument)
|   |-- main.py                 # ETL CLI entrypoint
|-- /data/                      # Source documents (standards, system design patterns)
|   |-- /standards/             # Coding standards, security practices, etc.
|   |-- /system_design/         # Architecture patterns, design patterns, etc.
|-- /output/                    # Generated SDD documents
|-- README.md
```

## 2. Agent Application (/agent_app)

This module houses the logic for reasoning, planning, and generation using LangChain and LangGraph.

### 2.1 Object-Oriented Agent Design

All specialized agents inherit from **`BaseAgent`** (Abstract Base Class) to ensure a uniform API (`perform_action`) for the Orchestrator. This implements the **Strategy Pattern** at the agent level, allowing the LangGraph orchestrator to treat all agents polymorphically.

**BaseAgent Features:**
- Abstract `perform_action(state: DocumentState) -> AgentOutput` method
- Tool validation (`get_required_tools()`, `_validate_tools()`)
- State validation (`validate_state()`, `_validate_and_execute()`)
- Structured logging via `structlog`
- Configuration management (`get_config_value()`)
- Error handling and retry logic support

| Agent Class | Responsibility | Key Reasoning Concept | Tools Used |
|--------------|----------------|------------------------|------------|
| **SystemArchitectAgent** | High-Level Design (HLD), Component structure, Technology Rationale. | Uses **ReAct pattern** (Reasoning + Acting): 1. **Thought**: Analyze requirements 2. **Action**: Query RAG for architectural patterns 3. **Observation**: Review retrieved context 4. **Thought**: Synthesize architecture 5. **Action**: Generate HLD using LangChain ChatOpenAI | `RAGTool` for semantic search, `ChatOpenAI` (gpt-4o-mini) for generation |
| **APIDataAgent** | Low-Level Design (LLD), Data Models, API Endpoints, Database Schemas. | Combines **MCP tools** for structured schema standards queries with **RAG** for API design patterns. Uses LangChain for LLM orchestration. | `MCPTools` (query_schema_standards), `RAGTool`, `ChatOpenAI` |
| **ReviewerAgent** | Quality Assurance, Validation, and Self-Correction loop initiation. | Uses **JSON Schema validation** (jsonschema library) and **LLM-based rubric scoring** to evaluate document quality. Sets `needs_revision` flag in DocumentState to control LangGraph conditional edges. | JSON Schema validator, `ChatOpenAI` for quality review, configurable rubric |
| **WriterFormatterAgent** | Final document assembly, Markdown formatting, and rendering Mermaid code blocks. | Retrieves document style guide via RAG, uses LangChain to format markdown with YAML frontmatter, generates Mermaid diagrams via LLM. | `RAGTool` for style guide, `ChatOpenAI` for formatting and diagram generation |

**Additional Agents (Partially Implemented):**
- `SecurityAgent`: Security analysis and recommendations (TODO: full implementation)
- `PerformanceAgent`: Performance optimization recommendations (TODO: full implementation)
- `DocumentationAgent`: Additional documentation generation (TODO: full implementation)

### 2.2 LangGraph Orchestration & Workflow

The workflow is a **stateful graph** (`StateGraph` from LangGraph) that enforces a robust review and revision cycle. The state is managed through a `GraphState` TypedDict containing a `DocumentState` Pydantic model.

**Workflow Definition (`orchestration/graph.py`):**

```python
Workflow Steps:
1. draft_hld (SystemArchitectAgent) → Generates HLD draft
2. draft_lld (APIDataAgent) → Generates LLD draft (depends on HLD)
3. review_doc (ReviewerAgent) → Reviews both drafts, sets needs_revision flag
4. should_revise? (Conditional Edge) → Decision function checks needs_revision
   - "revise" → Loops back to draft_hld (revision_count incremented)
   - "continue" → Proceeds to format_doc
5. format_doc (WriterFormatterAgent) → Assembles final SDD with YAML frontmatter
6. human_review (HITL checkpoint) → Pauses for human approval
   - "approved" → END
   - "revise" → Loops back to draft_hld
```

**State Management:**

The `DocumentState` (Pydantic model) serves as the **shared memory** for the entire workflow:

- **Input Fields:** `project_brief`, `additional_context`, `user_clarifications`, `requirements`
- **Intermediate Outputs:** `hld_draft`, `lld_draft`
- **Review Control:** `review_feedback` (Dict), `needs_revision` (bool), `revision_count` (int), `max_revisions` (int)
- **Final Output:** `final_document`, `document_status` (Enum: DRAFT, REVIEW, FINAL)
- **Metadata:** `retrieved_context` (RAG chunks used), `processing_metadata` (timestamps, config)

**Conditional Edges (`orchestration/graph_edges.py`):**

- `should_revise(graph_state: GraphState) -> str`: Checks `needs_revision` flag and `revision_count < max_revisions`. Returns `"revise"` or `"continue"`.
- `check_hitl(graph_state: GraphState) -> GraphState`: Human-in-the-Loop checkpoint (currently returns state; full HITL implementation depends on LangGraph checkpoint features).

**Node Execution (`_run_agent` function):**

Each node wraps an agent's `perform_action()` method:
1. Extracts `DocumentState` from `GraphState`
2. Calls `agent.perform_action(document_state)`
3. Updates `DocumentState` based on agent type (e.g., SystemArchitectAgent updates `hld_draft`)
4. Updates graph metadata (`current_node`, `iteration_count`)
5. Returns updated `GraphState`

### 2.3 ReAct Pattern Implementation

The **SystemArchitectAgent** implements the ReAct (Reasoning + Acting) pattern:

1. **Thought**: Analyzes project requirements from `project_brief`
2. **Action**: Queries RAG tool with semantic search: `rag_tool.retrieve_context(query, top_k=25)`
3. **Observation**: Reviews retrieved context chunks (architectural patterns, best practices)
4. **Thought**: Synthesizes architecture based on requirements + retrieved knowledge
5. **Action**: Generates HLD using LangChain's `ChatOpenAI.invoke()` with structured prompts

The RAG tool uses:
- **Embedding Model**: OpenAI `text-embedding-3-small` (1536 dimensions)
- **Vector Search**: pgvector cosine similarity search via `PgVectorLoader.get_best_matches()`
- **Context Formatting**: `format_context_for_prompt()` formats chunks with similarity scores and sources

### 2.4 LangChain Integration

All agents use **LangChain** for LLM interactions:

- **LLM Client**: `ChatOpenAI` from `langchain_openai` (configurable model, temperature, max_tokens)
- **Message Types**: `SystemMessage` (system prompts with agent role/instructions) and `HumanMessage` (user prompts with context)
- **Tool Integration**: RAG and MCP tools are integrated as callable functions, not LangChain Tools (simpler architecture)
- **Structured Outputs**: Agents return `AgentOutput` (Pydantic model) with `content`, `reasoning`, `sources`, `confidence`, `metadata`

### 2.5 MCP Tools Implementation

**MCPTools** (`tools/mcp_tools.py`) provides structured database queries following Model Context Protocol principles:

- **`query_schema_standards()`**: Queries PostgreSQL `document_chunks` table for schema design patterns, normalization rules, and database best practices. Uses SQL with metadata filtering (document_source, category, content keywords).
- **`get_technology_list()`**: Extracts approved technology lists from standards documents using regex patterns and metadata tags.
- **`format_for_llm()`**: Formats structured query results into LLM-friendly text for prompt injection.

Uses SQLAlchemy for connection pooling and psycopg2 for direct PostgreSQL queries.

## 3. ETL Pipeline (/etl_pipeline)

This pipeline is crucial for maintaining the quality and relevance of the agent's knowledge. It is triggered independently of the real-time agent app (e.g., via CLI: `python -m etl_pipeline.main`).

### 3.1 ETL Stages (Implemented)

| Stage | Process | Implementation Details | Output |
|--------|----------|-------------------------|---------|
| **E - Extract** | Loads raw standards documents from filesystem | `FilesystemExtractor`: Recursively scans configured directories, supports Markdown, PDF, DOCX. Extracts text content and file metadata. | `RawDocument` objects (Pydantic models) with `content`, `source`, `metadata` |
| **T - Transform** | 1. Normalization 2. Chunking 3. Embedding 4. Metadata Enrichment | **Normalizer**: Cleans text, handles encoding. **Chunker**: Uses LangChain's `RecursiveCharacterTextSplitter` (chunk_size=1000, overlap=200) or `MarkdownHeaderTextSplitter` for markdown-aware chunking. **Embedder**: OpenAI `text-embedding-3-small` (batch processing, 1536 dimensions). **MetadataEnricher**: Adds document_category, parent_directory, file metadata to chunks. | `Chunk` objects with `content`, `embedding` (vector), `metadata` (JSON) |
| **L - Load** | Upserts chunks into pgvector database | `PgVectorLoader`: Creates pgvector extension, `document_chunks` table with vector column. Batch upserts with conflict resolution (ON CONFLICT DO UPDATE). Creates IVFFlat or HNSW vector index for fast similarity search. Connection pooling via SQLAlchemy. | Live, searchable vector database with indexed chunks |

### 3.2 Vector Database: pgvector

**Implementation Details:**

- **Database**: PostgreSQL with pgvector extension
- **Table Schema**: `document_chunks` with columns:
  - `id` (UUID, primary key)
  - `document_id` (UUID, foreign key to documents table)
  - `chunk_index` (integer)
  - `content` (text)
  - `embedding` (vector(1536)) - pgvector column type
  - `metadata` (JSONB) - stores source, category, tags, etc.
  - `created_at` (timestamp)

- **Indexing**: IVFFlat or HNSW index on embedding column for fast approximate nearest neighbor search
- **Similarity Search**: Uses pgvector's `<=>` operator (cosine distance) in SQL queries
- **Connection Pooling**: SQLAlchemy QueuePool (pool_size=5, max_overflow=10)

### 3.3 RAG Tool Implementation

**RAGTool** (`agent_app/tools/rag_tool.py`):

- **Query Embedding**: Uses same embedder as ETL (`text-embedding-3-small`) to generate query vector
- **Similarity Search**: Calls `PgVectorLoader.get_best_matches(query_embedding, top_k, filters)` which executes SQL:
  ```sql
  SELECT *, embedding <=> %s AS similarity
  FROM document_chunks
  WHERE metadata @> %s  -- JSONB filter
  ORDER BY similarity
  LIMIT %s
  ```
- **Threshold Filtering**: Applies `similarity_threshold` (configurable) to filter low-relevance chunks
- **Context Formatting**: Formats chunks with similarity scores, sources, and content for LLM prompts

### 3.4 Standards Data Structure

The `/data` directory contains:
- **`/standards/`**: Coding standards, security best practices, logging standards, OOP principles
- **`/system_design/`**: Architecture patterns (microservices, event-driven), design patterns (creational, structural, behavioral), database design, API design, scalability patterns, etc.

Documents are processed by ETL pipeline and stored as chunks in the vector database with metadata tags for filtering.

## 4. Document Structure & Output Format

The final SDD uses a highly structured, machine-readable format.

### 4.1 Document Format: Structured Markdown

The final output is a Markdown file using three layers:

1. **YAML Frontmatter (Metadata):** Generated by `WriterFormatterAgent` using PyYAML. Contains:
   - `title`: "System Design Document"
   - `status`: "FINAL" (or "DRAFT", "REVIEW")
   - `created_at`: ISO 8601 timestamp
   - `version`: "1.0"
   - `project_brief`: Truncated brief
   - `revision_count`: Number of revisions (if > 0)

2. **Markdown Body:** Formatted by `WriterFormatterAgent` using LangChain LLM with style guide context from RAG. Includes:
   - High-Level Design section (from `SystemArchitectAgent`)
   - Low-Level Design section (from `APIDataAgent`)
   - Proper heading hierarchy
   - Code blocks for technical specifications

3. **Mermaid Blocks:** Generated by `WriterFormatterAgent` using LLM. Diagram types:
   - Architecture diagrams (`graph TD` or `graph LR`)
   - Data flow diagrams (`flowchart`)
   - Database schema diagrams (`erDiagram`)

### 4.2 JSON Schema Validation

The `ReviewerAgent` uses the `jsonschema` library to validate document structure:
- Validates YAML frontmatter against a JSON Schema (configurable path)
- Checks required fields, data types, and enum values (e.g., `status` must be DRAFT, REVIEW, or FINAL)
- Validation errors are added as CRITICAL severity issues in review feedback

### 4.3 Review Rubric

The `ReviewerAgent` uses a configurable rubric (YAML file or config dict) with weighted criteria:
- **Completeness** (weight: 0.3): All required sections present, sufficient detail
- **Quality** (weight: 0.3): Best practices, appropriate technology choices
- **Standards Compliance** (weight: 0.2): Coding standards, security, performance
- **Clarity** (weight: 0.2): Readable, well-documented, easy to understand

The agent uses LangChain LLM to score each criterion and calculate an overall score (0.0-1.0). If score < `min_score_threshold` (default: 0.7) or critical issues found, `needs_revision=True`.

## 5. Technology Stack

### 5.1 Core Frameworks

- **LangGraph** (>=0.2.0): Workflow orchestration with stateful graphs
- **LangChain** (>=0.1.0): LLM framework, tooling, text splitters
- **LangChain OpenAI** (>=0.1.0): OpenAI integration (`ChatOpenAI`)
- **LangChain Community** (>=0.0.20): Additional integrations
- **LangChain Text Splitters** (>=0.0.1): Document chunking (`RecursiveCharacterTextSplitter`, `MarkdownHeaderTextSplitter`)

### 5.2 LLM & Embeddings

- **OpenAI** (>=1.0.0): OpenAI API client
- **Tiktoken** (>=0.5.0): Token counting for prompt management

### 5.3 Data & Validation

- **Pydantic** (>=2.0.0): Data validation and models (`DocumentState`, `AgentOutput`, `ReviewFeedback`)
- **PyYAML** (>=6.0.0): YAML config and frontmatter generation
- **jsonschema** (>=4.0.0): JSON Schema validation for documents

### 5.4 Database & Vector Search

- **PostgreSQL** with **pgvector** extension: Vector database
- **psycopg2-binary** (>=2.9.0): PostgreSQL adapter
- **pgvector** (>=0.3.0): PostgreSQL vector extension client
- **SQLAlchemy** (>=2.0.0): ORM and connection pooling

### 5.5 Utilities

- **structlog** (>=23.0.0): Structured logging
- **tenacity** (>=8.2.0): Retry decorators for API calls
- **click** (>=8.1.0): CLI framework
- **python-dotenv** (>=1.0.0): Environment variable management

## 6. Getting Started

### 6.1 Prerequisites

- Python 3.10+
- PostgreSQL 12+ with pgvector extension installed
- OpenAI API key

### 6.2 Setup Steps

1. **Clone and Install Dependencies:**
   ```bash
   cd ai-agents-project-planner
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r agent_app/requirements.txt
   pip install -r etl_pipeline/requirements.txt
   ```

2. **Configure Environment:**
   - Set `OPENAI_API_KEY` environment variable
   - Set `DATABASE_URL` environment variable (PostgreSQL connection string)
   - Create config files: `config/local.yaml` (see agent config structure)

3. **Initialize Vector Database:**
   ```bash
   # Ensure PostgreSQL is running with pgvector extension
   # The ETL pipeline will create tables and indexes automatically
   python -m etl_pipeline.main --config config/etl_local.yaml
   ```

4. **Ingest Standards Data:**
   ```bash
   # Process documents from /data directory into vector database
   python -m etl_pipeline.main --config config/etl_local.yaml
   ```

5. **Run Agent:**
   ```bash
   # Generate SDD from project brief
   python -m agent_app.main --brief "E-commerce order processing microservice" \
     --config config/local.yaml \
     --output output/sdd.md \
     --verbose
   ```

### 6.3 Configuration Files

- **Agent Config** (`config/local.yaml`): Agent model settings, tool configs, validation schema paths
- **ETL Config** (`config/etl_local.yaml`): Extractor paths, chunking settings, embedding model, database connection

### 6.4 Workflow Execution Flow

1. **Initialization**: Load config, initialize RAG tool (pgvector connection + embedder), initialize MCP tools (PostgreSQL connection), create agent instances
2. **Workflow Execution**: LangGraph compiles and invokes workflow with initial `DocumentState`
3. **Agent Execution**: Each agent reads from/writes to `DocumentState`, uses tools (RAG, MCP), calls LangChain LLM
4. **Revision Loop**: If `needs_revision=True`, workflow loops back to `draft_hld` (max 3 revisions by default)
5. **Final Output**: `WriterFormatterAgent` generates formatted SDD with YAML frontmatter and Mermaid diagrams
6. **HITL Checkpoint**: Workflow pauses for human approval (currently auto-approves; full HITL requires LangGraph checkpoints)
7. **Output**: Final SDD saved to specified output path  
