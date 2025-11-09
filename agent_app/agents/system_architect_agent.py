"""System Architect Agent - High-Level Design generation."""

import os
from typing import Dict, Any, List, Tuple, Optional
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput
from agent_app.tools.rag_tool import RAGTool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class SystemArchitectAgent(BaseAgent):
    """Agent responsible for high-level system architecture design.
    
    This agent generates the High-Level Design (HLD) based on the project brief.
    It uses the ReAct (Reasoning + Acting) pattern to research architectural
    patterns via RAG and synthesize a comprehensive HLD.
    """
    
    def __init__(self, config: Dict[str, Any], tools: Dict[str, Any] = None):
        super().__init__(config, tools)
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
        max_tokens = self.get_config_value('max_tokens', 6000)  # Reduced to fit within 8192 token limit
        
        # Get API key from config or environment variable
        api_key = self.get_config_value('api_key') or os.getenv('OPENAI_API_KEY')
        
        # Only pass api_key if it's a non-empty string
        # If None, ChatOpenAI will try to read from env, but we want to ensure it's a string
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
        Generate high-level design based on project brief.
        
        Uses ReAct pattern:
        1. Thought: Analyze requirements
        2. Action: Query RAG for relevant patterns
        3. Observation: Review retrieved context
        4. Thought: Synthesize architecture
        5. Action: Generate HLD
        
        Args:
            state: Document state with project_brief
            
        Returns:
            AgentOutput with HLD content
        """
        # Use combined brief to include all context
        full_brief = state.get_combined_brief()
        
        # Handle revision case
        revision_context = ""
        if state.revision_count > 0 and state.review_feedback:
            revision_context = f"\n\nRevision Feedback:\n{state.review_feedback}"
            self.logger.info(
                "Processing revision",
                revision_count=state.revision_count,
                agent=self.name
            )
        
        # 1. Retrieve relevant architectural patterns via RAG
        self.logger.info("Retrieving architectural patterns via RAG", agent=self.name)
        query = f"System architecture patterns for: {full_brief}"
        
        # Build filters for system design documents
        filters = {}
        # Try to filter by document_source path (what we know exists in metadata)
        # The RAG tool will use vector similarity, but we can add metadata filters
        # Note: filters work if metadata has these fields
        
        context = self.rag_tool.retrieve_context(
            query=query,
            top_k=25,
            filters=filters
        )
        
        # 2. Format context for prompt
        formatted_context = self.rag_tool.format_context_for_prompt(context)
        
        # 3. Build prompt
        prompt = self._build_hld_prompt(full_brief, formatted_context, revision_context)
        
        # 4. Generate HLD using LLM
        self.logger.info("Generating HLD with LLM", agent=self.name)
        try:
            messages = [
                SystemMessage(content="""You are a senior system architect with deep expertise in designing scalable, maintainable, and secure systems.

