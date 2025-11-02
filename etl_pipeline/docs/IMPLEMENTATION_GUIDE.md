# ETL Pipeline Implementation Guide

## Overview
This guide outlines the step-by-step implementation order for the ETL pipeline. Start at Phase 1 and work sequentially.

---

## Phase 1: Foundation & Setup (Start Here)

### 1.1 Dependencies (`requirements.txt`)
Start by defining your dependencies. Here's a suggested starter:

```txt
# Core dependencies
pydantic>=2.0.0      # Data validation & models (Document, Chunk schemas)
pyyaml>=6.0.0        # Load YAML config files (base.yaml, local.yaml, prod.yaml)

# Database
psycopg2-binary>=2.9.0  # PostgreSQL adapter (connects Python to pgvector database)
pgvector>=0.3.0         # PostgreSQL extension client (stores & queries vectors)
sqlalchemy>=2.0.0       # ORM/database toolkit (optional, for cleaner DB code)

# Document processing
pypdf>=3.0.0           # Extract text from PDF files
markdown>=3.4.0        # Parse & process Markdown files (.md files)
python-docx>=1.0.0     # Extract text from Word documents (.docx files)

# Text processing & embeddings
langchain>=0.1.0           # Text splitting utilities, document loaders
langchain-community>=0.0.20  # Additional LangChain integrations
langchain-text-splitters>=0.0.1  # Advanced text splitters (semantic chunking, recursive)
sentence-transformers>=2.2.0  # Local embedding models (free, runs on CPU/GPU)
# OR openai>=1.0.0 (if using OpenAI embeddings)  # OpenAI API for embeddings (paid)

# Chunking & Retrieval
tiktoken>=0.5.0  # Token counting for precise chunk sizing
sentence-transformers[torch]>=2.2.0  # For semantic chunking (optional)
# For client-side similarity search (alternative to pgvector queries)
# faiss-cpu>=1.7.4  # OR faiss-gpu (if you have GPU support)

# Utilities
python-dotenv>=1.0.0  # Load .env file (database passwords, API keys)
tenacity>=8.2.0       # Retry decorators (automatic retries for API calls)

# CLI
click>=8.1.0  # Command-line interface framework (better than argparse)
```

### 1.2 Environment Setup
- Create `.env` file in project root with database credentials
- Start pgvector database: `docker-compose -f databases/docker-compose.pgvector.yml up -d`

---

## Phase 2: Data Models (Foundation)

### 2.1 Define Core Schemas
**Start with:** `models/document.py` and `models/chunk.py`

**Why first?** Everything else depends on these data structures.

#### `models/document.py`
```python
# RawDocument - extracted but not yet transformed
# Document - normalized document
```

#### `models/chunk.py`
```python
# Chunk - the final piece with embedding, metadata, etc.
```

**Key fields to include:**
- Document: `id`, `source`, `content`, `metadata`, `extracted_at`
- Chunk: `id`, `document_id`, `content`, `embedding`, `metadata`, `chunk_index`

---

## Phase 3: Base Classes & Interfaces

### 3.1 Base Classes
**Implement:** `extractors/base.py`, `transformers/base.py`, `loaders/base.py`

**Why?** These define the contracts that all implementations follow.

**Key methods:**
- `BaseExtractor.extract() -> Iterator[RawDocument]`
- `BaseTransformer.transform(document: RawDocument) -> Document`
- `BaseLoader.load(chunks: List[Chunk]) -> None`

---

## Phase 4: Utilities

### 4.1 Essential Utilities
**Implement:** `utils/logging.py`, `utils/hashing.py`, `utils/retry.py`

**Why?** Used throughout the pipeline for:
- Consistent logging
- Content hashing (deduplication)
- Retry logic for external API calls

**Quick wins:**
- `hashing.py`: Simple hash function for content deduplication
- `logging.py`: Structured logging setup
- `retry.py`: Decorator for retry logic

---

## Phase 5: Configuration

### 5.1 Config Files
**Set up:** `config/base.yaml`, `config/local.yaml`, `config/prod.yaml`

