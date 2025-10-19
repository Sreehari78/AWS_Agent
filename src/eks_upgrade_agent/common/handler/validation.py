"""
Validation phase exceptions for the EKS Upgrade Agent.
"""

from typing import Any, Dict, List, Optional

from .base import EKSUpgradeAgentError


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