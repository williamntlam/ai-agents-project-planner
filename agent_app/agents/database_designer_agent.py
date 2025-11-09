"""Database Designer Agent - Database schema and security specifications."""

import os
from typing import Dict, Any, List, Tuple, Optional
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput
from agent_app.tools.mcp_tools import MCPTools
from agent_app.tools.rag_tool import RAGTool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class DatabaseDesignerAgent(BaseAgent):
    """Agent responsible for detailed database schema design and security specifications.
    
    This agent generates:
    - Complete database schema with CREATE TABLE statements
    - Entity-relationship diagrams (ERD) descriptions
    - Indexing strategies
    - Encryption specifications with industry-standard algorithms
    - Database security best practices
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
        temperature = self.get_config_value('temperature', 0.5)  # Lower for precise schemas
        max_tokens = self.get_config_value('max_tokens', 6000)  # Reduced to fit within 8192 token limit
        
        # Get API key from config or environment variable
        api_key = self.get_config_value('api_key') or os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in config or environment variables")
        
        self.logger.debug(
            "Initializing LLM for database design",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            has_api_key=bool(api_key)
        )
        
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key
        )
    
    def perform_action(self, state: DocumentState) -> AgentOutput:
        """
        Generate comprehensive database schema and security specifications.
        
        Uses:
        - MCP tools to query schema standards
        - RAG to retrieve database design patterns
        - LLM to generate detailed schema with encryption specs
        
        Args:
            state: Document state with hld_draft and lld_draft
            
        Returns:
            AgentOutput with database schema content
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
            schema_standards_text = "No schema standards retrieved. Use your knowledge of database design best practices."
        
        # 2. Retrieve database design patterns via RAG
        self.logger.info("Retrieving database design patterns via RAG", agent=self.name)
        query = f"Database schema design patterns, normalization, indexing strategies, encryption for: {state.hld_draft[:500] if state.hld_draft else state.project_brief}"
        
        db_context = self.rag_tool.retrieve_context(
            query=query,
            top_k=20,
            filters={}
        )
        
        formatted_db_context = self.rag_tool.format_context_for_prompt(db_context)
        
        # 3. Build database schema prompt
        prompt = self._build_database_schema_prompt(
            state.hld_draft,
            state.lld_draft,
            schema_standards_text,
            formatted_db_context,
            revision_context
        )
        
        # 4. Generate database schema using LLM
        self.logger.info("Generating database schema with LLM", agent=self.name)
        try:
            messages = [
                SystemMessage(content="""You are a senior database architect specializing in schema design, normalization, indexing, and database security.

Core Principles You Follow:
- Database normalization: Follow 3NF (Third Normal Form) as standard, denormalize only when justified
- Indexing strategy: Create indexes for foreign keys, frequently queried columns, and composite indexes for common query patterns
- Data integrity: Use constraints (PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK, NOT NULL) appropriately
- Security by design: Encrypt sensitive data, use parameterized queries, implement least privilege access
- Performance: Optimize for read and write patterns, consider partitioning for large tables
- Scalability: Design for horizontal and vertical scaling, consider sharding strategies

Encryption Standards:
- Data at Rest: Use AES-256-GCM (Advanced Encryption Standard with Galois/Counter Mode) for symmetric encryption
- Data in Transit: Use TLS 1.3 (Transport Layer Security) for all database connections
- Key Management: Use industry-standard key management (AWS KMS, Azure Key Vault, HashiCorp Vault)
- Password Hashing: Use bcrypt (cost factor 12+) or Argon2id for password storage
- Sensitive Fields: Encrypt PII, financial data, authentication tokens using AES-256-GCM
- Encryption Keys: Rotate keys every 90 days, use separate keys for different data types

Your Approach:
- Analyze the HLD and LLD to understand all entities and relationships
- Design normalized schemas with proper relationships
- Specify all constraints, indexes, and data types
- Include encryption specifications for sensitive data
- Provide ERD descriptions for diagram generation
- Justify design decisions (normalization level, indexing choices)
- Ensure schemas are production-ready and implementable"""),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            schema_content = response.content
            
            # Extract sources from context chunks
            sources = []
            for chunk in db_context:
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
                "Database schema generation completed",
                agent=self.name,
                content_length=len(schema_content),
                db_context_chunks=len(db_context),
                has_schema_standards=bool(schema_standards_text and "No schema standards" not in schema_standards_text),
                sources_count=len(sources)
            )
            
            return AgentOutput(
                content=schema_content,
                reasoning="Queried schema standards via MCP, retrieved database patterns via RAG, generated comprehensive schema with encryption specifications",
                sources=sources if sources else None,
                confidence=0.85 if len(db_context) >= 5 and schema_standards_text else 0.7,
                metadata={
                    "agent": self.name,
                    "db_context_chunks_used": len(db_context),
                    "schema_standards_used": bool(schema_standards_text and "No schema standards" not in schema_standards_text),
                    "revision_count": state.revision_count,
                    "has_revision_feedback": state.revision_count > 0
                }
            )
            
        except Exception as e:
            self.logger.error(
                "Database schema generation failed",
                agent=self.name,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise RuntimeError(f"Failed to generate database schema: {str(e)}") from e
    
    def _build_database_schema_prompt(
        self,
        hld_draft: str,
        lld_draft: str,
        schema_standards: str,
        db_context: str,
        revision_context: str = ""
    ) -> str:
        """
        Build prompt for database schema generation.
        
        Args:
            hld_draft: High-Level Design from SystemArchitectAgent
            lld_draft: Low-Level Design from APIDataAgent
            schema_standards: Formatted schema standards from MCP tools
            db_context: Formatted database design patterns from RAG
            revision_context: Optional revision feedback
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a senior database architect. Generate a comprehensive database schema design document based on the provided High-Level and Low-Level Designs.

High-Level Design:
{hld_draft[:3000] if hld_draft else "Not available"}

Low-Level Design:
{lld_draft[:3000] if lld_draft else "Not available"}
{revision_context}

Database Schema Standards and Best Practices:
{schema_standards if schema_standards else "No specific schema standards retrieved. Use your knowledge of database design best practices."}

Database Design Patterns and Guidelines:
{db_context if db_context else "No specific patterns retrieved. Use your knowledge of database design patterns."}

Generate a comprehensive database schema document including:

1. Entity-Relationship Diagram (ERD) Description
   - Detailed text description of all entities and relationships
   - Cardinality (one-to-one, one-to-many, many-to-many)
   - Relationship types and constraints
   - Format suitable for Mermaid ERD diagram generation

2. Complete Database Schema (CREATE TABLE Statements)
   For EACH table, provide:
   - Complete CREATE TABLE statement with all columns
   - Column definitions: name, data type, size, constraints (NOT NULL, UNIQUE, CHECK)
   - PRIMARY KEY definition
   - FOREIGN KEY constraints with ON DELETE/UPDATE actions
   - DEFAULT values where applicable
   - CHECK constraints for data validation
   - Example:
     ```sql
     CREATE TABLE todos (
         id SERIAL PRIMARY KEY,
         title VARCHAR(255) NOT NULL,
         description TEXT,
         user_id INTEGER NOT NULL,
         status VARCHAR(20) NOT NULL DEFAULT 'pending',
         created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
         updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
         due_date DATE,
         CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
         CONSTRAINT chk_status CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled'))
     );
     ```

3. Indexing Strategy
   For EACH index, provide:
   - Index name and type (B-tree, Hash, GIN, GiST, etc.)
   - Columns included in the index
   - Purpose and justification (e.g., "Index on user_id for fast lookups")
   - CREATE INDEX statements
   - Composite indexes for common query patterns
   - Example:
     ```sql
     CREATE INDEX idx_todos_user_id ON todos(user_id);
     CREATE INDEX idx_todos_status_created ON todos(status, created_at DESC);
     ```

4. Encryption and Security Specifications
   For EACH sensitive field/table, specify:
   - Field/table name
   - Encryption algorithm: AES-256-GCM (for data at rest)
   - Key management: Specify key management solution (AWS KMS, Azure Key Vault, etc.)
   - Encryption scope: Which fields are encrypted (e.g., "email, phone_number, ssn")
   - TLS configuration: TLS 1.3 for data in transit
   - Password hashing: bcrypt (cost factor 12+) or Argon2id
   - Key rotation policy: Rotate encryption keys every 90 days
   - Example:
     ```
     Table: users
     Encrypted Fields: email, phone_number, ssn
     Encryption Algorithm: AES-256-GCM
     Key Management: AWS KMS with automatic key rotation
     Password Hashing: bcrypt with cost factor 12
     TLS: TLS 1.3 for all database connections
     ```

5. Database Constraints and Business Rules
   - All CHECK constraints with business logic
   - UNIQUE constraints
   - NOT NULL constraints
   - Foreign key relationships
   - Triggers (if applicable) with descriptions
   - Stored procedures (if applicable) with descriptions

6. Data Types and Rationale
   - Justify data type choices (e.g., "VARCHAR(255) for titles, TEXT for descriptions")
   - Precision and scale for numeric types
   - Date/time type choices
   - JSON/JSONB usage if applicable

7. Normalization Approach
   - Normal form achieved (typically 3NF)
   - Justification for normalization level
   - Any intentional denormalization with rationale
   - Trade-offs considered

8. Performance Optimization
   - Partitioning strategy (if applicable)
   - Materialized views (if applicable)
   - Query optimization considerations
   - Connection pooling recommendations

9. Migration and Versioning
   - Schema versioning strategy
   - Migration approach (e.g., using Alembic, Flyway)
   - Backward compatibility considerations

Format as structured markdown with clear sections and subsections.
Be EXTREMELY specific - provide production-ready SQL that can be executed directly.
Include complete CREATE TABLE statements, indexes, constraints, and encryption specifications.
Aim for 2000-3000 words with substantial detail.
"""
        return prompt
    
    def get_required_tools(self) -> List[str]:
        """Return list of required tools."""
        return ['mcp_tools', 'rag_tool']
    
    def validate_state(self, state: DocumentState) -> Tuple[bool, List[str]]:
        """
        Validate state for DatabaseDesignerAgent.
        
        Requires:
        - project_brief (always required)
        - hld_draft (required - needs architecture context)
        - lld_draft (required - needs data model context)
        """
        is_valid, errors = super().validate_state(state)
        
        # DatabaseDesignerAgent requires both drafts
        if not state.hld_draft or len(state.hld_draft.strip()) < 100:
            errors.append("hld_draft is required and must be at least 100 characters")
            is_valid = False
        
        if not state.lld_draft or len(state.lld_draft.strip()) < 100:
            errors.append("lld_draft is required and must be at least 100 characters")
            is_valid = False
        
        return is_valid, errors

