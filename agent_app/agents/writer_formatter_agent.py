"""Writer Formatter Agent - Final document assembly and formatting."""

import os
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, UTC
import yaml
from agent_app.agents.base import BaseAgent
from agent_app.schemas.document_state import DocumentState
from agent_app.schemas.agent_output import AgentOutput
from agent_app.tools.rag_tool import RAGTool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class WriterFormatterAgent(BaseAgent):
    """Agent responsible for final document formatting and assembly.
    
    This agent combines the HLD and LLD into a final formatted SDD document.
    It retrieves the document style guide via RAG and ensures the output
    adheres to formatting standards.
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
        temperature = self.get_config_value('temperature', 0.5)
        max_tokens = self.get_config_value('max_tokens', 4000)  # Reduced to fit within 8192 token limit (leaves room for input)
        
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
        Assemble and format final SDD document.
        
        Steps:
        1. Retrieve document style guide via RAG
        2. Combine HLD and LLD
        3. Add YAML frontmatter
        4. Format markdown
        5. Generate Mermaid diagrams
        6. Apply style guide
        
        Args:
            state: Document state with hld_draft and lld_draft
            
        Returns:
            AgentOutput with final formatted SDD
        """
        # 1. Retrieve style guide via RAG
        self.logger.info("Retrieving document style guide via RAG", agent=self.name)
        style_guide = self.rag_tool.retrieve_context(
            query="document style guide formatting standards markdown",
            top_k=10,
            filters={}  # RAG will use vector similarity
        )
        
        formatted_style_guide = self.rag_tool.format_context_for_prompt(style_guide)
        
        # 2. Combine documents
        combined = self._combine_documents(state)
        
        # 3. Format with style guide using LLM
        self.logger.info("Formatting document with style guide", agent=self.name)
        formatted = self._format_document(combined, formatted_style_guide, state)
        
        # 4. Generate Mermaid diagrams
        self.logger.info("Generating Mermaid diagrams", agent=self.name)
        formatted = self._add_mermaid_diagrams(formatted, state)
        
        # Extract sources
        sources = []
        for chunk in style_guide:
            source = chunk.get('metadata', {}).get('source') or chunk.get('metadata', {}).get('document_source')
            if source and source not in sources:
                sources.append(source)
        
        self.logger.info(
            "Document formatting completed",
            agent=self.name,
            content_length=len(formatted),
            style_guide_chunks=len(style_guide)
        )
        
        return AgentOutput(
            content=formatted,
            reasoning="Retrieved style guide, formatted markdown with YAML frontmatter, added Mermaid diagrams",
            sources=sources if sources else None,
            confidence=0.9,
            metadata={
                "agent": self.name,
                "style_guide_chunks_used": len(style_guide),
                "has_yaml_frontmatter": formatted.startswith("---"),
                "has_mermaid_diagrams": "```mermaid" in formatted
            }
        )
    
    def _combine_documents(self, state: DocumentState) -> str:
        """
        Combine HLD, LLD, and Database Schema into a single document.
        
        Args:
            state: Document state with hld_draft, lld_draft, and database_schema
            
        Returns:
            Combined document string
        """
        parts = []
        
        if state.hld_draft:
            parts.append("# High-Level Design\n\n")
            parts.append(state.hld_draft)
            parts.append("\n\n")
        
        if state.lld_draft:
            parts.append("# Low-Level Design\n\n")
            parts.append(state.lld_draft)
            parts.append("\n\n")
        
        if state.database_schema:
            parts.append("# Database Schema Design\n\n")
            parts.append(state.database_schema)
        
        return "\n".join(parts)
    
    def _format_document(self, content: str, style_guide: str, state: DocumentState) -> str:
        """
        Format document according to style guide.
        
        Args:
            content: Combined HLD and LLD content
            style_guide: Formatted style guide from RAG
            state: Document state for metadata
            
        Returns:
            Formatted document with YAML frontmatter
        """
        try:
            # Build prompt for formatting
            # Use more content but still limit to avoid token issues
            content_to_format = content[:12000] if len(content) > 12000 else content
            
            prompt = f"""You are a technical writer specializing in system design documents. Format this document according to the style guide.

Style Guide:
{style_guide if style_guide else "Use standard markdown formatting with clear sections and subsections."}

Document Content:
{content_to_format}

Tasks:
1. Add YAML frontmatter at the beginning with:
   - title: System Design Document
   - status: FINAL
   - created_at: {datetime.now(UTC).isoformat()}
   - project_brief: (extract from content or use provided brief)
   - version: 1.0

2. Ensure proper markdown structure:
   - Clear heading hierarchy (H1, H2, H3)
   - Consistent formatting
   - Proper code blocks for technical content
   - Well-organized sections

3. Apply style guide rules:
   - Formatting conventions
   - Section organization
   - Code block formatting
   - List formatting

4. CRITICAL: Do NOT use placeholders like "..." or "[content here]" or "TBD". 
   - If a section has content, include ALL of it in full detail
   - If a section is missing content, either omit the section header entirely OR provide a brief note explaining what should be there
   - Never use "..." as a placeholder - it makes the document look incomplete

5. Ensure the document is ready for final use with complete, detailed content in all sections.

Return the complete formatted document with YAML frontmatter at the top.
Format: YAML frontmatter between --- markers, followed by the formatted markdown content.
"""
            
            messages = [
                SystemMessage(content="""You are an expert technical writer specializing in system design documents.
You format documents according to style guides, ensuring consistency, clarity, and proper structure.
You add appropriate YAML frontmatter and ensure markdown follows best practices.
IMPORTANT: Never use placeholders like "..." or "[TBD]" in the document. Include complete, detailed content in all sections, or omit incomplete sections entirely."""),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            formatted_doc = response.content.strip()
            
            # Ensure YAML frontmatter is present
            if not formatted_doc.startswith("---"):
                # Add YAML frontmatter if missing
                frontmatter = self._generate_yaml_frontmatter(state)
                formatted_doc = f"{frontmatter}\n\n{formatted_doc}"
            
            return formatted_doc
            
        except Exception as e:
            self.logger.error(
                "Document formatting failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            # Fallback: add basic YAML frontmatter and return content
            frontmatter = self._generate_yaml_frontmatter(state)
            return f"{frontmatter}\n\n{content}"
    
    def _generate_yaml_frontmatter(self, state: DocumentState) -> str:
        """
        Generate YAML frontmatter for the document.
        
        Args:
            state: Document state for metadata
            
        Returns:
            YAML frontmatter string
        """
        frontmatter_data = {
            "title": "System Design Document",
            "status": "FINAL",
            "created_at": datetime.now(UTC).isoformat(),
            "version": "1.0"
        }
        
        # Add project brief if available
        if state.project_brief:
            # Truncate if too long
            brief = state.project_brief[:200] + "..." if len(state.project_brief) > 200 else state.project_brief
            frontmatter_data["project_brief"] = brief
        
        # Add revision info if applicable
        if state.revision_count > 0:
            frontmatter_data["revision_count"] = state.revision_count
        
        try:
            yaml_str = yaml.dump(frontmatter_data, default_flow_style=False, sort_keys=False)
            return f"---\n{yaml_str}---"
        except Exception as e:
            self.logger.warning("Failed to generate YAML frontmatter", error=str(e))
            return "---\ntitle: System Design Document\nstatus: FINAL\n---"
    
    def _add_mermaid_diagrams(self, content: str, state: DocumentState) -> str:
        """
        Add Mermaid diagram code blocks to document.
        
        Args:
            content: Formatted document content
            state: Document state for context
            
        Returns:
            Document with Mermaid diagrams added
        """
        try:
            # Build prompt for Mermaid diagram generation
            prompt = f"""Generate Mermaid diagrams for this System Design Document.

Document Content:
{content[:5000]}  # Limited to avoid token limit issues

Generate appropriate Mermaid diagrams:
1. Architecture Diagram: Show component relationships and interactions
2. Data Flow Diagram: Show how data moves through the system
3. Database Schema Diagram (ERD): Show entity relationships using erDiagram syntax
   - Include all entities, relationships, and cardinality
   - Format: Use Mermaid erDiagram syntax with proper relationship notation

Insert the diagrams as code blocks with ```mermaid markers in appropriate sections.

For architecture, use graph TD or graph LR format.
For data flow, use flowchart format.
For database, use erDiagram format.

Return the document with Mermaid diagrams inserted in relevant sections.
Each diagram should be in its own code block with ```mermaid markers.
"""
            
            messages = [
                SystemMessage(content="""You are an expert at creating Mermaid diagrams for system design documents.
You generate clear, accurate diagrams that visualize architecture, data flow, and system structure.
You insert diagrams in appropriate sections using proper Mermaid syntax."""),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            content_with_diagrams = response.content.strip()
            
            # If diagrams weren't added, add them manually at appropriate sections
            if "```mermaid" not in content_with_diagrams:
                self.logger.warning("LLM did not add Mermaid diagrams, adding placeholder diagrams")
                # Add basic architecture diagram after HLD section
                if "# High-Level Design" in content_with_diagrams:
                    architecture_diagram = """
## Architecture Diagram

```mermaid
graph TD
    A[Client] --> B[API Gateway]
    B --> C[Service Layer]
    C --> D[Database]
    C --> E[Message Queue]
```
"""
                    # Insert after first major section
                    content_with_diagrams = content_with_diagrams.replace(
                        "# High-Level Design",
                        "# High-Level Design" + architecture_diagram,
                        1
                    )
            
            return content_with_diagrams
            
        except Exception as e:
            self.logger.error(
                "Mermaid diagram generation failed",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            # Return content without diagrams on error
            return content
    
    def get_required_tools(self) -> List[str]:
        """Return list of required tools."""
        return ['rag_tool']
    
    def validate_state(self, state: DocumentState) -> Tuple[bool, List[str]]:
        """
        Validate state for WriterFormatterAgent.
        
        Requires:
        - project_brief (always required)
        - hld_draft (required)
        - lld_draft (required)
        - database_schema (required)
        """
        is_valid, errors = super().validate_state(state)
        
        # WriterFormatterAgent requires all drafts
        if not state.hld_draft or len(state.hld_draft.strip()) < 100:
            errors.append("hld_draft is required and must be at least 100 characters")
            is_valid = False
        
        if not state.lld_draft or len(state.lld_draft.strip()) < 100:
            errors.append("lld_draft is required and must be at least 100 characters")
            is_valid = False
        
        if not state.database_schema or len(state.database_schema.strip()) < 100:
            errors.append("database_schema is required and must be at least 100 characters")
            is_valid = False
        
        return is_valid, errors

