"""
Planning phase exceptions for the EKS Upgrade Agent.
"""

from typing import Any, Dict, Optional

from .base import EKSUpgradeAgentError


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