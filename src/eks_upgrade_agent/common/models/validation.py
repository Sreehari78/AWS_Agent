"""
Validation-related models for upgrade validation and error handling.
"""

from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from .enums import SeverityLevel, ValidationStatus


class ValidationCriterion(BaseModel):
    """Criteria for validating upgrade steps."""

    name: str = Field(..., description="Validation criterion name")
    description: str = Field(..., description="Criterion description")
    metric: str = Field(..., description="Metric to evaluate")
    operator: str = Field(..., description="Comparison operator (>, <, ==, etc.)")
    threshold: Union[int, float, str] = Field(..., description="Threshold value")
    timeout: timedelta = Field(
        default=timedelta(minutes=5), description="Validation timeout"
    )
    retry_count: int = Field(default=3, ge=0, description="Number of retries")
    critical: bool = Field(
        default=True, description="Whether failure blocks upgrade"
    )

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v):
        valid_operators = [">", "<", ">=", "<=", "==", "!=", "contains", "not_contains"]
        if v not in valid_operators:
            raise ValueError(f"Operator must be one of: {valid_operators}")
        return v


class ValidationError(BaseModel):
    """Validation error details."""

    model_config = ConfigDict(use_enum_values=True)

    error_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique error ID"
    )
    criterion_name: str = Field(..., description="Failed validation criterion")
    message: str = Field(..., description="Error message")
    actual_value: Optional[Union[int, float, str]] = Field(
        None, description="Actual metric value"
    )
    expected_value: Optional[Union[int, float, str]] = Field(
        None, description="Expected metric value"
    )
    severity: SeverityLevel = Field(..., description="Error severity")
    remediation: Optional[str] = Field(None, description="Suggested remediation")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Error timestamp"
    )


class ValidationResult(BaseModel):
    """Result of validation step execution."""

    model_config = ConfigDict(use_enum_values=True)

    result_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique result ID"
    )
    step_id: str = Field(..., description="Associated upgrade step ID")
    status: ValidationStatus = Field(..., description="Validation status")
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Validation start time"
    )
    completed_at: Optional[datetime] = Field(
        None, description="Validation completion time"
    )
    duration: Optional[timedelta] = Field(None, description="Validation duration")
    metrics: Dict[str, Union[int, float, str]] = Field(
        default_factory=dict, description="Collected metrics"
    )
    errors: List[ValidationError] = Field(
        default_factory=list, description="Validation errors"
    )
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional details"
    )

    @model_validator(mode="after")
    def validate_completion(self):
        if (
            self.status in [ValidationStatus.PASSED, ValidationStatus.FAILED]
            and not self.completed_at
        ):
            self.completed_at = datetime.now(UTC)

        if self.started_at and self.completed_at:
            self.duration = self.completed_at - self.started_at

        return self