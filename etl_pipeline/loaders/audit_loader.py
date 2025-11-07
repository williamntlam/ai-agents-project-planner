"""Audit loader for tracking ETL pipeline processing history."""

import os
import json
import logging
import sqlite3
from typing import Optional
from datetime import datetime
from pathlib import Path

import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool, StaticPool

from loaders.base import BaseAuditLoader
from utils.exceptions import ConnectionError, ConfigurationError, LoadingError
from utils.retry import retry_connection

logger = logging.getLogger(__name__)


class AuditLoader(BaseAuditLoader):
    """
    Audit loader for tracking ETL pipeline processing history.
    
    Supports:
    - PostgreSQL (production)
    - SQLite (development)
    - JSONL (optional, for simple file-based logging)
    
    Features:
    - Log extraction, transformation, and loading events
    - Track timestamps and source paths
    - Support incremental updates (get_last_processed)
    - Handle failures and successes
    """
    
    def __init__(self, config: dict):
        """
        Initialize audit loader.
        
        Args:
            config: Configuration dictionary with keys:
                - type: "postgresql", "sqlite", or "jsonl"
                - connection_string: PostgreSQL connection string (for postgresql type)
                - db_path: SQLite database path (for sqlite type)
                - table_name: Table name for audit logs (default: "etl_audit_log")
                - log_file: JSONL file path (for jsonl type)
        """
        super().__init__(config)
        self.db_type = config.get("type", "postgresql").lower()
        self.connection_string = config.get("connection_string")
        self.db_path = config.get("db_path", "./logs/audit.db")
        self.table_name = config.get("table_name", "etl_audit_log")
        self.log_file = config.get("log_file", "./logs/audit.jsonl")
        
        # Database connections
        self.engine: Optional[Engine] = None
        self._connection = None  # Direct connection for SQLite/PostgreSQL
        
        # Validate configuration
        if self.db_type == "postgresql" and not self.connection_string:
            raise ConfigurationError(
                "connection_string is required for PostgreSQL",
                config_key="connection_string"
            )
        if self.db_type == "sqlite" and not self.db_path:
            raise ConfigurationError(
                "db_path is required for SQLite",
                config_key="db_path"
            )
        if self.db_type == "jsonl" and not self.log_file:
            raise ConfigurationError(
                "log_file is required for JSONL",
                config_key="log_file"
            )
    
    def validate_config(self) -> bool:
        """
        Validate configuration.
        
        Returns:
            bool: True if configuration is valid
        
        Raises:
            ConfigurationError: If configuration is invalid
        """
        valid_types = ["postgresql", "sqlite", "jsonl"]
        if self.db_type not in valid_types:
            raise ConfigurationError(
                f"type must be one of {valid_types}, got '{self.db_type}'",
                config_key="type"
            )
        
        if self.db_type == "postgresql" and not self.connection_string:
            raise ConfigurationError("connection_string is required for PostgreSQL")
        
        if self.db_type == "sqlite" and not self.db_path:
            raise ConfigurationError("db_path is required for SQLite")
        
        if self.db_type == "jsonl" and not self.log_file:
            raise ConfigurationError("log_file is required for JSONL")
        
        logger.info(f"Configuration validated: type={self.db_type}, table={self.table_name}")
        return True
    
    @retry_connection(max_attempts=5, wait_seconds=2.0)
    def connect(self) -> None:
        """
        Establish connection to database.
        
        Raises:
            ConnectionError: If connection fails
        """
        try:
            if self.db_type == "postgresql":
                self._connect_postgresql()
            elif self.db_type == "sqlite":
                self._connect_sqlite()
            elif self.db_type == "jsonl":
                self._connect_jsonl()
            else:
                raise ConfigurationError(f"Unsupported database type: {self.db_type}")
            
            # Create table if needed
            self._create_table_if_not_exists()
            
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to {self.db_type} database: {str(e)}",
                target=f"audit_{self.db_type}"
            ) from e
    
    def _connect_postgresql(self) -> None:
        """Connect to PostgreSQL database."""
        connection_string = self._expand_connection_string(self.connection_string)
        
        # Create SQLAlchemy engine with connection pooling
        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        
        # Test connection
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # Create direct psycopg2 connection
        self._connection = psycopg2.connect(connection_string)
        self._connection.autocommit = False
        
        logger.info("Connected to PostgreSQL audit database")
    
    def _connect_sqlite(self) -> None:
        """Connect to SQLite database."""
        # Ensure directory exists
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create SQLAlchemy engine for SQLite
        # Use StaticPool for SQLite (single connection)
        sqlite_url = f"sqlite:///{self.db_path}"
        self.engine = create_engine(
            sqlite_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            echo=False
        )
        
        # Test connection
        with self.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # Create direct sqlite3 connection
        self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row  # Enable dict-like access
        
        logger.info(f"Connected to SQLite audit database: {self.db_path}")
    
    def _connect_jsonl(self) -> None:
        """Setup JSONL file logging (no database connection needed)."""
        # Ensure directory exists
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"JSONL audit logging enabled: {self.log_file}")
    
    def disconnect(self) -> None:
        """Close database connections."""
        if self._connection:
            try:
                self._connection.close()
                logger.debug(f"Closed {self.db_type} connection")
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            finally:
                self._connection = None
        
        if self.engine:
            try:
                self.engine.dispose()
                logger.debug("Closed SQLAlchemy engine")
            except Exception as e:
                logger.warning(f"Error disposing engine: {e}")
            finally:
                self.engine = None
    
    def _create_table_if_not_exists(self) -> None:
        """Create audit log table if it doesn't exist."""
        if self.db_type == "jsonl":
            return  # No table needed for JSONL
        
        if not self._connection:
            raise ConnectionError("Not connected to database")
        
        try:
            if self.db_type == "postgresql":
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id SERIAL PRIMARY KEY,
                    event_type VARCHAR(50) NOT NULL,
                    source_path TEXT,
                    document_id TEXT,
                    status VARCHAR(20) NOT NULL,
                    chunks_created INTEGER,
                    chunks_loaded INTEGER,
                    error_message TEXT,
                    processed_at TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_source_path 
                ON {self.table_name}(source_path);
                
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_document_id 
                ON {self.table_name}(document_id);
                
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_processed_at 
                ON {self.table_name}(processed_at);
                """
                
                with self._connection.cursor() as cursor:
                    cursor.execute(create_table_sql)
                    self._connection.commit()
            
            elif self.db_type == "sqlite":
                create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    source_path TEXT,
                    document_id TEXT,
                    status TEXT NOT NULL,
                    chunks_created INTEGER,
                    chunks_loaded INTEGER,
                    error_message TEXT,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_source_path 
                ON {self.table_name}(source_path);
                
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_document_id 
                ON {self.table_name}(document_id);
                
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_processed_at 
                ON {self.table_name}(processed_at);
                """
                
                self._connection.execute(create_table_sql)
                self._connection.commit()
            
            logger.info(f"Audit table '{self.table_name}' created or already exists")
            
        except Exception as e:
            if self.db_type == "postgresql":
                self._connection.rollback()
            raise LoadingError(
                f"Failed to create audit table: {str(e)}",
                target=f"audit_{self.db_type}"
            ) from e
    
    def log_extraction(
        self,
        source_path: str,
        status: str,
        error: Optional[str] = None
    ) -> None:
        """
        Log document extraction event.
        
        Args:
            source_path: Path/URL of extracted document
            status: 'success', 'failed', 'skipped'
            error: Error message if status is 'failed'
        """
        if status not in ["success", "failed", "skipped"]:
            raise ValueError(f"Invalid status: {status}. Must be 'success', 'failed', or 'skipped'")
        
        event_data = {
            "event_type": "extraction",
            "source_path": source_path,
            "status": status,
            "error_message": error,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        self._log_event(event_data)
        logger.debug(f"Logged extraction: {source_path} - {status}")
    
    def log_transformation(
        self,
        document_id: str,
        chunks_created: int,
        status: str,
        error: Optional[str] = None
    ) -> None:
        """
        Log document transformation event.
        
        Args:
            document_id: ID of transformed document
            chunks_created: Number of chunks created
            status: 'success', 'failed'
            error: Error message if status is 'failed'
        """
        if status not in ["success", "failed"]:
            raise ValueError(f"Invalid status: {status}. Must be 'success' or 'failed'")
        
        event_data = {
            "event_type": "transformation",
            "document_id": document_id,
            "chunks_created": chunks_created,
            "status": status,
            "error_message": error,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        self._log_event(event_data)
        logger.debug(f"Logged transformation: {document_id} - {status} ({chunks_created} chunks)")
    
    def log_loading(
        self,
        chunks_loaded: int,
        status: str,
        error: Optional[str] = None
    ) -> None:
        """
        Log chunk loading event.
        
        Args:
            chunks_loaded: Number of chunks loaded
            status: 'success', 'failed'
            error: Error message if status is 'failed'
        """
        if status not in ["success", "failed"]:
            raise ValueError(f"Invalid status: {status}. Must be 'success' or 'failed'")
        
        event_data = {
            "event_type": "loading",
            "chunks_loaded": chunks_loaded,
            "status": status,
            "error_message": error,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        self._log_event(event_data)
        logger.debug(f"Logged loading: {chunks_loaded} chunks - {status}")
    
    def _log_event(self, event_data: dict) -> None:
        """Internal method to log event to database or file."""
        if self.db_type == "jsonl":
            self._log_to_jsonl(event_data)
        else:
            self._log_to_database(event_data)
    
    def _log_to_database(self, event_data: dict) -> None:
        """Log event to PostgreSQL or SQLite database."""
        if not self._connection:
            raise ConnectionError("Not connected to database. Call connect() first.")
        
        try:
            if self.db_type == "postgresql":
                insert_sql = f"""
                INSERT INTO {self.table_name} 
                    (event_type, source_path, document_id, status, chunks_created, chunks_loaded, error_message, processed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """
                
                with self._connection.cursor() as cursor:
                    cursor.execute(
                        insert_sql,
                        (
                            event_data.get("event_type"),
                            event_data.get("source_path"),
                            event_data.get("document_id"),
                            event_data.get("status"),
                            event_data.get("chunks_created"),
                            event_data.get("chunks_loaded"),
                            event_data.get("error_message"),
                            event_data.get("processed_at")
                        )
                    )
                    self._connection.commit()
            
            elif self.db_type == "sqlite":
                insert_sql = f"""
                INSERT INTO {self.table_name} 
                    (event_type, source_path, document_id, status, chunks_created, chunks_loaded, error_message, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """
                
                self._connection.execute(
                    insert_sql,
                    (
                        event_data.get("event_type"),
                        event_data.get("source_path"),
                        event_data.get("document_id"),
                        event_data.get("status"),
                        event_data.get("chunks_created"),
                        event_data.get("chunks_loaded"),
                        event_data.get("error_message"),
                        event_data.get("processed_at")
                    )
                )
                self._connection.commit()
        
        except Exception as e:
            if self.db_type == "postgresql":
                self._connection.rollback()
            logger.error(f"Failed to log event to database: {e}")
            raise LoadingError(
                f"Failed to log audit event: {str(e)}",
                target=f"audit_{self.db_type}"
            ) from e
    
    def _log_to_jsonl(self, event_data: dict) -> None:
        """Log event to JSONL file."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                json.dump(event_data, f, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to log event to JSONL: {e}")
            raise LoadingError(
                f"Failed to log audit event to JSONL: {str(e)}",
                target="audit_jsonl"
            ) from e
    
    def get_last_processed(self, source_path: str) -> Optional[str]:
        """
        Get last processed timestamp for a source path (for incremental updates).
        
        Args:
            source_path: Path to check
        
        Returns:
            Optional[str]: ISO timestamp string or None if never processed
        """
        if self.db_type == "jsonl":
            return self._get_last_processed_jsonl(source_path)
        else:
            return self._get_last_processed_database(source_path)
    
    def _get_last_processed_database(self, source_path: str) -> Optional[str]:
        """Get last processed timestamp from database."""
        if not self._connection:
            return None
        
        try:
            if self.db_type == "postgresql":
                query_sql = f"""
                SELECT MAX(processed_at) as last_processed
                FROM {self.table_name}
                WHERE source_path = %s AND status = 'success';
                """
                
                with self._connection.cursor() as cursor:
                    cursor.execute(query_sql, (source_path,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        return row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0])
                    return None
            
            elif self.db_type == "sqlite":
                query_sql = f"""
                SELECT MAX(processed_at) as last_processed
                FROM {self.table_name}
                WHERE source_path = ? AND status = 'success';
                """
                
                cursor = self._connection.execute(query_sql, (source_path,))
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0] if isinstance(row[0], str) else str(row[0])
                return None
        
        except Exception as e:
            logger.warning(f"Failed to get last processed timestamp: {e}")
            return None
    
    def _get_last_processed_jsonl(self, source_path: str) -> Optional[str]:
        """Get last processed timestamp from JSONL file."""
        if not os.path.exists(self.log_file):
            return None
        
        try:
            last_processed = None
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    if (event.get("source_path") == source_path and 
                        event.get("status") == "success" and
                        event.get("event_type") == "extraction"):
                        processed_at = event.get("processed_at")
                        if processed_at:
                            if not last_processed or processed_at > last_processed:
                                last_processed = processed_at
            
            return last_processed
        
        except Exception as e:
            logger.warning(f"Failed to get last processed timestamp from JSONL: {e}")
            return None
    
    def _expand_connection_string(self, conn_str: str) -> str:
        """Replace environment variables in connection string."""
        if not conn_str:
            return conn_str
        
        import re
        def replace_env(match):
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))
        
        return re.sub(r'\$\{(\w+)\}', replace_env, conn_str)
    
    def _mask_connection_string(self, conn_str: str) -> str:
        """Mask password in connection string for logging."""
        import re
        return re.sub(r'(password=)([^@\s]+)', r'\1***', conn_str, flags=re.IGNORECASE)
