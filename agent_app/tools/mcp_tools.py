"""MCP Tools - Model Context Protocol tools for structured data access."""

import os
import logging
import re
from typing import Dict, Any, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

from agent_app.utils.logging import setup_logging

logger = logging.getLogger(__name__)


class MCPTools:
    """MCP-style tools for structured data access."""
    
    def __init__(self, db_connection, config: Dict[str, Any]):
        """
        Initialize MCP tools.
        
        Args:
            db_connection: Database connection (can be connection string or connection object)
            config: Tool configuration
        """
        self.config = config
        self.logger = setup_logging()
        
        # Handle different connection types
        if isinstance(db_connection, str):
            # Connection string provided
            self.connection_string = self._expand_connection_string(db_connection)
            self._connection = None
            self.engine = None
        elif hasattr(db_connection, 'execute'):
            # SQLAlchemy engine provided
            self.engine = db_connection
            self._connection = None
            self.connection_string = None
        elif hasattr(db_connection, 'cursor'):
            # Direct psycopg2 connection provided
            self._connection = db_connection
            self.engine = None
            self.connection_string = None
        else:
            # Try to get connection string from config
            self.connection_string = self._expand_connection_string(
                config.get("db_connection_string", os.getenv("DATABASE_URL", ""))
            )
            self._connection = None
            self.engine = None
    
    def _expand_connection_string(self, conn_str: str) -> str:
        """Replace environment variables in connection string."""
        if not conn_str:
            return conn_str
        
        def replace_env(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))
        
        return re.sub(r'\$\{(\w+)\}', replace_env, conn_str)
    
    def _ensure_connection(self):
        """Ensure database connection is established."""
        if self._connection is None and self.engine is None:
            if not self.connection_string:
                raise ValueError("No database connection available")
            
            # Create SQLAlchemy engine
            self.engine = create_engine(
                self.connection_string,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            
            # Create direct psycopg2 connection for queries
            self._connection = psycopg2.connect(self.connection_string)
            self._connection.autocommit = False
    
    def query_schema_standards(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Query database schema standards from the vector database.
        
        This queries the document_chunks table for standards documents related to
        database schema design patterns, naming conventions, and best practices.
        
        Args:
            table_name: Optional specific table to query standards for
            
        Returns:
            Dictionary containing schema standards information:
            - standards: List of relevant standards chunks
            - patterns: Common schema patterns found
            - best_practices: Best practices extracted
        """
        try:
            self._ensure_connection()
            
            # Check if document_chunks table exists
            with self._connection.cursor() as check_cursor:
                check_cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'document_chunks'
                    );
                """)
                table_exists = check_cursor.fetchone()[0]
                
                if not table_exists:
                    self.logger.warning("document_chunks table does not exist")
                    return {
                        "standards": [],
                        "patterns": [],
                        "best_practices": [],
                        "count": 0
                    }
            
            # Build query to find schema standards in document_chunks
            # Filter by metadata indicating schema/standards documents
            # Note: Files in system_design/ and standards/ directories contain relevant content
            # The metadata enricher sets parent_directory based on file path
            query = """
                SELECT DISTINCT
                    document_id,
                    content,
                    metadata,
                    created_at
                FROM document_chunks
                WHERE (
                    -- Match by directory structure (using document_source path)
                    LOWER(metadata->>'document_source') LIKE '%/standards/%'
                    OR LOWER(metadata->>'document_source') LIKE '%/system_design/%'
                    OR LOWER(metadata->>'source') LIKE '%/standards/%'
                    OR LOWER(metadata->>'source') LIKE '%/system_design/%'
                    OR metadata->>'parent_directory' = 'standards'
                    OR metadata->>'parent_directory' = 'system_design'
                    OR LOWER(metadata->>'file_path') LIKE '%/standards/%'
                    OR LOWER(metadata->>'file_path') LIKE '%/system_design/%'
                    -- Match by category (from metadata enricher)
                    OR metadata->>'document_category' = 'database'
                    OR metadata->>'document_category' = 'schema'
                    OR metadata->>'category' = 'database'
                    OR metadata->>'category' = 'schema'
                    OR metadata->>'category' = 'architecture'
                    -- Match by filename patterns (from document_source or file_name)
                    OR LOWER(metadata->>'document_source') LIKE '%/database%'
                    OR LOWER(metadata->>'document_source') LIKE '%/schema%'
                    OR LOWER(metadata->>'document_source') LIKE '%/data-modeling%'
                    OR LOWER(metadata->>'document_source') LIKE '%/data_modeling%'
                    OR LOWER(metadata->>'file_name') LIKE '%database%'
                    OR LOWER(metadata->>'file_name') LIKE '%schema%'
                    OR LOWER(metadata->>'file_name') LIKE '%data-modeling%'
                    OR LOWER(metadata->>'file_name') LIKE '%data_modeling%'
                    -- Match by content keywords (from actual document content)
                    OR LOWER(content) LIKE '%schema design%'
                    OR LOWER(content) LIKE '%database design%'
                    OR LOWER(content) LIKE '%table design%'
                    OR LOWER(content) LIKE '%normalization%'
                    OR LOWER(content) LIKE '%normal form%'
                    OR LOWER(content) LIKE '%index%'
                    OR LOWER(content) LIKE '%primary key%'
                    OR LOWER(content) LIKE '%foreign key%'
                )
            """
            
            # Add table_name filter if provided
            if table_name:
                query += " AND (LOWER(content) LIKE %s OR metadata->>'table_name' = %s)"
                query += " ORDER BY created_at DESC LIMIT 50"
                params = [f"%{table_name.lower()}%", table_name]
            else:
                query += " ORDER BY created_at DESC LIMIT 50"
                params = None  # No parameters needed
            
            try:
                with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    rows = cursor.fetchall()
            except (IndexError, psycopg2.Error) as e:
                self.logger.error(
                    "Error executing schema standards query",
                    error=str(e),
                    error_type=type(e).__name__,
                    table_name=table_name
                )
                # Return empty result instead of crashing
                return {
                    "standards": [],
                    "patterns": [],
                    "best_practices": [],
                    "count": 0
                }
            
            # Format results for LLM consumption
            standards = []
            patterns = []
            best_practices = []
            
            for row in rows:
                content = row['content']
                metadata = row.get('metadata', {}) or {}
                
                # Get source from metadata (document_source is the actual field name)
                source = (
                    metadata.get('document_source') or 
                    metadata.get('file_path') or 
                    metadata.get('source') or 
                    'unknown'
                )
                
                # Get title from metadata
                title = (
                    metadata.get('document_title') or 
                    metadata.get('title') or 
                    metadata.get('file_stem') or 
                    None
                )
                
                # Categorize content
                content_lower = content.lower()
                if 'pattern' in content_lower or 'design pattern' in content_lower:
                    patterns.append({
                        'content': content[:500],  # Truncate for readability
                        'source': source,
                        'title': title,
                        'document_id': row['document_id'],
                        'category': metadata.get('document_category') or metadata.get('category')
                    })
                elif 'best practice' in content_lower or 'guideline' in content_lower:
                    best_practices.append({
                        'content': content[:500],
                        'source': source,
                        'title': title,
                        'document_id': row['document_id'],
                        'category': metadata.get('document_category') or metadata.get('category')
                    })
                else:
                    standards.append({
                        'content': content[:500],
                        'source': source,
                        'title': title,
                        'document_id': row['document_id'],
                        'category': metadata.get('document_category') or metadata.get('category')
                    })
            
            result = {
                'standards': standards[:10],  # Limit to top 10
                'patterns': patterns[:10],
                'best_practices': best_practices[:10],
                'total_found': len(rows)
            }
            
            self.logger.info(
                "Queried schema standards",
                table_name=table_name,
                total_found=len(rows),
                standards_count=len(result['standards']),
                patterns_count=len(result['patterns']),
                best_practices_count=len(result['best_practices'])
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Error querying schema standards",
                error=str(e),
                error_type=type(e).__name__,
                table_name=table_name,
                exc_info=True
            )
            return {
                'standards': [],
                'patterns': [],
                'best_practices': [],
                'total_found': 0,
                'error': str(e)
            }
    
    def get_technology_list(self, category: Optional[str] = None) -> List[str]:
        """
        Get approved technology list for a category from standards documents.
        
        Queries the vector database for technology standards and extracts
        approved technologies, optionally filtered by category.
        
        Args:
            category: Optional technology category filter (e.g., "database", 
                     "framework", "language", "tool", etc.)
            
        Returns:
            List of approved technology names
        """
        try:
            self._ensure_connection()
            
            # Build query to find technology standards
            # Note: Documents mention technologies in examples but don't have explicit "approved" lists
            # We'll search in standards and system_design directories and extract technologies from content
            query = """
                SELECT DISTINCT
                    content,
                    metadata,
                    created_at
                FROM document_chunks
                WHERE (
                    -- Match by directory structure (using document_source path)
                    LOWER(metadata->>'document_source') LIKE '%/standards/%'
                    OR LOWER(metadata->>'document_source') LIKE '%/system_design/%'
                    OR LOWER(metadata->>'source') LIKE '%/standards/%'
                    OR LOWER(metadata->>'source') LIKE '%/system_design/%'
                    OR metadata->>'parent_directory' = 'standards'
                    OR metadata->>'parent_directory' = 'system_design'
                    OR LOWER(metadata->>'file_path') LIKE '%/standards/%'
                    OR LOWER(metadata->>'file_path') LIKE '%/system_design/%'
                    -- Match by category
                    OR metadata->>'document_category' = 'technology'
                    OR metadata->>'category' = 'technology'
                    OR metadata->>'category' = 'architecture'
                    -- Match by content keywords (technologies mentioned in examples)
                    OR LOWER(content) LIKE '%postgresql%'
                    OR LOWER(content) LIKE '%mysql%'
                    OR LOWER(content) LIKE '%mongodb%'
                    OR LOWER(content) LIKE '%redis%'
                    OR LOWER(content) LIKE '%python%'
                    OR LOWER(content) LIKE '%javascript%'
                    OR LOWER(content) LIKE '%django%'
                    OR LOWER(content) LIKE '%flask%'
                    OR LOWER(content) LIKE '%react%'
                    OR LOWER(content) LIKE '%framework%'
                    OR LOWER(content) LIKE '%library%'
                    OR LOWER(content) LIKE '%database%'
                    OR LOWER(content) LIKE '%kafka%'
                    OR LOWER(content) LIKE '%docker%'
                    OR LOWER(content) LIKE '%kubernetes%'
                    OR LOWER(content) LIKE '%aws%'
                    OR LOWER(content) LIKE '%azure%'
                    OR LOWER(content) LIKE '%example%'
                    OR LOWER(content) LIKE '%use when%'
                )
            """
            
            params = []
            if category:
                query += """ AND (
                    LOWER(metadata->>'document_category') = %s 
                    OR LOWER(metadata->>'category') = %s 
                    OR LOWER(content) LIKE %s
                )"""
                params.extend([category.lower(), category.lower(), f"%{category.lower()}%"])
            
            query += " ORDER BY created_at DESC LIMIT 100"
            
            with self._connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
            
            # Extract technology names from content
            technologies = set()
            
            # Common technology patterns to extract
            tech_patterns = [
                r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:v?\d+\.?\d*|framework|library|tool|database|language)',
                r'\b(?:PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|Kafka|RabbitMQ|Docker|Kubernetes|AWS|Azure|GCP)\b',
                r'\b(?:Python|JavaScript|TypeScript|Java|Go|Rust|C\+\+|C#|Ruby|PHP|Swift|Kotlin)\b',
                r'\b(?:Django|Flask|FastAPI|Express|React|Vue|Angular|Spring|Laravel|Rails)\b',
                r'\b(?:Node\.js|npm|pip|Maven|Gradle|Docker|Kubernetes|Terraform|Ansible)\b',
            ]
            
            for row in rows:
                content = row['content']
                # Try to extract technology names
                for pattern in tech_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            tech = ' '.join(match).strip()
                        else:
                            tech = match.strip()
                        if tech and len(tech) < 50:  # Reasonable length
                            technologies.add(tech)
            
            # Also check metadata for technology tags
            # Check both document_tags (from document) and tags (from chunk)
            for row in rows:
                metadata = row.get('metadata', {}) or {}
                
                # Check document_tags (array from document metadata)
                if 'document_tags' in metadata:
                    doc_tags = metadata['document_tags']
                    if isinstance(doc_tags, list):
                        for tag in doc_tags:
                            if isinstance(tag, str) and len(tag) < 50:
                                technologies.add(tag)
                    elif isinstance(doc_tags, str):
                        technologies.add(doc_tags)
                
                # Check tags (chunk-level tags)
                if 'tags' in metadata:
                    tags = metadata['tags']
                    if isinstance(tags, list):
                        # Filter tags that look like technology names
                        for tag in tags:
                            if isinstance(tag, str) and len(tag) < 50:
                                technologies.add(tag)
                    elif isinstance(tags, str):
                        technologies.add(tags)
                
                # Check for technologies field (if explicitly set)
                if 'technologies' in metadata:
                    tech_list = metadata['technologies']
                    if isinstance(tech_list, list):
                        technologies.update(tech_list)
                    elif isinstance(tech_list, str):
                        technologies.add(tech_list)
            
            result = sorted(list(technologies))
            
            self.logger.info(
                "Retrieved technology list",
                category=category,
                technologies_found=len(result),
                total_chunks_searched=len(rows)
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Error retrieving technology list",
                error=str(e),
                error_type=type(e).__name__,
                category=category,
                exc_info=True
            )
            return []
    
    def format_for_llm(self, data: Dict[str, Any]) -> str:
        """
        Format structured data for LLM consumption.
        
        Args:
            data: Dictionary of data to format
            
        Returns:
            Formatted string suitable for LLM prompts
        """
        if not data:
            return "No data available."
        
        formatted_parts = []
        
        if 'standards' in data:
            formatted_parts.append("## Schema Standards:")
            for i, std in enumerate(data['standards'][:5], 1):
                title = std.get('title', '')
                title_str = f"**{title}** - " if title else ""
                formatted_parts.append(f"{i}. {title_str}{std.get('content', '')[:200]}...")
                formatted_parts.append(f"   Source: {std.get('source', 'unknown')}")
                if std.get('category'):
                    formatted_parts.append(f"   Category: {std.get('category')}")
        
        if 'patterns' in data:
            formatted_parts.append("\n## Design Patterns:")
            for i, pattern in enumerate(data['patterns'][:5], 1):
                title = pattern.get('title', '')
                title_str = f"**{title}** - " if title else ""
                formatted_parts.append(f"{i}. {title_str}{pattern.get('content', '')[:200]}...")
                formatted_parts.append(f"   Source: {pattern.get('source', 'unknown')}")
        
        if 'best_practices' in data:
            formatted_parts.append("\n## Best Practices:")
            for i, practice in enumerate(data['best_practices'][:5], 1):
                title = practice.get('title', '')
                title_str = f"**{title}** - " if title else ""
                formatted_parts.append(f"{i}. {title_str}{practice.get('content', '')[:200]}...")
                formatted_parts.append(f"   Source: {practice.get('source', 'unknown')}")
        
        if isinstance(data, list):
            formatted_parts.append("## Technologies:")
            for tech in data[:20]:
                formatted_parts.append(f"- {tech}")
        
        return "\n".join(formatted_parts) if formatted_parts else "No data to format."

