"""
Execution phase exceptions for the EKS Upgrade Agent.
"""

from typing import Optional

from .base import EKSUpgradeAgentError


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