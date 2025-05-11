import json
import logging
import os
import sys
from datetime import datetime, UTC
from typing import Any, Dict

from pythonjsonlogger.json import JsonFormatter

from utils.telemetry import get_current_trace_id

class CustomJsonFormatter(JsonFormatter):
    """Custom JSON formatter that adds additional fields and handles special cases."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.now(UTC).isoformat()
        
        # Add severity (Google Cloud Logging standard)
        log_record['severity'] = record.levelname
        
        # Add service context
        log_record['serviceContext'] = {
            'service': os.getenv('K_SERVICE', 'local'),
            'version': os.getenv('K_REVISION', 'dev')
        }
        
        # Add trace context if available
        trace_id = get_current_trace_id()
        if trace_id:
            log_record['logging.googleapis.com/trace'] = f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT')}/traces/{trace_id}"
        
        # Add source location
        log_record['logging.googleapis.com/sourceLocation'] = {
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName
        }

def setup_logging(name: str = None) -> logging.Logger:
    """Configure and return a logger with JSON formatting.
    
    Args:
        name: The name for the logger. If None, returns the root logger.
        
    Returns:
        A configured logger instance.
    """
    logger = logging.getLogger(name)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Create JSON formatter
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Set default level
    logger.setLevel(logging.INFO)
    
    return logger

def log_structured(logger: logging.Logger, level: int, message: str, **kwargs) -> None:
    """Log a message with structured data.
    
    Args:
        logger: The logger instance to use
        level: The logging level (e.g., logging.INFO)
        message: The message to log
        **kwargs: Additional fields to include in the log entry
    """
    extra = {
        'custom_fields': kwargs
    }
    logger.log(level, message, extra=extra)