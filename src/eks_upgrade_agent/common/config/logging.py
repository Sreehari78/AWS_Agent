"""
Logging configuration for the EKS Upgrade Agent.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string"
    )
    structured: bool = Field(default=True, description="Use structured JSON logging")
    cloudwatch_enabled: bool = Field(default=False, description="Enable CloudWatch logging")
    cloudwatch_log_group: Optional[str] = Field(None, description="CloudWatch log group")
    cloudwatch_log_stream: Optional[str] = Field(None, description="CloudWatch log stream")
    file_enabled: bool = Field(default=True, description="Enable file logging")
    file_path: str = Field(default="logs/eks-upgrade-agent.log", description="Log file path")
    max_file_size: str = Field(default="10MB", description="Maximum log file size")
    backup_count: int = Field(default=5, description="Number of backup log files")

    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()