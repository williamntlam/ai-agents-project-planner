"""Vector database loader for pgvector - handles chunk storage and similarity search."""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, UTC

import psycopg2
from psycopg2.extras import execute_values, Json
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

from etl_pipeline.loaders.base import BaseVectorLoader
from etl_pipeline.models.chunk import Chunk
from etl_pipeline.utils.exceptions import LoadingError, ConnectionError, ConfigurationError, ValidationError
from etl_pipeline.utils.retry import retry_connection

logger = logging.getLogger(__name__)


class PgVectorLoader(BaseVectorLoader):
    """
    Loader for pgvector (PostgreSQL with vector extension).
    
    Features:
    - Creates pgvector extension and table if needed
    - Batch upserts with conflict resolution
    - Top-K similarity search (best match)
    - Connection pooling via SQLAlchemy
    """
    
    def __init__(self, config: dict):
        """
        Initialize pgvector loader.
        
        Args:
            config: Configuration dictionary with keys:
                - connection_string: PostgreSQL connection string
                - table_name: Name of the chunks table (default: "document_chunks")
                - batch_size: Batch size for upserts (default: 100)
                - upsert_mode: Whether to upsert (insert or update) (default: True)
                - create_index: Whether to create vector index (default: True)
                - index_type: "ivfflat" or "hnsw" (default: "ivfflat")
                - ivfflat_lists: Number of lists for IVFFlat index (default: 100)
                - embedding_dimension: Dimension of embedding vectors (required)
        """
        super().__init__(config)
        self.connection_string = config.get("connection_string")
        self.table_name = config.get("table_name", "document_chunks")
        self.batch_size = config.get("batch_size", 100)
        self.upsert_mode = config.get("upsert_mode", True)
        self.create_index = config.get("create_index", True)
        self.index_type = config.get("index_type", "ivfflat")
        self.ivfflat_lists = config.get("ivfflat_lists", 100)
        self.embedding_dimension = config.get("embedding_dimension")
        
        # SQLAlchemy engine (with connection pooling)
        self.engine: Optional[Engine] = None
        self._connection = None  # Direct psycopg2 connection for vector operations
        
        # Validate required fields
        if not self.connection_string:
            raise ConfigurationError(
                "connection_string is required",
                config_key="connection_string"
            )
        if not self.embedding_dimension:
            raise ConfigurationError(
                "embedding_dimension is required",
                config_key="embedding_dimension"
            )
    
    def validate_config(self) -> bool:
        """
        Validate configuration.
        
        Returns:
            bool: True if configuration is valid
        
        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not self.connection_string:
            raise ConfigurationError("connection_string is required")
        
        if not self.embedding_dimension or not isinstance(self.embedding_dimension, int):
            raise ConfigurationError(
                "embedding_dimension must be a positive integer",
                config_key="embedding_dimension"
            )
        
        if self.embedding_dimension <= 0:
            raise ConfigurationError(
                "embedding_dimension must be positive",
                config_key="embedding_dimension"
            )
        
        if self.index_type not in ["ivfflat", "hnsw"]:
            raise ConfigurationError(
                f"index_type must be 'ivfflat' or 'hnsw', got '{self.index_type}'",
                config_key="index_type"
            )
        
        if self.batch_size <= 0:
            raise ConfigurationError(
                "batch_size must be positive",
                config_key="batch_size"
            )
        
        logger.info(f"Configuration validated: table={self.table_name}, dimension={self.embedding_dimension}")
        return True
    
    @retry_connection(max_attempts=5, wait_seconds=2.0)
    def connect(self) -> None:
        """
        Establish connection to PostgreSQL database.
        Creates SQLAlchemy engine (with connection pooling) and direct psycopg2 connection.
        
        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Replace environment variables in connection string
            connection_string = self._expand_connection_string(self.connection_string)
            
            # Create SQLAlchemy engine with connection pooling
            # SQLAlchemy automatically handles pooling!
            self.engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=10,           # Number of connections to keep in pool
                max_overflow=20,        # Additional connections if pool is exhausted
                pool_pre_ping=True,      # Verify connections before use
                pool_recycle=3600,       # Recycle connections after 1 hour
                echo=False               # Set to True for SQL query logging
            )
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            # Create direct psycopg2 connection for vector operations
            # (pgvector operations sometimes need direct psycopg2)
            self._connection = psycopg2.connect(connection_string)
            self._connection.autocommit = False
            
            logger.info("Connected to PostgreSQL database")
            
            # Create extension and table if needed
            if self.create_index:
                self.create_index_if_not_exists()
            
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to PostgreSQL: {str(e)}",
                connection_string=self._mask_connection_string(connection_string),
                target="pgvector"
            ) from e
    
    def disconnect(self) -> None:
        """Close database connections."""
        if self._connection:
            try:
                self._connection.close()
                logger.debug("Closed direct psycopg2 connection")
            except Exception as e:
                logger.warning(f"Error closing direct connection: {e}")
            finally:
                self._connection = None
        
        if self.engine:
            try:
                self.engine.dispose()  # Closes all connections in pool
                logger.debug("Closed SQLAlchemy engine and connection pool")
            except Exception as e:
                logger.warning(f"Error disposing engine: {e}")
            finally:
                self.engine = None
    
    def create_index_if_not_exists(self) -> None:
        """
        Create pgvector extension and table if they don't exist.
        Also creates vector index for fast similarity search.
        """
        if not self._connection:
            raise ConnectionError("Not connected to database. Call connect() first.")
        
        try:
            with self._connection.cursor() as cursor:
                # Create pgvector extension
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                logger.info("pgvector extension created or already exists")
                
                # Create table if it doesn't exist
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id UUID PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector({self.embedding_dimension}) NOT NULL,
                    metadata JSONB DEFAULT '{{}}',
                    content_hash TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                """
                cursor.execute(create_table_sql)
                logger.info(f"Table '{self.table_name}' created or already exists")
                
                # Create indexes for faster lookups
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_document_id 
                    ON {self.table_name}(document_id);
                """)
                
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_content_hash 
                    ON {self.table_name}(content_hash) 
                    WHERE content_hash IS NOT NULL;
                """)
                
                # Create vector index for similarity search
                # Check if index already exists
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM pg_indexes 
                    WHERE tablename = '{self.table_name}' 
                    AND indexname LIKE '%_embedding%';
                """)
                index_exists = cursor.fetchone()[0] > 0
                
                if not index_exists:
                    if self.index_type == "ivfflat":
                        # IVFFlat index (faster to build, good for large datasets)
                        cursor.execute(f"""
                            CREATE INDEX idx_{self.table_name}_embedding_ivfflat 
                            ON {self.table_name} 
                            USING ivfflat (embedding vector_cosine_ops)
                            WITH (lists = {self.ivfflat_lists});
                        """)
                        logger.info(f"Created IVFFlat index with {self.ivfflat_lists} lists")
                    elif self.index_type == "hnsw":
                        # HNSW index (slower to build, but faster queries)
                        cursor.execute(f"""
                            CREATE INDEX idx_{self.table_name}_embedding_hnsw 
                            ON {self.table_name} 
                            USING hnsw (embedding vector_cosine_ops)
                            WITH (m = 16, ef_construction = 64);
                        """)
                        logger.info("Created HNSW index")
                else:
                    logger.info("Vector index already exists")
                
                self._connection.commit()
                logger.info("Database schema initialized successfully")
                
        except Exception as e:
            self._connection.rollback()
            raise LoadingError(
                f"Failed to create database schema: {str(e)}",
                target="pgvector"
            ) from e
    
    def load_chunks(self, chunks: List[Chunk]) -> None:
        """
        Load chunks into vector database.
        If upsert_mode is True, uses upsert_chunks. Otherwise, inserts only.
        
        Args:
            chunks: List of chunks to load (must have embeddings)
        
        Raises:
            LoadingError: If loading fails
            ValidationError: If chunks are invalid
        """
        if not chunks:
            logger.warning("No chunks to load")
            return
        
        # Validate chunks have embeddings
        for chunk in chunks:
            if not chunk.embedding:
                raise ValidationError(
                    f"Chunk {chunk.id} missing embedding",
                    field="embedding",
                    value=None
                )
            if len(chunk.embedding) != self.embedding_dimension:
                raise ValidationError(
                    f"Chunk {chunk.id} embedding dimension mismatch: "
                    f"expected {self.embedding_dimension}, got {len(chunk.embedding)}",
                    field="embedding",
                    value=len(chunk.embedding)
                )
        
        if self.upsert_mode:
            self.upsert_chunks(chunks)
        else:
            self._insert_chunks(chunks)
    
    def upsert_chunks(self, chunks: List[Chunk]) -> None:
        """
        Upsert chunks (insert or update if exists).
        Uses PostgreSQL's ON CONFLICT for efficient upserts.
        
        Args:
            chunks: List of chunks to upsert
        
        Raises:
            LoadingError: If upsert fails
        """
        if not chunks:
            return
        
        if not self._connection:
            raise ConnectionError("Not connected to database. Call connect() first.")
        
        # Process in batches
        total_loaded = 0
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            try:
                self._upsert_batch(batch)
                total_loaded += len(batch)
                logger.debug(f"Upserted batch: {len(batch)} chunks (total: {total_loaded}/{len(chunks)})")
            except Exception as e:
                raise LoadingError(
                    f"Failed to upsert batch starting at index {i}: {str(e)}",
                    chunk_ids=[chunk.id for chunk in batch],
                    target="pgvector"
                ) from e
        
        logger.info(f"Successfully upserted {total_loaded} chunks to {self.table_name}")
    
    def _upsert_batch(self, chunks: List[Chunk]) -> None:
        """Upsert a single batch of chunks."""
        if not self._connection:
            raise ConnectionError("Not connected to database")
        
        try:
            with self._connection.cursor() as cursor:
                # Prepare data for batch insert
                values = []
                for chunk in chunks:
                    values.append((
                        str(chunk.id),
                        chunk.document_id,
                        chunk.chunk_index,
                        chunk.content,
                        chunk.embedding,  # psycopg2 will convert list to vector
                        Json(chunk.metadata),  # Convert dict to JSONB
                        chunk.content_hash,
                        chunk.created_at,
                        datetime.now(UTC)  # updated_at
                    ))
                
                # Upsert using ON CONFLICT
                # If chunk with same id exists, update it
                upsert_sql = f"""
                INSERT INTO {self.table_name} 
                    (id, document_id, chunk_index, content, embedding, metadata, content_hash, created_at, updated_at)
                VALUES %s
                ON CONFLICT (id) 
                DO UPDATE SET
                    document_id = EXCLUDED.document_id,
                    chunk_index = EXCLUDED.chunk_index,
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    content_hash = EXCLUDED.content_hash,
                    updated_at = EXCLUDED.updated_at;
                """
                
                # Use execute_values for efficient batch insert
                execute_values(
                    cursor,
                    upsert_sql,
                    values,
                    template=None,
                    page_size=self.batch_size
                )
                
                self._connection.commit()
                
        except Exception as e:
            self._connection.rollback()
            raise LoadingError(
                f"Failed to upsert batch: {str(e)}",
                chunk_ids=[chunk.id for chunk in chunks],
                target="pgvector"
            ) from e
    
    def _insert_chunks(self, chunks: List[Chunk]) -> None:
        """Insert chunks without upsert (fails if duplicate)."""
        if not self._connection:
            raise ConnectionError("Not connected to database")
        
        # Process in batches
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            try:
                with self._connection.cursor() as cursor:
                    values = []
                    for chunk in batch:
                        values.append((
                            str(chunk.id),
                            chunk.document_id,
                            chunk.chunk_index,
                            chunk.content,
                            chunk.embedding,
                            Json(chunk.metadata),  # Convert dict to JSONB
                            chunk.content_hash,
                            chunk.created_at
                        ))
                    
                    insert_sql = f"""
                    INSERT INTO {self.table_name} 
                        (id, document_id, chunk_index, content, embedding, metadata, content_hash, created_at)
                    VALUES %s;
                    """
                    
                    execute_values(
                        cursor,
                        insert_sql,
                        values,
                        template=None,
                        page_size=self.batch_size
                    )
                    
                    self._connection.commit()
                    
            except psycopg2.IntegrityError as e:
                self._connection.rollback()
                raise LoadingError(
                    f"Duplicate chunk detected (use upsert_mode=True): {str(e)}",
                    chunk_ids=[chunk.id for chunk in batch],
                    target="pgvector"
                ) from e
            except Exception as e:
                self._connection.rollback()
                raise LoadingError(
                    f"Failed to insert batch: {str(e)}",
                    chunk_ids=[chunk.id for chunk in batch],
                    target="pgvector"
                ) from e
    
    def get_best_matches(
        self,
        query_embedding: List[float],
        top_k: int = 25,
        filters: Optional[dict] = None
    ) -> List[Chunk]:
        """
        Retrieve top-K most similar chunks using cosine similarity.
        
        Args:
            query_embedding: Query vector embedding (must match embedding_dimension)
            top_k: Number of results to return (default: 25)
            filters: Optional metadata filters (e.g., {"category": "security"})
        
        Returns:
            List[Chunk]: Top-K most similar chunks, sorted by similarity (highest first)
        
        Raises:
            ValidationError: If query_embedding dimension doesn't match
            LoadingError: If query fails
        """
        if not query_embedding:
            raise ValidationError("query_embedding cannot be empty", field="query_embedding")
        
        if len(query_embedding) != self.embedding_dimension:
            raise ValidationError(
                f"Query embedding dimension mismatch: "
                f"expected {self.embedding_dimension}, got {len(query_embedding)}",
                field="query_embedding",
                value=len(query_embedding)
            )
        
        if not self._connection:
            raise ConnectionError("Not connected to database. Call connect() first.")
        
        try:
            with self._connection.cursor() as cursor:
                # Build WHERE clause for filters
                where_clause = ""
                filter_params = []
                if filters:
                    filter_conditions = []
                    for key, value in filters.items():
                        filter_conditions.append(f"metadata->>'{key}' = %s")
                        filter_params.append(str(value))
                    if filter_conditions:
                        where_clause = "WHERE " + " AND ".join(filter_conditions)
                
                # Query using cosine similarity (1 - cosine_distance)
                # pgvector's <=> operator computes cosine distance
                # We use 1 - (embedding <=> query) to get cosine similarity
                query_sql = f"""
                SELECT 
                    id,
                    document_id,
                    chunk_index,
                    content,
                    embedding,
                    metadata,
                    content_hash,
                    created_at,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM {self.table_name}
                {where_clause}
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """
                
                # Execute query
                cursor.execute(
                    query_sql,
                    [query_embedding] + filter_params + [query_embedding, top_k]
                )
                
                rows = cursor.fetchall()
                
                # Convert rows to Chunk objects
                chunks = []
                for row in rows:
                    chunk_id, doc_id, chunk_idx, content, embedding, metadata, content_hash, created_at, similarity = row
                    
                    # Convert embedding from pgvector format to list
                    if isinstance(embedding, str):
                        # Parse vector string format: "[0.1, 0.2, ...]"
                        embedding = [float(x) for x in embedding.strip("[]").split(",")]
                    elif hasattr(embedding, '__iter__'):
                        embedding = list(embedding)
                    
                    chunk = Chunk(
                        id=UUID(chunk_id) if isinstance(chunk_id, str) else chunk_id,
                        document_id=doc_id,
                        chunk_index=chunk_idx,
                        content=content,
                        embedding=embedding,
                        metadata=metadata or {},
                        content_hash=content_hash,
                        created_at=created_at
                    )
                    chunks.append(chunk)
                
                logger.info(f"Retrieved {len(chunks)} best matches (top_k={top_k})")
                return chunks
                
        except Exception as e:
            raise LoadingError(
                f"Failed to retrieve best matches: {str(e)}",
                target="pgvector"
            ) from e
    
    def _expand_connection_string(self, conn_str: str) -> str:
        """Replace environment variables in connection string."""
        if not conn_str:
            return conn_str
        
        # Replace ${VAR_NAME} with environment variable value
        import re
        def replace_env(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))  # Return original if not found
        
        return re.sub(r'\$\{(\w+)\}', replace_env, conn_str)
    
    def _mask_connection_string(self, conn_str: str) -> str:
        """Mask password in connection string for logging."""
        import re
        return re.sub(r'(password=)([^@\s]+)', r'\1***', conn_str, flags=re.IGNORECASE)
