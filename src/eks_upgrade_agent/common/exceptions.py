"""
Custom exception hierarchy for the EKS Upgrade Agent.

This module defines a comprehensive exception hierarchy that preserves error context
and integrates with the centralized logging system for proper error tracking and debugging.
"""

import traceback
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone, timezone


class EKSUpgradeAgentError(Exception):
    """
    Base exception class for all EKS Upgrade Agent errors.
    
    Provides common functionality for error context preservation,
    structured error data, and integration with logging systems.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        recoverable: bool = False
    ):
        """
        Initialize the base exception with comprehensive error information.
        
        Args:
            message: Human-readable error description
            error_code: Machine-readable error identifier
            context: Additional context data for debugging
            cause: Original exception that caused this error
            recoverable: Whether this error can be recovered from
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.cause = cause
        self.recoverable = recoverable
        self.timestamp = datetime.now(timezone.utc)
        self.stack_trace = traceback.format_exc()
        
        # Preserve the original exception chain
        if cause:
            self.__cause__ = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for structured logging.
        
        Returns:
            Dictionary representation of the exception with all context
        """
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace,
            "cause": str(self.cause) if self.cause else None,
            "cause_type": type(self.cause).__name__ if self.cause else None
        }
    
    def add_context(self, key: str, value: Any) -> "EKSUpgradeAgentError":
        """
        Add additional context to the exception.
        
        Args:
            key: Context key
            value: Context value
            
        Returns:
            Self for method chaining
        """
        self.context[key] = value
        return self
    
    def __str__(self) -> str:
        """String representation including error code and context."""
        context_str = f" (Context: {self.context})" if self.context else ""
        return f"[{self.error_code}] {self.message}{context_str}"


class PerceptionError(EKSUpgradeAgentError):
    """
    Exceptions related to data collection and perception phase failures.
    
    This includes AWS API failures, Kubernetes API timeouts, release notes
    collection errors, and deprecation scanning issues.
    """
    
    def __init__(
        self,
        message: str,
        source: Optional[str] = None,
        api_error: Optional[Exception] = None,
        **kwargs
    ):
        """
        Initialize perception error with source information.
        
        Args:
            message: Error description
            source: Data source that failed (e.g., 'aws_api', 'k8s_api', 'release_notes')
            api_error: Original API exception
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.get('context', {})
        if source:
            context['source'] = source
        if api_error:
            context['api_error_type'] = type(api_error).__name__
            context['api_error_message'] = str(api_error)
        
        kwargs['context'] = context
        kwargs['cause'] = api_error or kwargs.get('cause')
        
        super().__init__(message, **kwargs)


