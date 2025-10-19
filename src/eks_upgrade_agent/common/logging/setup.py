"""
Logging setup and configuration for the EKS Upgrade Agent.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

import structlog
from structlog.types import FilteringBoundLogger

from .config import LoggerConfig
from .handlers import CloudWatchHandler
from .processors import add_context_processor, add_exception_processor


def setup_logging(config: Optional[LoggerConfig] = None) -> FilteringBoundLogger:
    """
    Set up structured logging for the EKS Upgrade Agent.
    
    Args:
        config: Logger configuration (uses defaults if None)
        
    Returns:
        Configured structlog logger
    """
    if config is None:
        config = LoggerConfig()
    
    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        add_context_processor,
        add_exception_processor,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Add appropriate formatter based on format preference
    if config.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.dev.ConsoleRenderer(colors=True)
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, config.log_level)
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # Remove default handlers
    
    # Add console handler if enabled
    if config.enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, config.log_level))
        root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if config.log_file:
        log_path = Path(config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            config.log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(getattr(logging, config.log_level))
        root_logger.addHandler(file_handler)
    
    # Add CloudWatch handler if enabled
    if config.enable_cloudwatch:
        cloudwatch_handler = CloudWatchHandler(
            log_group=config.cloudwatch_log_group,
            region=config.cloudwatch_region
        )
        cloudwatch_handler.setLevel(getattr(logging, config.log_level))
        root_logger.addHandler(cloudwatch_handler)
    
    # Create and return structlog logger
    logger = structlog.get_logger("eks_upgrade_agent")
    
    # Log initialization
    logger.info(
        "Logging system initialized",
        log_level=config.log_level,
        log_format=config.log_format,
        console_enabled=config.enable_console,
        file_enabled=config.log_file is not None,
        cloudwatch_enabled=config.enable_cloudwatch
    )
    
    return logger


def get_logger(name: Optional[str] = None) -> FilteringBoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (defaults to 'eks_upgrade_agent')
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name or "eks_upgrade_agent")


# Default logger instance for convenience
default_logger = None


def init_default_logger(config: Optional[LoggerConfig] = None) -> FilteringBoundLogger:
    """
    Initialize the default logger instance.
    
    Args:
        config: Logger configuration
        
    Returns:
        Configured logger instance
    """
    global default_logger
    default_logger = setup_logging(config)
    return default_logger


def get_default_logger() -> FilteringBoundLogger:
    """
    Get the default logger instance, initializing if necessary.
    
    Returns:
        Default logger instance
    """
    global default_logger
    if default_logger is None:
        default_logger = setup_logging()
    return default_logger