**Structure:**
```yaml
extractors:
  filesystem:
    base_path: "/data/standards"
    extensions: [".md", ".pdf", ".txt"]
  
transformers:
  chunker:
    chunk_size: 1000
    chunk_overlap: 200
  embedder:
    model: "sentence-transformers/all-MiniLM-L6-v2"
    batch_size: 32
  
loaders:
  vector_db:
    type: "pgvector"
    connection_string: "${DATABASE_URL}"
    table_name: "document_chunks"
```

---

## Phase 6: Extractors (E in ETL)

### 6.1 Start Simple: Filesystem Extractor
**Implement:** `extractors/filesystem_extractor.py`

**Features:**
- Walk directory tree
- Filter by extension (.md, .pdf, etc.)
- Read file contents
- Return `RawDocument` objects

### 6.2 Then: GitHub Extractor
**Implement:** `extractors/github_extractor.py`

**Features:**
- Use GitHub API or git clone
- Extract files from repos
- Handle rate limiting

### 6.3 Finally: S3 Extractor
**Implement:** `extractors/s3_extractor.py`

**Features:**
- List S3 objects
- Download files
- Handle pagination

---

## Phase 7: Transformers (T in ETL)

### 7.1 Normalizer
**Implement:** `transformers/normalizer.py`

**Purpose:** Convert raw files → normalized `Document`

**Features:**
- PDF text extraction
- Markdown parsing
- Code file handling
- Clean/extract metadata from filenames

### 7.2 Chunker
**Implement:** `transformers/chunker.py`

**Purpose:** Split documents into semantic chunks

