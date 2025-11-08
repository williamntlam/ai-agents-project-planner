from typing import Dict, List, Optional
from datetime import datetime, UTC
from pathlib import Path
import re

from etl_pipeline.transformers.base import BaseMetadataEnricher
from etl_pipeline.models.document import Document
from etl_pipeline.models.chunk import Chunk
from etl_pipeline.utils.exceptions import TransformationError

# Optional language detection
try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    detect = None
    LangDetectException = None


class MetadataEnricher(BaseMetadataEnricher):
    """Enriches documents and chunks with metadata."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        # Extract configuration
        self.extract_title = config.get("extract_title", True)
        self.extract_tags = config.get("extract_tags", True)
        self.extract_category = config.get("extract_category", True)
        self.auto_detect_language = config.get("auto_detect_language", True)
        self.enabled = config.get("enabled", True)
    
    def validate_config(self) -> bool:
        """Validate metadata enricher configuration."""
        # All config options are optional with defaults, so validation is simple
        return True
    
    def enrich(self, document: Document) -> Document:
        """
        Enrich document metadata with additional information.
        
        Args:
            document: Document to enrich
        
        Returns:
            Document: Document with enriched metadata
        """
        if not self.enabled:
            return document
        
        try:
            # Start with existing metadata
            enriched_metadata = dict(document.metadata or {})
            
            # Extract file information from source path
            enriched_metadata.update(self._extract_file_metadata(document.source))
            
            # Extract title from content
            if self.extract_title:
                title = self._extract_title(document.content, document.content_type)
                if title:
                    enriched_metadata["title"] = title
            
            # Extract tags
            if self.extract_tags:
                tags = self._extract_tags(document.content, document.source, enriched_metadata)
                if tags:
                    enriched_metadata["tags"] = tags
            
            # Infer category
            if self.extract_category:
                category = self._infer_category(document.source, document.content, enriched_metadata)
                if category:
                    enriched_metadata["category"] = category
            
            # Auto-detect language
            if self.auto_detect_language:
                language = self._detect_language(document.content)
                if language:
                    enriched_metadata["language"] = language
            
            # Add processing timestamp
            enriched_metadata["enriched_at"] = datetime.now(UTC).isoformat()
            
            # Create enriched document
            enriched_document = Document(
                id=document.id,
                source=document.source,
                content=document.content,
                content_type=document.content_type,
                metadata=enriched_metadata,
                extracted_at=document.extracted_at,
                normalized_at=document.normalized_at,
            )
            
            return enriched_document
            
        except Exception as e:
            raise TransformationError(
                f"Metadata enrichment failed: {e}",
                document_id=str(document.id),
                transformation_stage="enrich"
            )
    
    def enrich_chunk(self, chunk: Chunk, document: Document) -> Chunk:
        """
        Enrich chunk metadata with document context.
        
        Args:
            chunk: Chunk to enrich
            document: Source document for context
        
        Returns:
            Chunk: Chunk with enriched metadata
        """
        if not self.enabled:
            return chunk
        
        try:
            # Start with existing chunk metadata
            enriched_metadata = dict(chunk.metadata or {})
            
            # Add document-level metadata to chunk
            enriched_metadata.update({
                "document_source": document.source,
                "document_content_type": document.content_type,
                "document_title": document.metadata.get("title"),
                "document_category": document.metadata.get("category"),
                "document_tags": document.metadata.get("tags", []),
            })
            
            # Add chunk-specific metadata
            enriched_metadata.update({
                "chunk_position": f"{chunk.chunk_index + 1}/{self._estimate_total_chunks(document)}",
                "is_first_chunk": chunk.chunk_index == 0,
                "is_last_chunk": False,  # Will be updated if we know total chunks
            })
            
            # Add processing timestamp
            enriched_metadata["enriched_at"] = datetime.now(UTC).isoformat()
            
            # Create enriched chunk
            enriched_chunk = Chunk(
                id=chunk.id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=chunk.embedding,
                metadata=enriched_metadata,
                content_hash=chunk.content_hash,
                created_at=chunk.created_at,
            )
            
            return enriched_chunk
            
        except Exception as e:
            raise TransformationError(
                f"Chunk metadata enrichment failed: {e}",
                document_id=chunk.document_id,
                transformation_stage="enrich_chunk"
            )
    
    def _extract_file_metadata(self, source: str) -> Dict:
        """Extract metadata from file path."""
        metadata = {}
        
        try:
            path = Path(source)
            
            # Extract file information
            metadata["file_name"] = path.name
            metadata["file_stem"] = path.stem
            metadata["file_extension"] = path.suffix.lower()
            metadata["file_path"] = str(path)
            
            # Extract directory information
            if path.parent and path.parent.name:
                metadata["parent_directory"] = path.parent.name
                metadata["directory_path"] = str(path.parent)
            
            # Infer file type from extension
            file_type = self._infer_file_type(path.suffix)
            if file_type:
                metadata["file_type"] = file_type
            
        except Exception:
            # If path parsing fails, just use source as-is
            metadata["file_path"] = source
        
        return metadata
    
    def _extract_title(self, content: str, content_type: str) -> Optional[str]:
        """Extract title from document content."""
        if not content:
            return None
        
        # For markdown, extract first H1 header
        if content_type in ("markdown", "text/markdown"):
            match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        # For plain text, try first line (if it looks like a title)
        first_line = content.split('\n')[0].strip()
        if first_line and len(first_line) < 200 and not first_line.endswith('.'):
            return first_line
        
        return None
    
    def _extract_tags(self, content: str, source: str, metadata: Dict) -> List[str]:
        """Extract tags from content and source path."""
        tags = []
        
        # Extract tags from file path (directory names, keywords)
        path = Path(source)
        
        # Add directory names as potential tags
        for part in path.parts:
            if part and part not in ('.', '..', path.name):
                # Clean directory name
                clean_part = part.lower().replace('_', ' ').replace('-', ' ')
                if len(clean_part) > 2:  # Skip very short names
                    tags.append(clean_part)
        
        # Extract keywords from filename
        filename_lower = path.stem.lower()
        keywords = self._extract_keywords_from_filename(filename_lower)
        tags.extend(keywords)
        
        # Extract tags from content (look for common patterns)
        content_tags = self._extract_tags_from_content(content)
        tags.extend(content_tags)
        
        # Remove duplicates and normalize
        unique_tags = list(set([tag.lower().strip() for tag in tags if tag.strip()]))
        
        return unique_tags[:10]  # Limit to 10 tags
    
    def _extract_keywords_from_filename(self, filename: str) -> List[str]:
        """Extract keywords from filename."""
        keywords = []
        
        # Split by common separators
        parts = re.split(r'[_\-\s]+', filename)
        
        # Filter out common words and short parts
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        for part in parts:
            part = part.strip()
            if part and len(part) > 2 and part not in stop_words:
                keywords.append(part)
        
        return keywords
    
    def _extract_tags_from_content(self, content: str) -> List[str]:
        """Extract tags from document content."""
        tags = []
        
        # Look for markdown tags
        tag_pattern = re.compile(r'tags?:\s*\[(.*?)\]', re.IGNORECASE)
        match = tag_pattern.search(content)
        if match:
            tag_list = match.group(1)
            # Parse comma-separated tags
            for tag in tag_list.split(','):
                tag = tag.strip().strip('"\'')
                if tag:
                    tags.append(tag)
        
        # Look for YAML frontmatter tags
        yaml_tag_pattern = re.compile(r'^tags?:\s*(.+)$', re.MULTILINE | re.IGNORECASE)
        match = yaml_tag_pattern.search(content)
        if match:
            tag_value = match.group(1).strip()
            # Handle list or comma-separated
            if tag_value.startswith('['):
                # Parse list
                tag_list = tag_value.strip('[]')
                for tag in tag_list.split(','):
                    tag = tag.strip().strip('"\'')
                    if tag:
                        tags.append(tag)
            else:
                # Comma-separated
                for tag in tag_value.split(','):
                    tag = tag.strip().strip('"\'')
                    if tag:
                        tags.append(tag)
        
        return tags
    
    def _infer_category(self, source: str, content: str, metadata: Dict) -> Optional[str]:
        """Infer document category from source path and content."""
        # Check metadata first (might have been set earlier)
        if "category" in metadata:
            return metadata["category"]
        
        # Infer from file path
        path = Path(source)
        
        # Check parent directory names for common categories
        for part in path.parts:
            part_lower = part.lower()
            if part_lower in ["security", "api", "architecture", "standards", "guidelines", 
                            "docs", "documentation", "tests", "examples"]:
                return part_lower
        
        # Infer from filename
        filename_lower = path.stem.lower()
        if "security" in filename_lower:
            return "security"
        elif "api" in filename_lower:
            return "api"
        elif "architecture" in filename_lower:
            return "architecture"
        elif "standard" in filename_lower or "guideline" in filename_lower:
            return "standards"
        
        # Infer from content (look for headers or keywords)
        if content:
            content_lower = content.lower()[:500]  # Check first 500 chars
            if "security" in content_lower:
                return "security"
            elif "api" in content_lower or "endpoint" in content_lower:
                return "api"
            elif "architecture" in content_lower or "design" in content_lower:
                return "architecture"
        
        # Default category
        return "general"
    
    def _detect_language(self, content: str) -> Optional[str]:
        """Auto-detect document language."""
        if not content or len(content.strip()) < 10:
            return None
        
        if not LANGDETECT_AVAILABLE:
            return None
        
        try:
            # Use first 1000 characters for detection (faster)
            sample = content[:1000] if len(content) > 1000 else content
            language = detect(sample)
            return language
        except (LangDetectException, Exception):
            return None
    
    def _infer_file_type(self, extension: str) -> Optional[str]:
        """Infer file type from extension."""
        type_mapping = {
            ".md": "markdown",
            ".markdown": "markdown",
            ".txt": "text",
            ".py": "python",
            ".js": "javascript",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".xml": "xml",
            ".html": "html",
        }
        
        return type_mapping.get(extension.lower())
    
    def _estimate_total_chunks(self, document: Document) -> Optional[int]:
        """Estimate total number of chunks (if available in metadata)."""
        # This is a placeholder - in practice, you'd know this from the chunking step
        # For now, return None to indicate unknown
        return None
