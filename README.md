# 🤖 Project: Autonomous System Design Document (SDD) Generator Agent

This document outlines the architecture and components of a powerful, self-correcting AI agent system designed to automate the creation of high-quality, standards-compliant System Design Documents (SDDs).

## 1. Project Goal and Core Architecture

The primary goal is to transform a simple project brief into a fully structured SDD by coordinating multiple specialized AI agents. The core architecture relies on Agentic Retrieval-Augmented Generation (RAG) and Model Context Protocol (MCP) principles, orchestrated by LangGraph.

### 1.1 Architectural Pillars

**Orchestration (LangGraph):** Manages the multi-step, cyclical workflow, including automated review and revision loops (Human-in-the-Loop).

**Modularity (Object-Oriented Agents):** Uses specialized, highly focused agents to handle distinct phases of the design process.

**Knowledge Base (RAG/ETL):** Grounds all generated content in a reliable Vector Database containing internal software engineering standards.

### 1.2 Repository Structure (Monorepo)

To balance maintainability and ease of setup, the project uses a monorepo structure with strict module boundaries:

```
/ai-sdd-generator
|-- /agent_app/                 # Real-time Logic & Orchestration (LangGraph)
|-- /etl_pipeline/              # Batch Data Ingestion (RAG Prep)
|-- /shared_core/               # Shared Config, Schemas, and Utilities (The Bridge)
|-- README.md
```

## 2. Agent Application (/agent_app)

This module houses the logic for reasoning, planning, and generation.

### 2.1 Object-Oriented Agent Design

All specialized agents inherit from a **BaseAgent** interface (Abstract Base Class) to ensure a uniform API (`perform_action`) for the Orchestrator. This implements the **Strategy Pattern** at the agent level.

| Agent Class | Responsibility | Key Reasoning Concept |
|--------------|----------------|------------------------|
| **SystemArchitectAgent** | High-Level Design (HLD), Component structure, Technology Rationale. | Uses ReAct (Thought → Action → Observation) to research patterns via the RAG tool. |
| **APIDataAgent** | Low-Level Design (LLD), Data Models, API Endpoints, Database Schemas. | Uses MCP Tool to interact with the database (querying schema standards). |
| **ReviewerAgent** | Quality Assurance, Validation, and Self-Correction loop initiation. | Uses JSON Schema validation and the Rubric to set the `needs_revision` flag in the LangGraph state. |
| **WriterFormatterAgent** | Final document assembly, Markdown formatting, and rendering Mermaid code blocks. | Ensures final output adheres to the document style guide retrieved via RAG. |

### 2.2 LangGraph Orchestration & Workflow

The workflow is a stateful graph that enforces a robust review and revision cycle.

| LangGraph Component | Concept | Role in SDD Generation |
|----------------------|----------|--------------------------|
| **State** | Shared DocumentState object (memory). | Holds the `project_brief`, `hld_draft`, `lld_draft`, and the structured `review_feedback`. |
| **Nodes** | Each specialized agent's `perform_action()` method. | Executes a single step (e.g., `draft_hld`, `assess_risks`, `review_doc`). |
| **Conditional Edge** | Decider function that routes the flow. | Checks the `needs_revision` flag (set by the Reviewer Agent) and loops or proceeds to END. |
| **Human-in-the-Loop (HITL)** | Final human gate before production. | Pauses the graph for human “APPROVE” or “REVISE” feedback. |

## 3. ETL Pipeline (/etl_pipeline)

This pipeline is crucial for maintaining the quality and relevance of the agent's knowledge. It is triggered independently of the real-time agent app (e.g., via a scheduled job).

### 3.1 ETL Stages

| Stage | Process | Output |
|--------|----------|---------|
| **E - Extract** | Loads raw standards documents (Markdown, Code, PDF) from source directories. | Raw, unprocessed text content. |
| **T - Transform** | 1. Chunking: Splits text into small, semantically coherent chunks. 2. Metadata Generation: Assigns filtering tags. 3. Embedding: Converts chunks into numerical vectors. | Indexed chunks, metadata, and vectors. |
| **L - Load** | Upserts the vectors and metadata into the Vector Database. | The live, searchable Vector Database index. |

### 3.2 Tooling and Standards

**RAG Tool:** The `retrieve_context` MCP-style function queries the Vector Database.

**Vector Database:** Used for Semantic Memory (Pinecone, Weaviate, or pg_vector).

**Standards Data:** Stores architectural patterns, approved technology lists, security rules, and style guides.

## 4. Document Structure & Output Format

The final SDD uses a highly structured, machine-readable format.

### 4.1 Document Format: Structured Markdown

The final output is a Markdown file using three layers:

1. **YAML Frontmatter (Metadata):** Used for validation by the ReviewerAgent.  
2. **Markdown Body:** The main content.  
3. **Mermaid Blocks:** Code blocks for generating diagrams.

### 4.2 JSON Schema (Validation)

The master JSON Schema defines the required structure and permissible values for the YAML Frontmatter (e.g., `status` must be `DRAFT`, `REVIEW`, or `FINAL`).

## 5. Getting Started

1. **Setup Environment:** Create a virtual environment and install dependencies.  
2. **Configure:** Set up API keys and database credentials in `shared_core/config.py`.  
3. **Ingest Data:** Run `python etl_pipeline/ingest_data.py` to build the Vector Database.  
4. **Run Agent:** Execute `python main_entrypoint.py --brief "E-commerce order processing microservice"`.  
