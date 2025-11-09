"""Structured logging setup."""

import structlog
import logging
from typing import Dict, Any, Optional


def setup_logging(config: Optional[Dict[str, Any]] = None) -> structlog.BoundLogger:
    """
    Set up structured logging with configuration support.
    
    Args:
        config: Configuration dictionary with optional keys:
            - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: INFO
            - format: Output format ("json", "console", "pretty"). Default: "json"
            - timestamp_format: Timestamp format ("iso", "epoch", or custom). Default: "iso"
            - logger_name: Name for the logger. Default: None (uses module name)
            - processors: Custom list of processors (overrides default)
            - cache_logger: Whether to cache logger. Default: True
            - context_class: Context class for bound loggers. Default: dict
    
    Returns:
        Configured structlog logger instance
    """
    if config is None:
        config = {}
    
    # Extract configuration values with defaults
    log_level = config.get("level", config.get("log_level", "INFO"))
    output_format = config.get("format", "json")
    timestamp_format = config.get("timestamp_format", "iso")
    logger_name = config.get("logger_name")
    custom_processors = config.get("processors")
    cache_logger = config.get("cache_logger", True)
    context_class = config.get("context_class", dict)
    
    # Set up standard library logging level
    stdlib_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        level=stdlib_level,
    )
    
    # Build processors list
    if custom_processors:
        processors = custom_processors
    else:
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt=timestamp_format),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]
        
        # Add renderer based on format
        if output_format.lower() == "json":
            processors.append(structlog.processors.JSONRenderer())
        elif output_format.lower() == "console":
            processors.append(structlog.dev.ConsoleRenderer())
        elif output_format.lower() == "pretty":
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
        else:
            # Default to JSON if unknown format
            processors.append(structlog.processors.JSONRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=context_class,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=cache_logger,
    )
    
    # Return logger with optional name
    if logger_name:
        return structlog.get_logger(logger_name)
    return structlog.get_logger()

