"""
Enums and constants for the EKS Upgrade Agent models.
"""

from enum import Enum


class StrategyType(str, Enum):
    """Supported upgrade strategies."""
    BLUE_GREEN = "blue_green"
    IN_PLACE = "in_place"
    ROLLING = "rolling"


class ValidationStatus(str, Enum):
    """Validation result status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class UpgradeStatus(str, Enum):
    """Overall upgrade status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class NodeGroupStatus(str, Enum):
    """EKS node group status."""
    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    UPDATING = "UPDATING"
    DELETING = "DELETING"
    CREATE_FAILED = "CREATE_FAILED"
    DELETE_FAILED = "DELETE_FAILED"
    DEGRADED = "DEGRADED"


class AddonStatus(str, Enum):
    """EKS addon status."""
    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    CREATE_FAILED = "CREATE_FAILED"
    UPDATING = "UPDATING"
    DELETING = "DELETING"
    DELETE_FAILED = "DELETE_FAILED"
    DEGRADED = "DEGRADED"


class ApplicationStatus(str, Enum):
    """Application deployment status."""
    HEALTHY = "healthy"
    PROGRESSING = "progressing"
    DEGRADED = "degraded"
    SUSPENDED = "suspended"
    MISSING = "missing"
    UNKNOWN = "unknown"


class SeverityLevel(str, Enum):
    """Severity levels for issues and findings."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"