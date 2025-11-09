"""System Architect Agent - High-Level Design generation."""

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
        max_tokens = self.get_config_value('max_tokens', 4000)
        
        # Get API key from config or environment
        api_key = self.get_config_value('api_key')
        
        self.logger.debug(
            "Initializing LLM",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key
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
        prompt = f"""You are a senior system architect. Generate a High-Level Design (HLD) document.

Project Brief:
{brief}
{revision_context}

Relevant Architectural Patterns and Standards:
{context if context else "No specific patterns retrieved. Use your knowledge of best practices."}

Generate a comprehensive HLD including:
1. System Overview
   - High-level description of the system
   - Key business objectives
   - Scope and boundaries

2. Component Architecture
   - Major components and their responsibilities
   - Component interactions and dependencies
   - Service boundaries (if applicable)

3. Technology Stack (with rationale)
   - Programming languages and frameworks
   - Databases and data storage
   - Message queues/event streaming (if applicable)
   - Infrastructure and deployment tools
   - Justify each choice based on requirements

4. High-level Data Flow
   - How data moves through the system
   - Key data transformations
   - Data storage locations

5. Scalability and Performance Considerations
   - Expected load and scaling strategy
   - Performance requirements
   - Caching strategies (if applicable)
   - Database scaling approach

6. Security Considerations
   - Authentication and authorization approach
   - Data protection and encryption
   - API security
   - Compliance requirements (if mentioned)

Format as structured markdown with clear sections and subsections.
Be specific and actionable - this will be used to generate detailed low-level design.
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

