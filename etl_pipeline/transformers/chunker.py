from typing import List, Dict

from etl_pipeline.transformers.base import BaseChunker
from etl_pipeline.models.document import Document
from etl_pipeline.models.chunk import Chunk
from etl_pipeline.utils.exceptions import TransformationError

# LangChain text splitters
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    RecursiveCharacterTextSplitter = None
    MarkdownHeaderTextSplitter = None


class Chunker(BaseChunker):
    """Chunker using LangChain's text splitters."""
    
    def __init__(self, config: Dict):
        super().__init__(config)
        
        # Extract configuration
        self.chunk_size = int(config.get("chunk_size", 1000))
        self.chunk_overlap = int(config.get("chunk_overlap", 200))
        self.strategy = str(config.get("strategy", "recursive_character"))
        self.separators = list(config.get("separators", ["\n\n", "\n", ". ", " ", ""]))
        
        # Validate configuration
        self.validate_config()
    
    def validate_config(self) -> bool:
        """Validate chunking configuration."""
        if not LANGCHAIN_AVAILABLE:
            raise ValueError(
                "LangChain text splitters are required. "
                "Install with: pip install langchain-text-splitters"
            )
        
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be >= 0")
        
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be < chunk_size")
        
        if self.strategy not in ["recursive_character", "markdown"]:
            raise ValueError(
                f"Unknown strategy: {self.strategy}. "
                "Supported strategies: 'recursive_character', 'markdown'"
            )
        
        return True
    
    def chunk(self, document: Document) -> List[Chunk]:
        """
        Chunk document using LangChain's text splitter.
        
        Args:
            document: Document to chunk
        
        Returns:
            List[Chunk]: Chunks ready for embedding
        """
        try:
            text = document.content or ""
            if not text.strip():
                return []
            
            # Route to appropriate chunking strategy
            if self.strategy == "markdown":
                chunk_texts = self._markdown_chunk(text)
            else:
                # Default to recursive character splitter
                chunk_texts = self._recursive_character_chunk(text)
            
            # Convert to Chunk objects
            chunks = []
            for idx, chunk_text in enumerate(chunk_texts):
                if not chunk_text.strip():
                    continue
                
                chunk = Chunk(
                    document_id=str(document.id),
                    chunk_index=idx,
                    content=chunk_text.strip(),
                    embedding=[],  # Will be filled by embedder
                    metadata={
                        "source": document.source,
                        "content_type": document.content_type,
                        "chunk_size": len(chunk_text),
                        "chunk_overlap": self.chunk_overlap,
                        "strategy": self.strategy,
                    }
                )
                chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            raise TransformationError(
                f"Chunking failed: {e}",
                document_id=str(document.id),
                transformation_stage="chunk"
            )
    
    def _recursive_character_chunk(self, text: str) -> List[str]:
        """
        Use LangChain's RecursiveCharacterTextSplitter.
        
        This splitter tries to split on separators in order:
        1. First tries to split on "\n\n" (paragraphs)
        2. Then "\n" (lines)
        3. Then ". " (sentences)
        4. Then " " (words)
        5. Finally character-by-character if needed
        
        This respects text structure and avoids splitting mid-sentence when possible.
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
        )
        return splitter.split_text(text)
    
    def _markdown_chunk(self, text: str) -> List[str]:
        """
        Use LangChain's MarkdownHeaderTextSplitter.
        
        Splits markdown by headers first, then recursively splits large sections.
        This preserves document structure (sections, subsections).
        """
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on
        )
        md_header_splits = splitter.split_text(text)
        
        # Further split if chunks are too large
        chunks = []
        recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
        )
        
        for split in md_header_splits:
            # Check if chunk is too large
            if len(split.page_content) > self.chunk_size:
                # Recursively split large chunks
                sub_chunks = recursive_splitter.split_text(split.page_content)
                chunks.extend(sub_chunks)
            else:
                chunks.append(split.page_content)
        
        return chunks