Core Principles You Follow:
- SOLID principles: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- DRY (Don't Repeat Yourself): Eliminate duplication, create reusable components
- KISS (Keep It Simple, Stupid): Prefer simple solutions over complex ones, avoid over-engineering
- YAGNI (You Aren't Gonna Need It): Don't implement functionality until necessary
- Composition over Inheritance: Favor object composition and interfaces over deep inheritance hierarchies

Architectural Best Practices:
- Design for scalability: Consider horizontal scaling, stateless services, and distributed systems patterns
- Ensure maintainability: Clear component boundaries, modular design, well-documented architecture
- Prioritize security: Authentication, authorization, data protection, and compliance from the start
- Plan for observability: Logging, monitoring, distributed tracing, and error handling
- Consider performance: Caching strategies, database optimization, and performance requirements

Your Approach:
- Analyze requirements thoroughly before proposing solutions
- Justify technology choices with clear rationale based on requirements
- Consider trade-offs (monolith vs microservices, SQL vs NoSQL, etc.)
- Design for future growth while avoiding premature optimization
- Ensure designs are practical, implementable, and aligned with industry best practices
- Reference and apply relevant architectural patterns (microservices, event-driven, etc.) when appropriate"""),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            hld_content = response.content
            
            # Extract sources from context chunks
            sources = []
            for chunk in context:
                source = chunk.get('metadata', {}).get('source') or chunk.get('metadata', {}).get('document_source')
                if source and source not in sources:
                    sources.append(source)
            
            self.logger.info(
                "HLD generation completed",
                agent=self.name,
                content_length=len(hld_content),
                context_chunks_used=len(context),
                sources_count=len(sources)
            )
            
            return AgentOutput(
                content=hld_content,
                reasoning="Researched architectural patterns via RAG, synthesized HLD based on retrieved context and project requirements",
                sources=sources if sources else None,
                confidence=0.8 if len(context) >= 5 else 0.6,  # Higher confidence with more context
                metadata={
                    "agent": self.name,
                    "context_chunks_used": len(context),
                    "revision_count": state.revision_count,
                    "has_revision_feedback": state.revision_count > 0
                }
            )
            
        except Exception as e:
            self.logger.error(
                "HLD generation failed",
                agent=self.name,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise RuntimeError(f"Failed to generate HLD: {str(e)}") from e
    
    def _build_hld_prompt(self, brief: str, context: str, revision_context: str = "") -> str:
        """
        Build prompt for HLD generation.
        
        Args:
            brief: Project brief with all context
            context: Formatted RAG context chunks
            revision_context: Optional revision feedback
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a senior system architect. Generate a comprehensive and detailed High-Level Design (HLD) document.

Project Brief:
{brief}
{revision_context}

Relevant Architectural Patterns and Standards:
{context if context else "No specific patterns retrieved. Use your knowledge of best practices."}

Generate a comprehensive and DETAILED HLD with extensive depth in each section:

1. System Overview
   - High-level description of the system (2-3 paragraphs with specific details)
   - Key business objectives (list 5-7 specific objectives with explanations)
   - Scope and boundaries (clearly define what's in scope and what's explicitly out of scope)
   - System context diagram description (describe interactions with external systems)
   - User personas (identify primary users: roles, responsibilities, goals)
   - Detailed Use Cases (for each major feature/functionality):
     * Use Case ID and Name
     * Actor (who performs the use case)
     * Preconditions (what must be true before the use case starts)
     * Main Flow (step-by-step description of the primary scenario)
     * Alternative Flows (other scenarios and variations)
     * Postconditions (what is true after the use case completes)
     * Business Rules (rules that apply to this use case)
     * Success Criteria (how success is measured for this use case)
   - Success criteria and KPIs (how will success be measured at system level?)

2. Component Architecture
   - Major components and their responsibilities (detailed description of each component, 3-5 sentences each)
   - Component interactions and dependencies (detailed interaction patterns, data flow between components)
   - Service boundaries (if applicable - clearly define microservice boundaries or module boundaries)
   - Component communication patterns (synchronous vs asynchronous, protocols used)
   - Interface contracts (high-level API contracts between components)
   - Deployment architecture (how components are deployed, containerization strategy)
   - Component diagrams (describe architecture in detail for diagram generation)

3. Technology Stack (with detailed rationale)
   - Programming languages and frameworks (specific versions, why chosen, alternatives considered)
     * Use Case Connections: How technology choice supports use cases (e.g., "Python chosen for UC-001 rapid development")
   - Databases and data storage (specific database choice, schema approach, replication strategy)
     * Use Case Connections: Database features used per use case (e.g., "UC-001 uses PostgreSQL JSONB for flexible schema")
   - Message queues/event streaming (if applicable - specific technologies, patterns, use cases)
     * Use Case Connections: Which use cases use message queues (e.g., "UC-003: Bulk operations use RabbitMQ")
   - Infrastructure and deployment tools (specific tools, CI/CD pipeline, container orchestration)
     * Use Case Connections: How infrastructure supports use case requirements
   - Monitoring and observability tools (logging, metrics, tracing solutions)
     * Use Case Connections: What's monitored per use case, tracing per use case flow
   - Security tools and libraries (authentication libraries, encryption tools)
     * Use Case Connections: Security libraries used per use case
   - Justify each choice with specific requirements and trade-offs considered
     * Connect each technology choice to use case requirements
   - Include version numbers and specific technology names where applicable

4. High-level Data Flow
   - Detailed data flow diagrams description (step-by-step flow for key operations)
   - How data moves through the system (request/response flows, data transformation points)
   - Layer Responsibilities (for each layer, specify what it does):
     * API Layer: Request validation, authentication, input sanitization, response formatting
     * Business Logic Layer: Business rule validation, state management, workflow orchestration, calculations
     * Data Access/Repository Layer: Database queries, data persistence, transaction management
   - Key data transformations (what transformations occur, where, and why)
   - Data storage locations (where different types of data are stored and why)
   - Data lifecycle (creation, updates, archival, deletion policies)
   - Data consistency patterns (eventual consistency, strong consistency, where applied, which use cases require each pattern)
   - Caching layers and strategies:
     * What's cached (specific data types, entities, query results)
     * Where caching is applied (which components, which APIs)
     * TTL strategies (time-to-live for different cache entries)
     * Cache invalidation strategies
     * Use Case Connections: For each caching strategy, specify:
       - Which use cases benefit from this caching (e.g., "UC-001: View Todo List benefits from caching frequently accessed todos")
       - Where in the use case flow caching is applied
       - Performance impact on use case execution (e.g., "Reduces response time from 200ms to 50ms for UC-001")
       - Cache hit/miss scenarios for each use case

5. Scalability and Performance Considerations
   - Expected load (specific numbers: requests per second, concurrent users, data volume)
     * Break down by use case: "UC-001 expected 1000 req/min, UC-002 expected 500 req/min"
   - Scaling strategy (horizontal vs vertical, auto-scaling rules, scaling triggers)
     * Use Case Connections: Which use cases drive scaling needs
     * Scaling triggers based on use case patterns (e.g., "Scale up during UC-003 bulk operations")
   - Performance requirements (specific SLAs: response times, throughput, availability targets)
     * Per-use-case SLAs: "UC-001 must respond in <200ms, UC-002 in <500ms"
   - Caching strategies (detailed caching approach: what, where, when, invalidation)
     * Use Case Connections: For EACH caching strategy, specify:
       - Which use cases use this cache (e.g., "UC-001: List Todos uses Redis cache for todo items")
       - Cache key strategy per use case
       - Cache invalidation triggers from use cases (e.g., "UC-004: Update Todo invalidates cache")
       - Expected cache hit rate per use case
       - Performance improvement per use case (e.g., "UC-001: 80% cache hit rate reduces DB load by 80%")
   - Database scaling approach (read replicas, sharding strategy, partitioning)
     * Use Case Connections: Which use cases use read replicas vs primary (e.g., "UC-001 uses read replica, UC-003 uses primary")
   - Load balancing strategy (algorithm, health checks, failover)
     * Use Case Connections: How load balancing affects each use case
   - Performance bottlenecks and mitigation (identify potential bottlenecks and solutions)
     * Per-use-case bottleneck analysis: "UC-002 may bottleneck on database writes, mitigated by..."
   - Capacity planning (resource requirements, growth projections)
     * Per-use-case capacity needs: "UC-001 requires X resources, UC-002 requires Y resources"

6. Security Considerations
   - Authentication and authorization approach (detailed auth flow, token management, session handling)
     * Use Case Connections: For each use case, specify:
       - Authentication requirements (e.g., "UC-001 requires JWT token, UC-002 requires OAuth")
       - Authorization checks (e.g., "UC-003: Update Todo requires user to own the todo")
       - Security flow in use case execution
   - Data protection and encryption (SPECIFIC industry-standard algorithms):
     * Data at Rest Encryption:
       - Algorithm: AES-256-GCM (Advanced Encryption Standard with Galois/Counter Mode)
       - Key Management: AWS KMS, Azure Key Vault, or HashiCorp Vault
       - Key Rotation: Every 90 days
     * Data in Transit Encryption:
       - Protocol: TLS 1.3 (Transport Layer Security version 1.3)
       - Cipher Suites: TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256
       - Certificate Management: Use valid SSL/TLS certificates from trusted CAs
     * Password Hashing:
       - Algorithm: bcrypt with cost factor 12+ or Argon2id
       - Salt: Automatically generated, unique per password
     * Use Case Connections: Which use cases handle sensitive data requiring encryption
     * Encryption applied per use case (e.g., "UC-004: Create Todo encrypts PII fields using AES-256-GCM")
   - API security (rate limiting, input validation, CORS, API keys)
     * Use Case Connections: Rate limits per use case (e.g., "UC-001: 100 req/min per user, UC-002: 50 req/min")
     * Input validation requirements per use case
   - Compliance requirements (GDPR, HIPAA, PCI-DSS if applicable)
     * Use Case Connections: Which use cases handle regulated data
     * Compliance measures per use case
   - Security monitoring and incident response (logging, alerting, response procedures)
     * Use Case Connections: Security events to monitor per use case
     * Alert triggers based on use case patterns
   - Access control model (RBAC, ABAC, or other - with detailed explanation)
     * Use Case Connections: Role requirements per use case (e.g., "UC-001: User role, UC-005: Admin role")
     * Permission matrix: Use Case → Required Permissions
   - Security best practices implementation (OWASP top 10 mitigation, secure coding practices)
     * Use Case Connections: Security measures applied per use case
     * Threat mitigation per use case (e.g., "UC-002: SQL injection prevention via parameterized queries")

7. Reliability and Fault Tolerance
   - Error handling strategy (how errors are handled, retry logic, circuit breakers)
     * Use Case Connections: Error handling per use case
     * Retry logic per use case (e.g., "UC-001: Retry 3 times with exponential backoff")
     * Circuit breaker triggers based on use case failure patterns
   - Disaster recovery (backup strategies, RTO/RPO targets, recovery procedures)
     * Use Case Connections: RTO/RPO requirements per use case (e.g., "UC-001: RTO 1 hour, UC-002: RTO 4 hours")
     * Recovery procedures per use case
   - High availability design (redundancy, failover mechanisms, health checks)
     * Use Case Connections: Availability requirements per use case (e.g., "UC-001: 99.9% uptime, UC-002: 99.5%")
     * Failover behavior per use case
   - Monitoring and alerting (what's monitored, alert thresholds, escalation procedures)
     * Use Case Connections: Metrics to monitor per use case
     * Alert thresholds per use case (e.g., "UC-001: Alert if response time > 500ms")
     * Use case health indicators

Format as structured markdown with clear sections and subsections.
Be EXTREMELY specific and detailed - provide concrete examples, specific technologies, and actionable details.
Each section should be comprehensive enough that a developer could understand the full system architecture.
Aim for 2000-3000 words total with substantial detail in each section.
"""
        return prompt
    
    def get_required_tools(self) -> List[str]:
        """Return list of required tools."""
        return ['rag_tool']
    
    def validate_state(self, state: DocumentState) -> Tuple[bool, List[str]]:
        """
        Validate state for SystemArchitectAgent.
        
        Requires:
        - project_brief (always required)
        - revision_feedback (if revision_count > 0)
        """
        is_valid, errors = super().validate_state(state)
        
        # Additional validation: if revising, need feedback
        if state.revision_count > 0 and not state.review_feedback:
            errors.append("revision_feedback is required when revision_count > 0")
            is_valid = False
        
        return is_valid, errors

