"""
Upgrade configuration for the EKS Upgrade Agent.
"""

from typing import List
from pydantic import BaseModel, Field, field_validator


class UpgradeConfig(BaseModel):
    """Upgrade-specific configuration."""
    
    default_strategy: str = Field(default="blue_green", description="Default upgrade strategy")
    max_parallel_upgrades: int = Field(default=1, description="Maximum parallel upgrades")
    upgrade_timeout_minutes: int = Field(default=120, description="Upgrade timeout in minutes")
    rollback_timeout_minutes: int = Field(default=30, description="Rollback timeout in minutes")
    health_check_interval_seconds: int = Field(
        default=30, description="Health check interval in seconds"
    )
    traffic_shift_intervals: List[int] = Field(
        default=[10, 25, 50, 75, 100], description="Traffic shift percentages"
    )
    validation_timeout_minutes: int = Field(
        default=15, description="Validation timeout per step in minutes"
    )
    backup_enabled: bool = Field(default=True, description="Enable cluster backup")
    backup_retention_days: int = Field(default=7, description="Backup retention in days")

    @field_validator("traffic_shift_intervals")
    @classmethod
    def validate_traffic_intervals(cls, v):
        if not v or v[-1] != 100:
            raise ValueError("Traffic shift intervals must end with 100")
        if any(x <= 0 or x > 100 for x in v):
            raise ValueError("Traffic shift intervals must be between 1 and 100")
        if v != sorted(v):
            raise ValueError("Traffic shift intervals must be in ascending order")
        return v