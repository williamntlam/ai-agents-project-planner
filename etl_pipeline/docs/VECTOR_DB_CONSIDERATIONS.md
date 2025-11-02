# Vector Database & Retrieval Considerations

## 🎯 Critical Considerations for Chunking, Retrieval, and Vector DB

---

## 1. Vector Database Indexing & Performance

### 1.1 Index Selection (pgvector)

**IVFFlat Index** (Default - Fast approximate search)
```sql
CREATE INDEX ON document_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- Adjust based on data size
```
- **When to use:** Large datasets (>100K vectors), fast approximate search
- **Trade-off:** Slight accuracy loss for speed
- **Lists parameter:** ~sqrt(total_vectors) for balanced performance

**HNSW Index** (Best quality, slower build)
```sql
CREATE INDEX ON document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```
- **When to use:** Need highest accuracy, smaller datasets
- **Trade-off:** Slower index building, better search quality

**Recommendation:** Start with IVFFlat, switch to HNSW if quality is insufficient.

### 1.2 Embedding Dimension Consistency

**Critical:** All embeddings MUST have the same dimension.

```python
# OpenAI text-embedding-3-small: 1536 dimensions
# OpenAI text-embedding-3-large: 3072 dimensions
# sentence-transformers models: 384, 768, etc.

# Store dimension in config
embedding_dimension: 1536  # Must match your model!

# Validate before insertion
assert len(embedding) == expected_dimension
```

### 1.3 Connection Pooling

**Add to requirements:**
```txt
psycopg2-pool>=2.0.0  # Connection pooling for better performance
```

**Usage:**
```python
from psycopg2 import pool

connection_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    dsn=connection_string
)
```

### 1.4 Batch Operations

**Always use batch inserts/upserts for performance:**
```python
# BAD: Individual inserts
for chunk in chunks:
    insert_chunk(chunk)  # Slow!

# GOOD: Batch insert
insert_chunks_batch(chunks, batch_size=100)  # 10-100x faster
```

---

## 2. Advanced Chunking Strategies

### 2.1 Chunk Size Optimization

**Key Principle:** Match chunk size to your use case and embedding model context.

| Use Case | Recommended Chunk Size | Reason |
|----------|----------------------|--------|
| Question answering | 256-512 tokens | Focused context |
| Document summarization | 1024-2048 tokens | Broader context |
| Code/documentation | 512-1024 tokens | Logical blocks |

**Token-based chunking:**
```python
import tiktoken

def chunk_by_tokens(text: str, max_tokens: int = 512) -> List[str]:
    encoding = tiktoken.encoding_for_model("text-embedding-3-small")
    tokens = encoding.encode(text)
    # Split into chunks of max_tokens
```

### 2.2 Document-Aware Chunking

**Different strategies for different content types:**

```python
# Markdown: Split by headers
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=[("#", "Header 1"), ("##", "Header 2")]
)

# Code: Split by functions/classes
code_splitter = LanguageTextSplitter(language="python")

# Prose: Semantic or recursive character splitting
prose_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ". ", " ", ""]
)
```

### 2.3 Overlap Strategy

**Why overlap matters:**
- Prevents information loss at chunk boundaries
- Maintains context across chunks
- Critical for retrieval quality

**Recommended overlap:**
- **Small chunks (256-512):** 10-15% overlap
- **Medium chunks (512-1024):** 15-20% overlap
- **Large chunks (1024+):** 20-25% overlap

**Smart overlap:** Overlap at sentence boundaries, not mid-sentence.

### 2.4 Chunk Deduplication

**Problem:** Same content chunked multiple times wastes storage/compute.

**Solution:**
```python
from utils.hashing import content_hash

seen_hashes = set()
for chunk in chunks:
    chunk_hash = content_hash(chunk.content)
    if chunk_hash not in seen_hashes:
        process_chunk(chunk)
        seen_hashes.add(chunk_hash)
```

---

## 3. Best Match 25 - Retrieval Optimization

### 3.1 Query Preprocessing

