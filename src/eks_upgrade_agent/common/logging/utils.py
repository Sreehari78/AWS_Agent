"""
Logging utility functions for the EKS Upgrade Agent.
"""

from typing import Optional

from structlog.types import FilteringBoundLogger

from ..handler import EKSUpgradeAgentError


def log_exception(
    logger: FilteringBoundLogger,
    exception,  # Can be Exception or str
    message: str = "An error occurred",
    **context
) -> None:
    """
    Log an exception with proper context and structure.
    
    Args:
        logger: Logger instance
        exception: Exception to log or error message string
        message: Log message
        **context: Additional context to include
    """
    if isinstance(exception, str):
        # Handle string error messages
        logger.error(f"{message}: {exception}", **context)
    elif isinstance(exception, EKSUpgradeAgentError):
        # Use the exception's structured data
        logger.error(
            message,
            exception_data=exception.to_dict(),
            **context
        )
    elif exception is None:
        # Handle None values gracefully
        logger.error(message, **context)
    else:
        # Log regular exceptions
        logger.error(
            message,
            exc_info=exception,
            **context
        )


def log_upgrade_step(
    logger: FilteringBoundLogger,
    step_name: Optional[str],
    action: str,
    cluster_name: Optional[str] = None,
    upgrade_id: Optional[str] = None,
    extra_context: Optional[dict] = None,
    **context
) -> None:
    """
    Log upgrade step progress with consistent structure.
    
    Args:
        logger: Logger instance
        step_name: Name of the upgrade step
        action: Step action (start, complete, fail)
        cluster_name: Target cluster name
        upgrade_id: Unique upgrade identifier
        extra_context: Additional context dictionary
        **context: Additional context to include
    """
    step_name = step_name or "Unknown Step"
    message = f"Upgrade step {step_name} {action}"
    
    log_context = {
        "step_name": step_name,
        "action": action,
        "cluster_name": cluster_name,
        "upgrade_id": upgrade_id,
        **context
    }
    
    if extra_context:
        log_context["extra"] = extra_context
    
    if action == "fail":
        logger.error(message, **log_context)
    else:
        logger.info(message, **log_context)


def log_aws_api_call(
    logger: FilteringBoundLogger,
    service: Optional[str],
    operation: Optional[str],
    cluster_name: Optional[str] = None,
    duration: Optional[float] = None,
    success: Optional[bool] = True,
    error: Optional[str] = None,
    request_id: Optional[str] = None,
    **context
) -> None:
    """
    Log AWS API calls with consistent structure.
    
    Args:
        logger: Logger instance
        service: AWS service name
        operation: API operation name
        success: Whether the call succeeded
        cluster_name: Target cluster name
        duration: Call duration in seconds
        error: Error message if failed
        request_id: AWS request ID
        **context: Additional context to include
    """
    service = service or "unknown"
    operation = operation or "unknown"
    
    if success:
        message = f"AWS {service} {operation} succeeded"
        if request_id:
            message += f" (request_id: {request_id})"
        logger.info(
            message,
            aws_service=service,
            aws_operation=operation,
            cluster_name=cluster_name,
            duration=duration,
            request_id=request_id,
            **context
        )
    else:
        message = f"AWS {service} {operation} failed"
        if error:
            message += f": {error}"
        if request_id:
            message += f" (request_id: {request_id})"
        logger.error(
            message,
            aws_service=service,
            aws_operation=operation,
            cluster_name=cluster_name,
            duration=duration,
            error=error,
            request_id=request_id,
            **context
        )