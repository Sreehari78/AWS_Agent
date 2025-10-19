"""
Factory functions for creating common exceptions.
"""

from typing import List, Optional

from .perception import PerceptionError
from .execution import ExecutionError
from .validation import ValidationError


def create_perception_error(
    message: str,
    source: str,
    api_error: Optional[Exception] = None,
    **context
) -> PerceptionError:
    """Create a PerceptionError with common context."""
    return PerceptionError(
        message=message,
        source=source,
        api_error=api_error,
        context=context
    )


def create_execution_error(
    message: str,
    step: str,
    command: Optional[str] = None,
    exit_code: Optional[int] = None,
    **context
) -> ExecutionError:
    """Create an ExecutionError with common context."""
    return ExecutionError(
        message=message,
        execution_step=step,
        command=command,
        exit_code=exit_code,
        context=context
    )


def create_validation_error(
    message: str,
    validation_type: str,
    failed_checks: Optional[List[str]] = None,
    **context
) -> ValidationError:
    """Create a ValidationError with common context."""
    return ValidationError(
        message=message,
        validation_type=validation_type,
        failed_checks=failed_checks,
        context=context
    )