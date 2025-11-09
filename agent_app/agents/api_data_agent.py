"""API Data Agent - Low-Level Design generation."""

import os
from typing import Dict, Any, List, Tuple, Optional
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput
from agent_app.tools.mcp_tools import MCPTools
from agent_app.tools.rag_tool import RAGTool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class APIDataAgent(BaseAgent):
    """Agent responsible for low-level design: APIs, data models, schemas.
    
    This agent generates the Low-Level Design (LLD) based on the HLD from
    SystemArchitectAgent. It uses MCP tools to query schema standards and
    RAG to retrieve API design patterns.
    """
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
        self.mcp_tools: MCPTools = self._get_tool('mcp_tools')
        self.rag_tool: RAGTool = self._get_tool('rag_tool')
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        """
        Initialize LLM client for content generation.
        
        Returns:
            ChatOpenAI instance configured from config
        """
        model = self.get_config_value('model', 'gpt-4o-mini')
        temperature = self.get_config_value('temperature', 0.7)
        max_tokens = self.get_config_value('max_tokens', 8000)  # Increased for more detailed output
        
        # Get API key from config or environment variable
        api_key = self.get_config_value('api_key') or os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in config or environment variables")
        
        self.logger.debug(
            "Initializing LLM",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            has_api_key=bool(api_key)
        )
        
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key  # Now guaranteed to be a string
        )
    
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Generate low-level design based on HLD.
        
        Uses:
        - MCP tools to query schema standards
        - RAG to retrieve API design patterns
        - LLM to generate detailed LLD
        
        Args:
            state: Document state with hld_draft
            
        Returns:
            AgentOutput with LLD content
        """
        # Handle revision case
        revision_context = ""
        if state.revision_count > 0 and state.review_feedback:
            revision_context = f"\n\nRevision Feedback:\n{state.review_feedback}"
            self.logger.info(
                "Processing revision",
                revision_count=state.revision_count,
                agent=self.name
            )
        
        # 1. Query schema standards via MCP tools
        self.logger.info("Querying schema standards via MCP tools", agent=self.name)
        try:
            schema_standards = self.mcp_tools.query_schema_standards()
            schema_standards_text = self.mcp_tools.format_for_llm(schema_standards)
        except Exception as e:
            self.logger.warning(
                "Failed to query schema standards via MCP",
                error=str(e),
                agent=self.name
            )
            schema_standards_text = "No schema standards retrieved. Use your knowledge of best practices."
        
        # 2. Retrieve API design patterns via RAG
        self.logger.info("Retrieving API design patterns via RAG", agent=self.name)
        query = f"API design patterns and data modeling for: {state.hld_draft}"
        
        api_context = self.rag_tool.retrieve_context(
            query=query,
            top_k=20,
            filters={}  # RAG will use vector similarity to find relevant patterns
        )
        
        formatted_api_context = self.rag_tool.format_context_for_prompt(api_context)
        
        # 3. Build LLD prompt
        prompt = self._build_lld_prompt(
            state.hld_draft,
            schema_standards_text,
            formatted_api_context,
            revision_context
        )
        
        # 4. Generate LLD using LLM
        self.logger.info("Generating LLD with LLM", agent=self.name)
        try:
            messages = [
                SystemMessage(content="""You are a senior software architect specializing in API design, data modeling, and database schemas.

Core Principles You Follow:
- RESTful API design: Use proper HTTP methods, status codes, and resource-based URLs
- Data normalization: Follow database normalization principles (1NF, 2NF, 3NF) when appropriate
- API versioning: Plan for API evolution and backward compatibility
- Security by design: Authentication, authorization, input validation, and data protection
- Documentation: Clear API documentation with examples and error responses

Best Practices:
- Design clear, intuitive API endpoints with consistent naming conventions
- Use appropriate data types and constraints in database schemas
- Implement proper indexing strategies for performance
- Consider data relationships (one-to-one, one-to-many, many-to-many)
- Plan for data migration and schema evolution
- Design for scalability: pagination, filtering, sorting
- Error handling: Consistent error response formats
- API contracts: Define request/response schemas clearly

