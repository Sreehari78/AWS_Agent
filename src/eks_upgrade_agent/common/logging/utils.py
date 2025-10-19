"""
Logging utility functions for the EKS Upgrade Agent.
"""

from typing import Optional

from structlog.types import FilteringBoundLogger

from ..handler import EKSUpgradeAgentError


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