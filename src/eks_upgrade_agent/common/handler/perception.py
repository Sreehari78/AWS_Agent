"""
Perception phase exceptions for the EKS Upgrade Agent.
"""

from typing import Optional

from .base import EKSUpgradeAgentError


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