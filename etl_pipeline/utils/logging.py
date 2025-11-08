import logging
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime, UTC


def setup_logger(
    name: str = "etl_pipeline",
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up structured logger for ETL pipeline.
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file (if None, only console)
        format_string: Optional custom format string
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Prevent duplicate handlers if logger already configured
    if logger.handlers:
        return logger
    
    # Default format: timestamp, level, logger name, message
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    
    # Console handler (always)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def log_structured_data(logger: logging.Logger, level: str, message: str, **context):
    """
    Log structured data as JSON in the message.
    
    Args:
        logger: Logger instance
        message: Log message
        context: Additional context as keyword arguments
    """
    log_entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "message": message,
        **context
    }
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(json.dumps(log_entry))


def log_pipeline_stage(logger: logging.Logger, stage: str, action: str, **context):
    """
    Log a pipeline stage event with structured data.
    
    Args:
        logger: Logger instance
        stage: Pipeline stage ('extract', 'transform', 'load')
        action: Action description (e.g., 'started', 'completed', 'failed')
        context: Additional context
    """
    log_structured(
        logger,
        "info",
        f"Pipeline {stage} - {action}",
        stage=stage,
        action=action,
        **context
    )


def log_processed_document_event(logger: logging.Logger, document_id: str, source: str, status: str, **context):
    """
    Log document processing event.
    
    Args:
        logger: Logger instance
        document_id: Document identifier
        source: Source path/URL
        status: Processing status ('success', 'failed', 'skipped')
        context: Additional context (chunks_created, error_message, etc.)
    """
    log_structured(
        logger,
        "info" if status == "success" else "error",
        f"Document processed: {status}",
        document_id=document_id,
        source=source,
        status=status,
        **context
    )


def setup_logging(config: dict) -> logging.Logger:
    """
    Set up logging from configuration dictionary.
    
    Args:
        config: Logging configuration dictionary with keys:
            - level: Log level (DEBUG, INFO, WARNING, ERROR)
            - log_file: Path to log file (optional)
            - structured: Whether to use structured logging (optional)
    
    Returns:
        Configured logger instance
    """
    log_level = config.get('level', 'INFO')
    log_file = config.get('log_file')
    structured = config.get('structured', False)
    
    logger = setup_logger(
        name="etl_pipeline",
        log_level=log_level,
        log_file=log_file
    )
    
    return logger


# Default logger instance
default_logger = setup_logger()