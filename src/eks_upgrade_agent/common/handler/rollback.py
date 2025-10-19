"""
Rollback exceptions for the EKS Upgrade Agent.
"""

from typing import Optional

from .base import EKSUpgradeAgentError


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