Your Approach:
- Analyze the High-Level Design thoroughly to understand system requirements
- Design APIs that align with the component architecture from HLD
- Create data models that support the business logic and use cases
- Justify design decisions (why this data structure, why this API pattern)
- Consider edge cases, error scenarios, and validation requirements
- Ensure designs are practical, implementable, and follow industry standards
- Reference schema standards and API design patterns when appropriate"""),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            lld_content = response.content
            
            # Extract sources from context chunks
            sources = []
            for chunk in api_context:
                source = chunk.get('metadata', {}).get('source') or chunk.get('metadata', {}).get('document_source')
                if source and source not in sources:
                    sources.append(source)
            
            # Add schema standards sources if available
            if schema_standards and 'standards' in schema_standards:
                for standard in schema_standards.get('standards', []):
                    if isinstance(standard, dict) and 'source' in standard:
                        source = standard['source']
                        if source and source not in sources:
                            sources.append(source)
            
            self.logger.info(
                "LLD generation completed",
                agent=self.name,
                content_length=len(lld_content),
                api_context_chunks=len(api_context),
                has_schema_standards=bool(schema_standards_text and "No schema standards" not in schema_standards_text),
                sources_count=len(sources)
            )
            
            return AgentOutput(
                content=lld_content,
                reasoning="Queried schema standards via MCP, retrieved API patterns via RAG, synthesized LLD based on HLD and retrieved context",
                sources=sources if sources else None,
                confidence=0.8 if len(api_context) >= 5 and schema_standards_text else 0.6,
                metadata={
                    "agent": self.name,
                    "api_context_chunks_used": len(api_context),
                    "schema_standards_used": bool(schema_standards_text and "No schema standards" not in schema_standards_text),
                    "revision_count": state.revision_count,
                    "has_revision_feedback": state.revision_count > 0
                }
            )
            
        except Exception as e:
            self.logger.error(
                "LLD generation failed",
                agent=self.name,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise RuntimeError(f"Failed to generate LLD: {str(e)}") from e
    
    def _build_lld_prompt(
        self, 
        hld_draft: str, 
        schema_standards: str, 
        api_context: str,
        revision_context: str = ""
    ) -> str:
        """
        Build prompt for LLD generation.
        
        Args:
            hld_draft: High-Level Design from SystemArchitectAgent
            schema_standards: Formatted schema standards from MCP tools
            api_context: Formatted API design patterns from RAG
            revision_context: Optional revision feedback
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a senior software architect. Generate a comprehensive and extremely detailed Low-Level Design (LLD) document based on the provided High-Level Design.

High-Level Design:
{hld_draft}
{revision_context}

Database Schema Standards and Best Practices:
{schema_standards if schema_standards else "No specific schema standards retrieved. Use your knowledge of database design best practices."}

API Design Patterns and Data Modeling Guidelines:
{api_context if api_context else "No specific API patterns retrieved. Use your knowledge of RESTful API design and data modeling best practices."}

Generate a comprehensive and DETAILED LLD with extensive depth:

1. Use Cases to API Mapping
   For each use case identified in the HLD, map it to specific API endpoints:
   - Use Case ID and Name
   - Primary API endpoints that support this use case
   - API sequence (step-by-step API calls to complete the use case)
   - Alternative API flows for different scenarios
   - Error handling APIs for failure cases
   - Create a clear traceability matrix showing: Use Case → API Endpoints → Business Value

