"""
EKS Upgrade Agent Models Package.

This package contains all Pydantic models used throughout the system for data validation,
serialization, and type safety. Models are organized by functional area for better
maintainability and readability.
"""

# Import all enums
from .enums import (
    AddonStatus,
    ApplicationStatus,
    NodeGroupStatus,
    SeverityLevel,
    StrategyType,
    UpgradeStatus,
    ValidationStatus,
)

# Import AWS resource models
from .aws_resources import (
    AddonInfo,
    ApplicationInfo,
    DeprecatedAPIInfo,
    NodeGroupInfo,
)

# Import AWS AI service models
from .aws_ai import (
    AWSAIConfig,
    BedrockAnalysisResult,
    ComprehendEntity,
)

# Import validation models
from .validation import (
    ValidationCriterion,
    ValidationError,
    ValidationResult,
)

# Import upgrade models
from .upgrade import (
    RollbackAction,
    RollbackPlan,
    UpgradePlan,
    UpgradeResult,
    UpgradeStep,
)

# Import cluster models
from .cluster import ClusterState

# Import progress tracking models
from .progress import (
    ProgressEvent,
    ProgressStatus,
    TaskProgress,
    TaskType,
    UpgradeProgress,
)

# Import test artifacts models
from .artifacts import (
    ArtifactCollection,
    ArtifactStatus,
    ArtifactType,
    TestArtifact,
    TestSession,
)

# Export all models for easy importing
__all__ = [
    # Enums
    "StrategyType",
    "ValidationStatus",
    "UpgradeStatus",
    "NodeGroupStatus",
    "AddonStatus",
    "ApplicationStatus",
    "SeverityLevel",
    # AWS Resource Models
    "NodeGroupInfo",
    "AddonInfo",
    "ApplicationInfo",
    "DeprecatedAPIInfo",
    # AWS AI Models
    "BedrockAnalysisResult",
    "ComprehendEntity",
    "AWSAIConfig",
    # Validation Models
    "ValidationCriterion",
    "ValidationError",
    "ValidationResult",
    # Upgrade Models
    "RollbackAction",
    "RollbackPlan",
    "UpgradeStep",
    "UpgradePlan",
    "UpgradeResult",
    # Cluster Models
    "ClusterState",
    # Progress Tracking Models
    "ProgressEvent",
    "ProgressStatus",
    "TaskProgress",
    "TaskType",
    "UpgradeProgress",
    # Test Artifacts Models
    "ArtifactCollection",
    "ArtifactStatus",
    "ArtifactType",
    "TestArtifact",
    "TestSession",
]