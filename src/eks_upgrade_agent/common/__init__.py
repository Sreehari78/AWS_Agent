"""
Common utilities and shared components for the EKS Upgrade Agent.

This module contains configuration management, logging, exception handling,
data models, and other utilities shared across all agent modules.
"""

# Import from the models package
from .models import (
    AWSAIConfig,
    BedrockAnalysisResult,
    ClusterState,
    ComprehendEntity,
    UpgradePlan,
    UpgradeStep,
    ValidationResult,
)

# Import configuration management
from .config import AgentConfig

# Import logging utilities
from .logging import (
    LoggerConfig,
    setup_logging,
    get_logger,
    get_default_logger,
    init_default_logger,
    log_exception,
    log_upgrade_step,
    log_aws_api_call,
)

# Import exception hierarchy
from .handler import (
    EKSUpgradeAgentError,
    PerceptionError,
    PlanningError,
    ExecutionError,
    ValidationError,
    ConfigurationError,
    AWSServiceError,
    RollbackError,
    create_perception_error,
    create_execution_error,
    create_validation_error,
)

# Import progress tracking and test artifacts
from .progress import ProgressTracker
from .artifacts import TestArtifactsManager

__all__ = [
    # Configuration
    "AgentConfig",
    
    # Data Models
    "ClusterState",
    "UpgradePlan",
    "UpgradeStep",
    "ValidationResult",
    "BedrockAnalysisResult",
    "ComprehendEntity",
    "AWSAIConfig",
    
    # Logging
    "LoggerConfig",
    "setup_logging",
    "get_logger",
    "get_default_logger",
    "init_default_logger",
    "log_exception",
    "log_upgrade_step",
    "log_aws_api_call",
    
    # Exceptions
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
    "create_validation_error",
    
    # Progress Tracking and Test Artifacts
    "ProgressTracker",
    "TestArtifactsManager",
]