2. API Endpoint Specifications (CONCRETE and DETAILED for each endpoint)
   Generate CONCRETE, PRODUCTION-READY API endpoints based on the use cases.
   For EACH endpoint, provide:
   - Full endpoint URL with path parameters (e.g., POST /api/v1/todos/{id}/complete)
   - HTTP method (GET, POST, PUT, DELETE, PATCH)
   - Use Case(s) supported (which use cases this API supports)
   - Detailed description and purpose (what business function it serves)
   - Authentication and authorization requirements (specific roles/permissions needed)
   - Path parameters (name, type, description, validation rules, examples)
   - Query parameters (name, type, description, default values, validation, examples)
   - Request body schema (complete JSON schema with all fields, types, constraints, examples)
   - Response schemas (200 success, 201 created, 400 bad request, 401 unauthorized, 404 not found, 422 validation error, 500 error)
   - Error response formats (detailed error codes, messages, error object structure)
   - Rate limiting and throttling (specific limits: e.g., 100 requests/minute per user)
   - Request/response headers (required and optional headers with examples)
   - Content-Type and Accept headers (application/json, etc.)
   - Pagination details (if applicable: page size, cursor-based vs offset-based, max page size)
   - Filtering and sorting options (available filters, sort fields, operators, examples)
   - API versioning strategy (how versions are handled)
   
   IMPORTANT: Generate ALL endpoints needed to support the use cases. Include:
   - CRUD operations for all main entities
   - Search and query endpoints
   - Bulk operations if needed
   - Status update endpoints
   - Any specialized endpoints for business workflows

3. Data Models (COMPREHENSIVE)
   - Entity-relationship diagrams (detailed text description for diagram generation)
   - Complete database tables with:
     * Column names, data types, sizes, precision
     * NOT NULL constraints
     * DEFAULT values
     * UNIQUE constraints
     * CHECK constraints
     * Column descriptions and business meaning
   - Primary keys (single or composite, rationale)
   - Foreign keys (referenced tables, ON DELETE/UPDATE actions)
   - Indexes (all indexes: primary, foreign key, unique, composite, covering indexes)
   - Relationships (detailed: one-to-one, one-to-many, many-to-many with cardinality)
   - Data validation rules (field-level and cross-field validations)
   - Enumerations (all enum types with allowed values)
   - Data constraints and business rules

4. Database Schema Design (DETAILED SQL-like definitions)
   - Complete table definitions (CREATE TABLE statements with all constraints)
   - Column specifications (data type, size, nullable, default, check constraints)
   - Indexes for performance (all indexes with columns, type, purpose)
   - Constraints (NOT NULL, UNIQUE, CHECK, FOREIGN KEY with full definitions)
   - Normalization approach (normal form achieved, justification, denormalization if any)
   - Data types chosen and rationale (why VARCHAR(255) vs TEXT, INT vs BIGINT, etc.)
   - Sequences or auto-increment strategies
   - Triggers (if applicable: what triggers, when, what they do)
   - Views (if applicable: view definitions and purposes)
   - Stored procedures (if applicable: procedures, functions, their purposes)

5. API Request/Response Examples (COMPLETE examples for each endpoint)
   For EACH endpoint, provide complete, copy-paste ready examples:
   - Example requests (complete curl commands with all headers, authentication tokens)
   - Example responses (success cases: 200, 201 with full JSON payloads)
   - Error response examples (400, 401, 404, 422, 500 with error details)
   - Status codes for all scenarios (all possible status codes per endpoint)
   - Pagination examples (first page, last page, empty results, with pagination metadata)
   - Filtering examples (single filter, multiple filters, complex queries with operators)
   - Sorting examples (single field, multiple fields, ascending/descending)
   - Request validation examples (valid requests, invalid requests with error details)
   - Use case flow examples (complete API call sequences for each use case)
   
   Format examples as:
   ```bash
   # Use Case: UC-001 - Create Todo Item
   curl -X POST https://api.example.com/api/v1/todos \\
     -H "Authorization: Bearer {token}" \\
     -H "Content-Type: application/json" \\
     -d '{{"title": "Buy groceries", "description": "Milk, eggs, bread", "due_date": "2024-01-15"}}'
   ```
   
   Include at least 2-3 examples per endpoint showing different scenarios.

