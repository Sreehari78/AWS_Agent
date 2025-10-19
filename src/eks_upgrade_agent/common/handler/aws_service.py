"""
AWS service exceptions for the EKS Upgrade Agent.
"""

from typing import Optional

from .base import EKSUpgradeAgentError


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