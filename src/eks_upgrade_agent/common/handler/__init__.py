"""
Exception handler hierarchy for the EKS Upgrade Agent.

This module defines a comprehensive exception hierarchy that preserves error context
and integrates with the centralized logging system.
"""

from .base import EKSUpgradeAgentError
from .perception import PerceptionError
from .planning import PlanningError
from .execution import ExecutionError
from .validation import ValidationError
from .configuration import ConfigurationError
from .aws_service import AWSServiceError
from .rollback import RollbackError
from .factories import (
    create_perception_error,
    create_execution_error,
    create_validation_error
)

__all__ = [
    "EKSUpgradeAgentError",
    "PerceptionError",
    "PlanningError", 
    "ExecutionError",
    "ValidationError",
    "ConfigurationError",
    "AWSServiceError",
    "RollbackError",
    "create_perception_error",
    "create_execution_error",
    "create_validation_error"
]