"""
Configuration exceptions for the EKS Upgrade Agent.
"""

from typing import Any, Dict, List, Optional

from .base import EKSUpgradeAgentError


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