6. Data Validation Rules (COMPREHENSIVE)
   - Input validation requirements (field-by-field validation rules)
   - Business rule validations (cross-field validations, business logic constraints)
   - Data format constraints (regex patterns, format requirements, examples)
   - Error messages for validation failures (specific error messages per validation rule)
   - Validation order and dependencies
   - Custom validation logic (complex validations that require business logic)
   - Sanitization requirements (input sanitization, SQL injection prevention, XSS prevention)

7. Integration Points (DETAILED)
   - External API integrations (complete API contracts, authentication, rate limits)
   - Message queue schemas (if applicable: queue names, message formats, routing keys)
   - Event payload structures (if applicable: event types, schemas, consumers)
   - Third-party service contracts (service names, endpoints, authentication, SLAs)
   - Webhook configurations (if applicable: endpoints, payloads, retry logic)
   - Integration patterns (synchronous, asynchronous, polling, webhooks)
   - Error handling for integrations (retry logic, circuit breakers, fallbacks)

8. Business Logic Details and Use Case Implementation
   - Use Case Implementation Details:
     * For each use case, describe how it's implemented via APIs
     * Step-by-step API call sequence for each use case flow
     * State changes that occur during use case execution
     * Data validation and business rules applied
   - Core business workflows (step-by-step workflows for key operations with API calls)
   - State machines (if applicable: states, transitions, triggers, API endpoints that trigger transitions)
   - Business rules (all business rules with conditions and actions, which APIs enforce them)
   - Calculation logic (formulas, algorithms, examples, which APIs perform calculations)
   - Workflow diagrams (text descriptions for diagram generation showing API interactions)
   - Use Case to API Traceability:
     * Matrix showing which APIs support which use cases
     * Coverage analysis (ensure all use cases have supporting APIs)
     * API dependencies for complex use cases

9. Error Handling and Edge Cases
   - Error scenarios (all possible error conditions)
   - Error handling strategy (how each error type is handled)
   - Edge cases (boundary conditions, unusual scenarios)
   - Failure modes (what happens when components fail)
   - Retry logic (when to retry, how many times, backoff strategy)

Format as structured markdown with clear sections and subsections.

CRITICAL REQUIREMENTS:
1. Generate CONCRETE, SPECIFIC API endpoints - not generic placeholders
   - Use actual endpoint paths like: POST /api/v1/todos, GET /api/v1/todos/{id}
   - Base URL: https://api.example.com (or derive from project brief)
   - API version: /api/v1/ (or appropriate versioning strategy)

2. Connect EVERY API to use cases:
   - Each API must specify which use case(s) it supports
   - Show complete API call sequences for each use case
   - Ensure all use cases from HLD have supporting APIs

3. Provide production-ready specifications:
   - Complete JSON schemas with all fields, types, constraints
   - Realistic example values (not just "string", "integer")
   - Complete curl commands that can be copy-pasted and tested
   - All possible status codes and error responses

4. Be EXTREMELY specific and detailed:
   - Include concrete, copy-paste ready examples that developers can use directly
   - Every endpoint should have complete documentation
   - Every table should have full schema definitions
   - Every use case should have a clear API implementation path

Aim for 4000-5000 words with substantial detail in each section.
The document should be comprehensive enough for developers to implement the system directly.
"""
        return prompt
    
    def get_required_tools(self) -> List[str]:
        """Return list of required tools."""
        return ['mcp_tools', 'rag_tool']
    
    def validate_state(self, state: DocumentState) -> Tuple[bool, List[str]]:
        """
        Validate state for APIDataAgent.
        
        Requires:
        - project_brief (always required)
        - hld_draft (required - depends on SystemArchitectAgent output)
        """
        is_valid, errors = super().validate_state(state)
        
        # APIDataAgent requires hld_draft
        if not state.hld_draft or len(state.hld_draft.strip()) < 100:
            errors.append("hld_draft is required and must be at least 100 characters")
            is_valid = False
        
        return is_valid, errors