class PlanningError(EKSUpgradeAgentError):
    """
    Exceptions related to upgrade planning and reasoning phase failures.
    
    This includes NLP analysis failures, strategy selection errors, plan generation
    issues, and configuration validation problems.
    """
    
    def __init__(
        self,
        message: str,
        planning_phase: Optional[str] = None,
        invalid_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize planning error with phase information.
        
        Args:
            message: Error description
            planning_phase: Phase that failed (e.g., 'nlp_analysis', 'strategy_selection', 'plan_generation')
            invalid_config: Configuration that caused the error
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.get('context', {})
        if planning_phase:
            context['planning_phase'] = planning_phase
        if invalid_config:
            context['invalid_config'] = invalid_config
        
        kwargs['context'] = context
        
        super().__init__(message, **kwargs)


class ExecutionError(EKSUpgradeAgentError):
    """
    Exceptions related to upgrade execution phase failures.
    
    This includes infrastructure provisioning failures, GitOps deployment errors,
    traffic management issues, and CLI command execution problems.
    """
    
    def __init__(
        self,
        message: str,
        execution_step: Optional[str] = None,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize execution error with command details.
        
        Args:
            message: Error description
            execution_step: Step that failed (e.g., 'provision_cluster', 'deploy_apps', 'shift_traffic')
            command: Command that failed
            exit_code: Command exit code
            stdout: Command standard output
            stderr: Command standard error
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.get('context', {})
        if execution_step:
            context['execution_step'] = execution_step
        if command:
            context['command'] = command
        if exit_code is not None:
            context['exit_code'] = exit_code
        if stdout:
            context['stdout'] = stdout[:1000]  # Truncate long output
        if stderr:
            context['stderr'] = stderr[:1000]  # Truncate long output
        
        kwargs['context'] = context
        
        super().__init__(message, **kwargs)


class ValidationError(EKSUpgradeAgentError):
    """
    Exceptions related to validation phase failures.
    
    This includes health check failures, metrics analysis problems, test execution
    errors, and rollback trigger conditions.
    """
    
    def __init__(
        self,
        message: str,
        validation_type: Optional[str] = None,
        failed_checks: Optional[List[str]] = None,
        metrics: Optional[Dict[str, float]] = None,
        threshold_violations: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize validation error with check details.
        
        Args:
            message: Error description
            validation_type: Type of validation that failed (e.g., 'health_check', 'metrics', 'tests')
            failed_checks: List of specific checks that failed
            metrics: Relevant metrics at time of failure
            threshold_violations: Threshold violations that triggered the error
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.get('context', {})
        if validation_type:
            context['validation_type'] = validation_type
        if failed_checks:
            context['failed_checks'] = failed_checks
        if metrics:
            context['metrics'] = metrics
        if threshold_violations:
            context['threshold_violations'] = threshold_violations
        
        kwargs['context'] = context
        
        super().__init__(message, **kwargs)


class ConfigurationError(EKSUpgradeAgentError):
    """
    Exceptions related to configuration validation and loading.
    
    This includes invalid YAML files, missing required settings, AWS credential
    issues, and environment setup problems.
    """
    
    def __init__(
        self,
        message: str,
        config_file: Optional[str] = None,
        missing_keys: Optional[List[str]] = None,
        invalid_values: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize configuration error with config details.
        
        Args:
            message: Error description
            config_file: Configuration file that caused the error
            missing_keys: List of missing required configuration keys
            invalid_values: Dictionary of invalid configuration values
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.get('context', {})
        if config_file:
            context['config_file'] = config_file
        if missing_keys:
            context['missing_keys'] = missing_keys
        if invalid_values:
            context['invalid_values'] = invalid_values
        
        kwargs['context'] = context
        
        super().__init__(message, **kwargs)


class AWSServiceError(EKSUpgradeAgentError):
    """
    Exceptions related to AWS service integration failures.
    
    This includes Bedrock API errors, Comprehend service issues, Step Functions
    execution failures, and EventBridge problems.
    """
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        operation: Optional[str] = None,
        aws_error_code: Optional[str] = None,
        aws_error_message: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize AWS service error with service details.
        
        Args:
            message: Error description
            service_name: AWS service that failed (e.g., 'bedrock', 'comprehend', 'stepfunctions')
            operation: Operation that failed
            aws_error_code: AWS error code
            aws_error_message: AWS error message
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.get('context', {})
        if service_name:
            context['service_name'] = service_name
        if operation:
            context['operation'] = operation
        if aws_error_code:
            context['aws_error_code'] = aws_error_code
        if aws_error_message:
            context['aws_error_message'] = aws_error_message
        
        kwargs['context'] = context
        
        super().__init__(message, **kwargs)


class RollbackError(EKSUpgradeAgentError):
    """
    Exceptions related to rollback operation failures.
    
    This is a critical error type as it indicates that both the upgrade
    and the rollback have failed, requiring manual intervention.
    """
    
    def __init__(
        self,
        message: str,
        rollback_step: Optional[str] = None,
        original_error: Optional[Exception] = None,
        **kwargs
    ):
        """
        Initialize rollback error with rollback details.
        
        Args:
            message: Error description
            rollback_step: Rollback step that failed
            original_error: Original error that triggered the rollback
            **kwargs: Additional arguments passed to base class
        """
        context = kwargs.get('context', {})
        if rollback_step:
            context['rollback_step'] = rollback_step
        if original_error:
            context['original_error_type'] = type(original_error).__name__
            context['original_error_message'] = str(original_error)
        
        kwargs['context'] = context
        kwargs['cause'] = original_error or kwargs.get('cause')
        kwargs['recoverable'] = False  # Rollback failures are not recoverable
        
        super().__init__(message, **kwargs)


# Convenience functions for creating common exceptions
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