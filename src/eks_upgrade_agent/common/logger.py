"""
Centralized logging configuration for the EKS Upgrade Agent.

This module provides structured logging with JSON output, AWS CloudWatch integration,
and proper error context preservation. It uses structlog for structured logging
and integrates with the custom exception hierarchy.
"""

import logging
import logging.handlers
import os
import sys
from typing import Any, Dict, Optional, Union
from datetime import datetime, timezone
from pathlib import Path

import structlog
from structlog.types import FilteringBoundLogger
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .exceptions import EKSUpgradeAgentError


class CloudWatchHandler(logging.Handler):
    """
    Custom logging handler for AWS CloudWatch Logs integration.
    
    Sends log messages to CloudWatch Logs with proper error handling
    and fallback to local logging when CloudWatch is unavailable.
    """
    
    def __init__(
        self,
        log_group: str,
        log_stream: Optional[str] = None,
        region: str = "us-east-1",
        create_log_group: bool = True
    ):
        """
        Initialize CloudWatch handler.
        
        Args:
            log_group: CloudWatch log group name
            log_stream: CloudWatch log stream name (defaults to hostname-timestamp)
            region: AWS region for CloudWatch
            create_log_group: Whether to create log group if it doesn't exist
        """
        super().__init__()
        self.log_group = log_group
        self.log_stream = log_stream or self._generate_log_stream_name()
        self.region = region
        self.create_log_group = create_log_group
        
        self._client = None
        self._sequence_token = None
        self._enabled = False
        
        # Try to initialize CloudWatch client
        self._initialize_client()
    
    def _generate_log_stream_name(self) -> str:
        """Generate a unique log stream name."""
        import socket
        hostname = socket.gethostname()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{hostname}_{timestamp}"
    
    def _initialize_client(self) -> None:
        """Initialize CloudWatch Logs client with error handling."""
        try:
            self._client = boto3.client('logs', region_name=self.region)
            
            # Test credentials and create log group/stream if needed
            if self.create_log_group:
                self._ensure_log_group_exists()
            self._ensure_log_stream_exists()
            
            self._enabled = True
            
        except (NoCredentialsError, ClientError) as e:
            # Log to stderr that CloudWatch is unavailable
            print(f"CloudWatch logging unavailable: {e}", file=sys.stderr)
            self._enabled = False
    
    def _ensure_log_group_exists(self) -> None:
        """Create log group if it doesn't exist."""
        try:
            self._client.create_log_group(logGroupName=self.log_group)
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
    
    def _ensure_log_stream_exists(self) -> None:
        """Create log stream if it doesn't exist."""
        try:
            self._client.create_log_stream(
                logGroupName=self.log_group,
                logStreamName=self.log_stream
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to CloudWatch.
        
        Args:
            record: Log record to emit
        """
        if not self._enabled or not self._client:
            return
        
        try:
            # Format the log message
            message = self.format(record)
            
            # Prepare log event
            log_event = {
                'timestamp': int(record.created * 1000),  # CloudWatch expects milliseconds
                'message': message
            }
            
            # Send to CloudWatch
            kwargs = {
                'logGroupName': self.log_group,
                'logStreamName': self.log_stream,
                'logEvents': [log_event]
            }
            
            if self._sequence_token:
                kwargs['sequenceToken'] = self._sequence_token
            
            response = self._client.put_log_events(**kwargs)
            self._sequence_token = response.get('nextSequenceToken')
            
        except Exception as e:
            # Fallback to stderr if CloudWatch fails
            print(f"CloudWatch logging failed: {e}", file=sys.stderr)
            print(f"Log message: {self.format(record)}", file=sys.stderr)


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
    import threading
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


class LoggerConfig:
    """Configuration class for logging setup."""
    
    def __init__(
        self,
        log_level: str = "INFO",
        log_format: str = "json",
        log_file: Optional[str] = None,
        cloudwatch_log_group: Optional[str] = None,
        cloudwatch_region: str = "us-east-1",
        enable_console: bool = True,
        enable_cloudwatch: bool = False
    ):
        """
        Initialize logger configuration.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_format: Log format ('json' or 'console')
            log_file: Path to log file (optional)
            cloudwatch_log_group: CloudWatch log group name (optional)
            cloudwatch_region: AWS region for CloudWatch
            enable_console: Whether to enable console logging
            enable_cloudwatch: Whether to enable CloudWatch logging
        """
        self.log_level = log_level.upper()
        self.log_format = log_format
        self.log_file = log_file
        self.cloudwatch_log_group = cloudwatch_log_group
        self.cloudwatch_region = cloudwatch_region
        self.enable_console = enable_console
        self.enable_cloudwatch = enable_cloudwatch and cloudwatch_log_group is not None


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


def log_exception(
    logger: FilteringBoundLogger,
    exception: Exception,
    message: str = "An error occurred",
    **context
) -> None:
    """
    Log an exception with proper context and structure.
    
    Args:
        logger: Logger instance
        exception: Exception to log
        message: Log message
        **context: Additional context to include
    """
    if isinstance(exception, EKSUpgradeAgentError):
        # Use the exception's structured data
        logger.error(
            message,
            exception_data=exception.to_dict(),
            **context
        )
    else:
        # Log regular exceptions
        logger.error(
            message,
            exc_info=exception,
            **context
        )


def log_upgrade_step(
    logger: FilteringBoundLogger,
    step_name: str,
    step_id: str,
    status: str,
    **context
) -> None:
    """
    Log upgrade step progress with consistent structure.
    
    Args:
        logger: Logger instance
        step_name: Name of the upgrade step
        step_id: Unique step identifier
        status: Step status (started, completed, failed)
        **context: Additional context to include
    """
    logger.info(
        f"Upgrade step {status}",
        step_name=step_name,
        step_id=step_id,
        status=status,
        **context
    )


def log_aws_api_call(
    logger: FilteringBoundLogger,
    service: str,
    operation: str,
    success: bool,
    duration_ms: Optional[float] = None,
    **context
) -> None:
    """
    Log AWS API calls with consistent structure.
    
    Args:
        logger: Logger instance
        service: AWS service name
        operation: API operation name
        success: Whether the call succeeded
        duration_ms: Call duration in milliseconds
        **context: Additional context to include
    """
    level = "info" if success else "error"
    getattr(logger, level)(
        f"AWS API call {('succeeded' if success else 'failed')}",
        aws_service=service,
        aws_operation=operation,
        success=success,
        duration_ms=duration_ms,
        **context
    )


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