**Features:**
- Text splitting with overlap (prevent information loss at boundaries)
- Respect paragraph/section boundaries (don't split mid-sentence)
- Handle code blocks intelligently (keep code blocks together)
- Token-aware chunking (using `tiktoken` for precise sizing)
- Semantic chunking (optional - group semantically similar sentences)

**Chunking Strategies:**

1. **Recursive Character Splitter** (LangChain)
   ```python
   from langchain_text_splitters import RecursiveCharacterTextSplitter
   # Respects text structure, good default
   ```

2. **Semantic Chunking** (Advanced)
   ```python
   # Groups sentences by semantic similarity
   # Better for preserving context
   ```

3. **Markdown Header Splitter** (LangChain)
   ```python
   from langchain_text_splitters import MarkdownHeaderTextSplitter
   # Splits by markdown headers - preserves document structure
   ```

4. **Token-based Chunking**
   ```python
   import tiktoken
   # Precise chunk sizing based on token count (important for embeddings)
   ```

**Best Practices:**
- Use overlap (10-20% of chunk size) to prevent context loss
- Match chunk size to embedding model's context window
- Consider document type: code vs prose need different strategies

### 7.3 Metadata Enricher
**Implement:** `transformers/metadata_enricher.py`

**Purpose:** Add tags, categories, timestamps

**Features:**
- Extract file type, source path
- Add processing timestamps
- Infer document category
- Add filtering tags

### 7.4 Embedder
**Implement:** `transformers/embedder.py`

**Purpose:** Generate vector embeddings for chunks

**Features:**
- Batch embedding generation
- Support multiple models (OpenAI, sentence-transformers)
- Handle rate limits
- Cache embeddings (optional)

---

## Phase 8: Loaders (L in ETL)

### 8.1 Vector Loader
**Implement:** `loaders/vector_loader.py`

**Purpose:** Upsert chunks + embeddings to pgvector

**Features:**
- Create pgvector extension if needed
- Create table with vector column
- Batch upserts with conflict resolution
- Handle duplicate detection

**SQL Setup:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE document_chunks (
  id UUID PRIMARY KEY,
  document_id TEXT,
  content TEXT,
  embedding vector(384),  -- match your embedding dimension
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops);
```

### 8.2 Audit Loader
**Implement:** `loaders/audit_loader.py`

**Purpose:** Track processing history

**Features:**
- Log what was processed
- Store timestamps, source paths
- Handle failures/successes
- Support SQLite (dev) or PostgreSQL (prod)

### 8.3 Retrieval Utilities (Best Match / Top-K Search)
**Create:** `utils/retrieval.py` or add to `loaders/vector_loader.py`

**Purpose:** Query pgvector to find top-K most similar chunks

**Features:**
- **Top-K Similarity Search** (e.g., "best match 25")
  - Query embedding against pgvector
  - Return top 25 most similar chunks by cosine similarity
  - Support different similarity metrics (cosine, L2, inner product)

**Example Implementation:**
```python
def get_best_matches(query_embedding: List[float], top_k: int = 25) -> List[Chunk]:
    """
    Find top-K most similar chunks using pgvector.
    
    Args:
        query_embedding: Vector representation of the query
        top_k: Number of results to return (default: 25)
    
    Returns:
        List of Chunk objects sorted by similarity (best match first)
    """
    query = """
        SELECT id, content, embedding, metadata
        FROM document_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """
    # Execute query and return results
```

**Advanced Features:**
- **Metadata Filtering**: Filter by document type, source, tags before similarity search
- **Hybrid Search**: Combine semantic similarity + keyword matching
- **Reranking**: Optional reranking of top results using cross-encoders
- **Query Expansion**: Expand query with related terms before embedding

**SQL Example for Best Match 25:**
```sql
-- pgvector similarity search (cosine similarity)
SELECT 
    id,
    content,
    metadata,
    1 - (embedding <=> %s::vector) as similarity_score
FROM document_chunks
WHERE metadata->>'document_type' = 'standards'  -- Optional filtering
ORDER BY embedding <=> %s::vector
LIMIT 25;
```

**Usage in Agent App:**
```python
# Query: "What are the security standards?"
query_embedding = embedder.embed("What are the security standards?")
best_matches = vector_loader.get_best_matches(query_embedding, top_k=25)
# Returns 25 most relevant chunks for RAG context
```

---

## Phase 9: Main Orchestrator

### 9.1 CLI Entrypoint
**Implement:** `main.py`

**Features:**
- Load config from YAML
- Instantiate extractors, transformers, loaders
- Run pipeline: Extract → Transform → Load
- Progress logging
- Error handling

**Flow:**
```python
1. Load config
2. Initialize extractor (filesystem/GitHub/S3)
3. Initialize transformers (normalizer, chunker, embedder, metadata_enricher)
4. Initialize loaders (vector_loader, audit_loader)
5. For each document:
   a. Extract → RawDocument
   b. Normalize → Document
   c. Chunk → List[Chunk]
   d. Enrich metadata
   e. Generate embeddings
   f. Load to vector DB
   g. Log to audit
6. Report summary
```

---

## Phase 10: Testing

### 10.1 Unit Tests
- Test each component in isolation
- Mock external dependencies

### 10.2 Integration Tests
- Test full pipeline with sample data
- Test error scenarios

---

## Quick Start Checklist

- [ ] Phase 1: Set up `requirements.txt` and `.env`
- [ ] Phase 2: Implement `models/document.py` and `models/chunk.py`
- [ ] Phase 3: Implement base classes
- [ ] Phase 4: Implement utility functions
- [ ] Phase 5: Set up config files
- [ ] Phase 6: Implement filesystem extractor (start simple!)
- [ ] Phase 7: Implement normalizer and chunker
- [ ] Phase 8: Implement embedder and vector loader
- [ ] Phase 9: Wire everything in `main.py`
- [ ] Phase 10: Test with sample data

---

## Pro Tips

1. **Start small:** Get filesystem extractor + normalizer working end-to-end first
2. **Test incrementally:** After each phase, test with sample data
3. **Log everything:** Helps debug issues in complex pipelines
4. **Handle errors gracefully:** Use retry utilities for external APIs
5. **Optimize later:** Get it working, then optimize batch sizes, parallelism, etc.

---

## Next Steps After Basic Implementation

- Add monitoring/metrics
- Implement incremental updates (only process changed files)
- Add content deduplication
- Optimize batch processing
- Add parallel processing for large datasets

