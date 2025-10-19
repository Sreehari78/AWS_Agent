"""
AWS AI service models for Bedrock, Comprehend, and other AI services.
"""

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.types import PositiveFloat, PositiveInt


class BedrockAnalysisResult(BaseModel):
    """Result from Amazon Bedrock analysis."""

    analysis_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique analysis ID"
    )
    model_id: str = Field(..., description="Bedrock model used for analysis")
    input_text: str = Field(..., description="Input text analyzed")
    findings: List[str] = Field(..., description="Analysis findings")
    breaking_changes: List[str] = Field(
        default_factory=list, description="Identified breaking changes"
    )
    deprecations: List[str] = Field(
        default_factory=list, description="Identified deprecations"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommended actions"
    )
    severity_score: PositiveFloat = Field(
        ..., ge=0.0, le=10.0, description="Severity score (0-10)"
    )
    confidence: PositiveFloat = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    processing_time: PositiveFloat = Field(
        ..., description="Processing time in seconds"
    )
    token_usage: Dict[str, int] = Field(
        default_factory=dict, description="Token usage statistics"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Analysis timestamp"
    )

    @field_validator("severity_score")
    @classmethod
    def validate_severity_score(cls, v):
        if not 0.0 <= v <= 10.0:
            raise ValueError("Severity score must be between 0.0 and 10.0")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class ComprehendEntity(BaseModel):
    """Named entity extracted by Amazon Comprehend."""

    text: str = Field(..., description="Entity text")
    type: str = Field(..., description="Entity type")
    confidence: PositiveFloat = Field(
        ..., ge=0.0, le=1.0, description="Confidence score"
    )
    begin_offset: int = Field(..., ge=0, description="Start position in text")
    end_offset: int = Field(..., ge=0, description="End position in text")
    category: Optional[str] = Field(None, description="Entity category")
    subcategory: Optional[str] = Field(None, description="Entity subcategory")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    @model_validator(mode="after")
    def validate_offsets(self):
        if self.end_offset <= self.begin_offset:
            raise ValueError("End offset must be greater than begin offset")
        return self


class AWSAIConfig(BaseModel):
    """Configuration for AWS AI services."""

    # Amazon Bedrock configuration
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-sonnet-20240229-v1:0",
        description="Bedrock model ID for analysis",
    )
    bedrock_region: str = Field(default="us-east-1", description="AWS region for Bedrock")
    bedrock_max_tokens: PositiveInt = Field(
        default=4096, description="Maximum tokens for Bedrock"
    )
    bedrock_temperature: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Model temperature"
    )

    # Amazon Comprehend configuration
    comprehend_endpoint: Optional[str] = Field(
        None, description="Custom Comprehend endpoint"
    )
    comprehend_region: str = Field(
        default="us-east-1", description="AWS region for Comprehend"
    )
    comprehend_language_code: str = Field(
        default="en", description="Language code for analysis"
    )

    # AWS Step Functions configuration
    step_functions_arn: Optional[str] = Field(
        None, description="Step Functions state machine ARN"
    )
    step_functions_region: str = Field(
        default="us-east-1", description="AWS region for Step Functions"
    )

    # Amazon EventBridge configuration
    eventbridge_bus_name: str = Field(
        default="default", description="EventBridge bus name"
    )
    eventbridge_region: str = Field(
        default="us-east-1", description="AWS region for EventBridge"
    )

    # AWS Systems Manager configuration
    ssm_parameter_prefix: str = Field(
        default="/eks-upgrade-agent/",
        description="SSM parameter prefix for configuration",
    )
    ssm_region: str = Field(default="us-east-1", description="AWS region for SSM")

    # General AWS configuration
    aws_profile: Optional[str] = Field(None, description="AWS profile to use")
    aws_access_key_id: Optional[str] = Field(None, description="AWS access key ID")
    aws_secret_access_key: Optional[str] = Field(
        None, description="AWS secret access key"
    )
    aws_session_token: Optional[str] = Field(None, description="AWS session token")

    # Cost and rate limiting
    max_bedrock_requests_per_minute: PositiveInt = Field(
        default=60, description="Bedrock rate limit"
    )
    max_comprehend_requests_per_minute: PositiveInt = Field(
        default=100, description="Comprehend rate limit"
    )
    cost_threshold_usd: PositiveFloat = Field(
        default=100.0, description="Daily cost threshold"
    )

    @field_validator("bedrock_temperature")
    @classmethod
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        return v