**Before embedding, enhance your query:**
```python
def preprocess_query(query: str) -> str:
    # Expand abbreviations
    # Add synonyms
    # Handle typos (optional)
    # Normalize formatting
    return normalized_query
```

### 3.2 Metadata Filtering

**Filter BEFORE similarity search for better performance:**

```sql
-- GOOD: Filter first, then search
SELECT * FROM document_chunks
WHERE metadata->>'document_type' = 'standards'
  AND metadata->>'category' = 'security'
ORDER BY embedding <=> %s::vector
LIMIT 25;

-- BAD: Search all, then filter (slow)
SELECT * FROM (
  SELECT * FROM document_chunks
  ORDER BY embedding <=> %s::vector
  LIMIT 1000
) WHERE metadata->>'document_type' = 'standards'
LIMIT 25;
```

### 3.3 Hybrid Search (Semantic + Keyword)

**Combine vector similarity with full-text search:**
```sql
-- Weighted hybrid search
SELECT 
  id,
  content,
  (1 - (embedding <=> %s::vector)) * 0.7 + 
  ts_rank_cd(to_tsvector('english', content), query) * 0.3 as combined_score
FROM document_chunks,
     to_tsquery('english', %s) query
ORDER BY combined_score DESC
LIMIT 25;
```

**Requires:** Full-text search index on content column.

### 3.4 Reranking (Optional but Powerful)

**Two-stage retrieval:**
1. Get top 100 with fast vector search
2. Rerank top 100 with more expensive cross-encoder

```python
# Stage 1: Fast approximate search (top 100)
candidates = vector_db.search(query_embedding, top_k=100)

# Stage 2: Rerank for quality (top 25)
reranked = cross_encoder_rerank(query, candidates)
final_results = reranked[:25]
```

**Add to requirements:**
```txt
# Optional: For reranking
sentence-transformers>=2.2.0  # Already have this
# OR use OpenAI's reranking API
```

### 3.5 Similarity Threshold

**Don't return low-quality matches:**
```python
def get_best_matches(query_embedding, top_k=25, min_similarity=0.7):
    results = vector_db.search(query_embedding, top_k=top_k * 2)
    # Filter by similarity threshold
    filtered = [r for r in results if r.similarity >= min_similarity]
    return filtered[:top_k]
```

### 3.6 Result Deduplication

**Avoid returning multiple chunks from same document:**
```python
def deduplicate_results(results, max_per_document=3):
    by_document = {}
    for result in results:
        doc_id = result.metadata['document_id']
        if doc_id not in by_document or len(by_document[doc_id]) < max_per_document:
            by_document.setdefault(doc_id, []).append(result)
    return [r for results in by_document.values() for r in results][:25]
```

### 3.7 Query Expansion

**Expand queries with related terms:**
```python
def expand_query(query: str) -> str:
    # Add synonyms, related concepts
    expanded = f"{query} OR {get_synonyms(query)}"
    return expanded
```

---

## 4. Production Considerations

### 4.1 Incremental Updates

**Only process new/changed files:**
```python
# Track processed files in audit table
def should_process(file_path: str) -> bool:
    last_processed = audit_loader.get_last_processed(file_path)
    file_modified = os.path.getmtime(file_path)
    return last_processed is None or file_modified > last_processed
```

**Benefits:**
- Faster runs
- Lower embedding costs
- Handle large datasets efficiently

### 4.2 Embedding Caching

**Cache embeddings to avoid recomputation:**
```python
# Hash chunk content → check cache → use cached embedding or generate new
def get_embedding(chunk: Chunk, cache: dict) -> List[float]:
    chunk_hash = content_hash(chunk.content)
    if chunk_hash in cache:
        return cache[chunk_hash]
    
    embedding = embedder.embed(chunk.content)
    cache[chunk_hash] = embedding
    return embedding
```

### 4.3 Cost Optimization (OpenAI Embeddings)

