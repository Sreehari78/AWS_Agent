"""
Upgrade-related models for plans, steps, and execution tracking.
"""

from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import StrategyType, UpgradeStatus
from .validation import ValidationCriterion, ValidationResult


class RollbackAction(BaseModel):
    """Action to perform during rollback."""

    action_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique action ID"
    )
    name: str = Field(..., description="Rollback action name")
    description: str = Field(..., description="Action description")
    executor: str = Field(..., description="Executor responsible for action")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Action parameters"
    )
    timeout: timedelta = Field(
        default=timedelta(minutes=10), description="Action timeout"
    )
    critical: bool = Field(
        default=True, description="Whether action failure blocks rollback"
    )
    order: int = Field(default=0, description="Execution order (lower first)")


class RollbackPlan(BaseModel):
    """Plan for rolling back an upgrade."""

    plan_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique rollback plan ID"
    )
    name: str = Field(..., description="Rollback plan name")
    description: str = Field(..., description="Plan description")
    actions: List[RollbackAction] = Field(..., description="Rollback actions")
    estimated_duration: timedelta = Field(
        ..., description="Estimated rollback duration"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Plan creation time"
    )

    @field_validator("actions")
    @classmethod
    def validate_actions_order(cls, v):
        if not v:
            raise ValueError("Rollback plan must have at least one action")

        # Sort actions by order
        v.sort(key=lambda x: x.order)
        return v


class UpgradeStep(BaseModel):
    """Individual step in an upgrade plan."""

    step_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique step ID"
    )
    name: str = Field(..., description="Step name")
    description: str = Field(..., description="Step description")
    executor: str = Field(..., description="Executor module responsible")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Step parameters"
    )
    validation_criteria: List[ValidationCriterion] = Field(
        default_factory=list, description="Validation criteria"
    )
    rollback_action: Optional[RollbackAction] = Field(
        None, description="Rollback action"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Dependent step IDs"
    )
    timeout: timedelta = Field(default=timedelta(minutes=30), description="Step timeout")
    retry_count: int = Field(default=1, ge=1, description="Number of retry attempts")
    critical: bool = Field(
        default=True, description="Whether failure blocks upgrade"
    )
    order: int = Field(default=0, description="Execution order")
    estimated_duration: Optional[timedelta] = Field(
        None, description="Estimated duration"
    )

    # Execution tracking
    status: UpgradeStatus = Field(
        default=UpgradeStatus.NOT_STARTED, description="Step status"
    )
    started_at: Optional[datetime] = Field(None, description="Step start time")
    completed_at: Optional[datetime] = Field(None, description="Step completion time")
    actual_duration: Optional[timedelta] = Field(
        None, description="Actual execution duration"
    )
    validation_results: List[ValidationResult] = Field(
        default_factory=list, description="Validation results"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        use_enum_values = True

    @model_validator(mode="after")
    def validate_execution_times(self):
        if self.started_at and self.completed_at:
            self.actual_duration = self.completed_at - self.started_at

        return self


class UpgradePlan(BaseModel):
    """Complete upgrade execution plan."""

    plan_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique plan ID"
    )
    name: str = Field(..., description="Plan name")
    description: str = Field(..., description="Plan description")
    source_version: str = Field(..., description="Current EKS version")
    target_version: str = Field(..., description="Target EKS version")
    strategy: StrategyType = Field(..., description="Upgrade strategy")
    cluster_name: str = Field(..., description="Target cluster name")

    # Plan structure
    steps: List[UpgradeStep] = Field(..., description="Upgrade steps")
    rollback_plan: RollbackPlan = Field(..., description="Rollback plan")

    # Timing and estimation
    estimated_duration: timedelta = Field(
        ..., description="Estimated total duration"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Plan creation time"
    )

    # Execution tracking
    status: UpgradeStatus = Field(
        default=UpgradeStatus.NOT_STARTED, description="Plan status"
    )
    started_at: Optional[datetime] = Field(None, description="Execution start time")
    completed_at: Optional[datetime] = Field(
        None, description="Execution completion time"
    )
    actual_duration: Optional[timedelta] = Field(
        None, description="Actual execution duration"
    )
    current_step_index: int = Field(default=0, ge=0, description="Current step index")

    # Configuration and context
    configuration: Dict[str, Any] = Field(
        default_factory=dict, description="Plan configuration"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Execution context"
    )

    class Config:
        use_enum_values = True

    @field_validator("steps")
    @classmethod
    def validate_steps_order(cls, v):
        if not v:
            raise ValueError("Upgrade plan must have at least one step")

        # Sort steps by order
        v.sort(key=lambda x: x.order)

        # Validate step dependencies
        step_ids = {step.step_id for step in v}
        for step in v:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    raise ValueError(
                        f"Step {step.step_id} depends on non-existent step {dep_id}"
                    )

        return v

    @model_validator(mode="after")
    def validate_execution_times(self):
        if self.started_at and self.completed_at:
            self.actual_duration = self.completed_at - self.started_at

        return self

    def get_current_step(self) -> Optional[UpgradeStep]:
        """Get the current step being executed."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def get_next_step(self) -> Optional[UpgradeStep]:
        """Get the next step to execute."""
        next_index = self.current_step_index + 1
        if next_index < len(self.steps):
            return self.steps[next_index]
        return None

    def advance_step(self) -> bool:
        """Advance to the next step. Returns True if advanced, False if at end."""
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            return True
        return False


class UpgradeResult(BaseModel):
    """Final result of an upgrade operation."""

    result_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique result ID"
    )
    plan_id: str = Field(..., description="Associated plan ID")
    cluster_name: str = Field(..., description="Cluster name")
    source_version: str = Field(..., description="Source version")
    target_version: str = Field(..., description="Target version")
    strategy: StrategyType = Field(..., description="Strategy used")

    # Result status
    status: UpgradeStatus = Field(..., description="Final upgrade status")
    success: bool = Field(..., description="Whether upgrade succeeded")

    # Timing information
    started_at: datetime = Field(..., description="Upgrade start time")
    completed_at: datetime = Field(..., description="Upgrade completion time")
    total_duration: timedelta = Field(..., description="Total upgrade duration")

    # Step results
    completed_steps: int = Field(default=0, ge=0, description="Number of completed steps")
    total_steps: int = Field(..., gt=0, description="Total number of steps")
    failed_step: Optional[str] = Field(None, description="Failed step ID if any")

    # Validation and rollback
    validation_results: List[ValidationResult] = Field(
        default_factory=list, description="All validation results"
    )
    rollback_performed: bool = Field(
        default=False, description="Whether rollback was performed"
    )
    rollback_success: Optional[bool] = Field(
        None, description="Rollback success if performed"
    )

    # Error information
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_details: Dict[str, Any] = Field(
        default_factory=dict, description="Detailed error info"
    )

    # Artifacts and logs
    log_files: List[str] = Field(default_factory=list, description="Generated log files")
    artifacts: Dict[str, str] = Field(
        default_factory=dict, description="Generated artifacts"
    )

    class Config:
        use_enum_values = True

    @model_validator(mode="after")
    def validate_result_consistency(self):
        # Ensure status and success are consistent
        if self.status == UpgradeStatus.COMPLETED and not self.success:
            raise ValueError("Completed status must have success=True")
        elif (
            self.status in [UpgradeStatus.FAILED, UpgradeStatus.ROLLED_BACK]
            and self.success
        ):
            raise ValueError( "Failed/rolled back status must have success=False")

        # Calculate duration
        if self.started_at and self.completed_at:
            self.total_duration = self.completed_at - self.started_at

        return self