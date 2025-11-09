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
        max_tokens = self.get_config_value('max_tokens', 4000)
        
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
        prompt = f"""You are a senior software architect. Generate a detailed Low-Level Design (LLD) document based on the provided High-Level Design.

High-Level Design:
{hld_draft}
{revision_context}

Database Schema Standards and Best Practices:
{schema_standards if schema_standards else "No specific schema standards retrieved. Use your knowledge of database design best practices."}

API Design Patterns and Data Modeling Guidelines:
{api_context if api_context else "No specific API patterns retrieved. Use your knowledge of RESTful API design and data modeling best practices."}

Generate a comprehensive LLD including:

1. API Endpoint Specifications
   - List all API endpoints with HTTP methods (GET, POST, PUT, DELETE, PATCH)
   - Request/response schemas (JSON examples)
   - Authentication and authorization requirements
   - Query parameters, path parameters, request bodies
   - Error response formats
   - Rate limiting and throttling considerations

2. Data Models
   - Entity-relationship diagrams (describe in text/markdown)
   - Database tables with columns, data types, constraints
   - Primary keys, foreign keys, indexes
   - Relationships between entities (one-to-one, one-to-many, many-to-many)
   - Data validation rules

3. Database Schema Design
   - Table definitions with detailed column specifications
   - Indexes for performance optimization
   - Constraints (NOT NULL, UNIQUE, CHECK, FOREIGN KEY)
   - Normalization approach (justify normalization level)
   - Data types chosen and rationale

4. API Request/Response Examples
   - Example requests for each endpoint
   - Example responses (success and error cases)
   - Status codes for different scenarios
   - Pagination, filtering, sorting examples

5. Data Validation Rules
   - Input validation requirements
   - Business rule validations
   - Data format constraints
   - Error messages for validation failures

6. Integration Points
   - External API integrations (if any)
   - Message queue schemas (if applicable)
   - Event payload structures (if applicable)
   - Third-party service contracts

Format as structured markdown with clear sections and subsections.
Be specific and detailed - this will be used for implementation.
Include concrete examples and schemas that developers can use directly.
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

