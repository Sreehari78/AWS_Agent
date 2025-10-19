"""
Structlog processors for the EKS Upgrade Agent.
"""

import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict

import structlog
from structlog.types import FilteringBoundLogger

from ..handler import EKSUpgradeAgentError


def add_context_processor(logger: FilteringBoundLogger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add common context to all log messages.
    
    Args:
        logger: Bound logger instance
        method_name: Log method name
        event_dict: Event dictionary
        
    Returns:
        Enhanced event dictionary with context
    """
    # Add timestamp
    event_dict['timestamp'] = datetime.now(timezone.utc).isoformat()
    
    # Add log level
    event_dict['level'] = method_name.upper()
    
    # Add process info
    event_dict['process_id'] = os.getpid()
    
    # Add thread info if available
    event_dict['thread_name'] = threading.current_thread().name
    
    return event_dict


def add_exception_processor(logger: FilteringBoundLogger, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process exceptions for structured logging.
    
    Args:
        logger: Bound logger instance
        method_name: Log method name
        event_dict: Event dictionary
        
    Returns:
        Enhanced event dictionary with exception details
    """
    exc_info = event_dict.get('exc_info')
    if exc_info and exc_info[1]:
        exception = exc_info[1]
        
        # If it's our custom exception, use its structured data
        if isinstance(exception, EKSUpgradeAgentError):
            event_dict['exception'] = exception.to_dict()
        else:
            # For other exceptions, create basic structure
            event_dict['exception'] = {
                'type': type(exception).__name__,
                'message': str(exception),
                'traceback': structlog.processors.format_exc_info(logger, method_name, event_dict)
            }
        
        # Remove exc_info to avoid duplication
        event_dict.pop('exc_info', None)
    
    return event_dict