"""Custom exceptions for ETL pipeline with context and error codes."""


class ETLException(Exception):
    """Base exception for all ETL errors."""
    
    def __init__(self, message: str, context: dict = None, error_code: str = None):
        """
        Initialize ETL exception.
        
        Args:
            message: Human-readable error message
            context: Optional context dictionary (e.g., {'source_path': '/path/to/file'})
            error_code: Optional error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.error_code = error_code
    
    def __str__(self) -> str:
        """String representation with context if available."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (Context: {context_str})"
        return self.message
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "exception_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
        }


class ExtractionError(ETLException):
    """Raised when extraction fails."""
    
    def __init__(self, message: str, source_path: str = None, **kwargs):
        """
        Initialize extraction error.
        
        Args:
            message: Error message
            source_path: Path/URL of the source that failed
            **kwargs: Additional context or error_code
        """
        context = kwargs.pop("context", {})
        if source_path:
            context["source_path"] = source_path
        super().__init__(message, context=context, **kwargs)
        self.source_path = source_path


class TransformationError(ETLException):
    """Raised when transformation fails."""
    
    def __init__(self, message: str, document_id: str = None, transformation_stage: str = None, **kwargs):
        """
        Initialize transformation error.
        
        Args:
            message: Error message
            document_id: ID of document that failed transformation
            transformation_stage: Stage that failed ('normalize', 'chunk', 'embed', 'enrich')
            **kwargs: Additional context or error_code
        """
        context = kwargs.pop("context", {})
        if document_id:
            context["document_id"] = document_id
        if transformation_stage:
            context["transformation_stage"] = transformation_stage
        super().__init__(message, context=context, **kwargs)
        self.document_id = document_id
        self.transformation_stage = transformation_stage


class EmbeddingError(ETLException):
    """Raised when embedding generation fails."""
    
    def __init__(self, message: str, chunk_id: str = None, model: str = None, **kwargs):
        """
        Initialize embedding error.
        
        Args:
            message: Error message
            chunk_id: ID of chunk that failed embedding
            model: Embedding model name that failed
            **kwargs: Additional context or error_code
        """
        context = kwargs.pop("context", {})
        if chunk_id:
            context["chunk_id"] = chunk_id
        if model:
            context["model"] = model
        super().__init__(message, context=context, **kwargs)
        self.chunk_id = chunk_id
        self.model = model


class LoadingError(ETLException):
    """Raised when loading fails."""
    
    def __init__(self, message: str, chunk_ids: list = None, target: str = None, **kwargs):
        """
        Initialize loading error.
        
        Args:
            message: Error message
            chunk_ids: List of chunk IDs that failed to load
            target: Target system (e.g., 'pgvector', 'audit_db')
            **kwargs: Additional context or error_code
        """
        context = kwargs.pop("context", {})
        if chunk_ids:
            context["chunk_ids"] = chunk_ids
            context["failed_count"] = len(chunk_ids)
        if target:
            context["target"] = target
        super().__init__(message, context=context, **kwargs)
        self.chunk_ids = chunk_ids
        self.target = target


class ConnectionError(ETLException):
    """Raised when connection fails."""
    
    def __init__(self, message: str, connection_string: str = None, target: str = None, **kwargs):
        """
        Initialize connection error.
        
        Args:
            message: Error message
            connection_string: Connection string (may be partially masked)
            target: Target system (e.g., 'pgvector', 's3')
            **kwargs: Additional context or error_code
        """
        context = kwargs.pop("context", {})
        if connection_string:
            # Mask password in connection string for security
            masked = self._mask_connection_string(connection_string)
            context["connection_string"] = masked
        if target:
            context["target"] = target
        super().__init__(message, context=context, **kwargs)
        self.connection_string = connection_string
        self.target = target
    
    @staticmethod
    def _mask_connection_string(conn_str: str) -> str:
        """Mask password in connection string."""
        # Simple masking: replace password=xxx with password=***
        import re
        return re.sub(r'(password=)([^@\s]+)', r'\1***', conn_str, flags=re.IGNORECASE)


class ConfigurationError(ETLException):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str, config_key: str = None, **kwargs):
        """
        Initialize configuration error.
        
        Args:
            message: Error message
            config_key: Key in config that is invalid
            **kwargs: Additional context or error_code
        """
        context = kwargs.pop("context", {})
        if config_key:
            context["config_key"] = config_key
        super().__init__(message, context=context, **kwargs)
        self.config_key = config_key


class ValidationError(ETLException):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: str = None, value: any = None, **kwargs):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            field: Name of field that failed validation
            value: Invalid value
            **kwargs: Additional context or error_code
        """
        context = kwargs.pop("context", {})
        if field:
            context["field"] = field
        if value is not None:
            context["invalid_value"] = str(value)
        super().__init__(message, context=context, **kwargs)
        self.field = field
        self.value = value