**Strategies to reduce API costs:**
- Cache embeddings (see above)
- Use batch API (cheaper per token)
- Incremental updates (only new content)
- Consider local models for development

### 4.4 Monitoring & Metrics

**Track important metrics:**
```python
# Pipeline metrics
- Documents processed
- Chunks created
- Embeddings generated (cost tracking)
- Insert/update operations
- Processing time per document
- Error rates

# Retrieval metrics (in agent_app)
- Query latency
- Results returned
- Average similarity scores
- Cache hit rates
```

### 4.5 Error Handling & Retries

**Use tenacity for retry logic:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def embed_with_retry(text: str):
    return embedder.embed(text)
```

### 4.6 Data Quality Checks

**Validate before insertion:**
```python
def validate_chunk(chunk: Chunk) -> bool:
    checks = [
        len(chunk.content) > 10,  # Not too short
        len(chunk.content) < 10000,  # Not too long
        len(chunk.embedding) == expected_dimension,  # Correct dimension
        chunk.metadata is not None,  # Has metadata
    ]
    return all(checks)
```

---

## 5. Recommended Database Schema

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Main chunks table
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id TEXT NOT NULL,  -- Reference to source document
    chunk_index INTEGER NOT NULL,  -- Position in document
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,  -- Match your model dimension!
    metadata JSONB NOT NULL DEFAULT '{}',
    content_hash TEXT,  -- For deduplication
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT unique_document_chunk UNIQUE(document_id, chunk_index)
);

-- Vector similarity index
CREATE INDEX ON document_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Metadata indexes (for filtering)
CREATE INDEX ON document_chunks USING GIN (metadata);

-- Full-text search index (for hybrid search)
CREATE INDEX ON document_chunks USING GIN (to_tsvector('english', content));

-- Audit table
CREATE TABLE etl_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_path TEXT NOT NULL,
    document_id TEXT,
    status TEXT NOT NULL,  -- 'success', 'failed', 'skipped'
    chunks_processed INTEGER DEFAULT 0,
    error_message TEXT,
    processed_at TIMESTAMP DEFAULT NOW(),
    processing_time_ms INTEGER
);

CREATE INDEX ON etl_audit_log(source_path);
CREATE INDEX ON etl_audit_log(processed_at);
```

---

## 6. Configuration Recommendations

**Add to your config YAML:**
```yaml
chunking:
  strategy: "recursive_character"  # or "semantic", "markdown"
  chunk_size: 1000
  chunk_overlap: 200
  use_tokens: true  # Token-based vs character-based
  respect_sentences: true

embedding:
  model: "text-embedding-3-small"
  dimension: 1536
  batch_size: 100
  cache_enabled: true

retrieval:
  top_k: 25
  min_similarity: 0.7
  use_reranking: false
  rerank_top_k: 100
  max_per_document: 3  # Deduplication
  use_hybrid_search: false

database:
  connection_pool_size: 20
  batch_size: 100
  index_type: "ivfflat"  # or "hnsw"
  ivfflat_lists: 100
```

---

## 7. Performance Benchmarks

**Target performance (for reference):**
- **Chunking:** ~1000 chunks/second
- **Embedding:** ~50-100 chunks/second (OpenAI API), ~500+ chunks/second (local)
- **Vector insert:** ~1000 chunks/second (batched)
- **Vector search (top 25):** <50ms with proper indexing

---

## Summary Checklist

- [ ] Choose appropriate index type (IVFFlat vs HNSW)
- [ ] Ensure embedding dimension consistency
- [ ] Implement connection pooling
- [ ] Use batch operations for inserts
- [ ] Configure chunk size based on use case
- [ ] Implement smart overlap strategy
- [ ] Add chunk deduplication
- [ ] Use metadata filtering in queries
- [ ] Consider hybrid search for better results
- [ ] Implement incremental updates
- [ ] Cache embeddings to reduce costs
- [ ] Add monitoring and metrics
- [ ] Validate data quality before insertion
- [ ] Set similarity thresholds
- [ ] Deduplicate retrieval results

