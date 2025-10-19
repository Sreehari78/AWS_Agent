"""
Main agent configuration for the EKS Upgrade Agent.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..models.aws_ai import AWSAIConfig
from .logging import LoggingConfig
from .security import SecurityConfig
from .upgrade import UpgradeConfig
from .kubernetes import KubernetesConfig
from .terraform import TerraformConfig
from .utils import ConfigUtils


class AgentConfig(BaseSettings):
    """
    Main configuration class for the EKS Upgrade Agent.
    
    Supports loading configuration from:
    - YAML files
    - Environment variables (with EKS_UPGRADE_AGENT_ prefix)
    - AWS Systems Manager Parameter Store
    - Direct instantiation
    """
    
    model_config = SettingsConfigDict(
        env_prefix="EKS_UPGRADE_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid"
    )
    
    # Core configuration
    agent_name: str = Field(default="eks-upgrade-agent", description="Agent instance name")
    version: str = Field(default="0.1.0", description="Agent version")
    environment: str = Field(default="development", description="Environment (dev/staging/prod)")
    debug: bool = Field(default=False, description="Enable debug mode")
    dry_run: bool = Field(default=False, description="Enable dry-run mode")
    
    # AWS AI services configuration
    aws_ai: AWSAIConfig = Field(default_factory=AWSAIConfig, description="AWS AI services config")
    
    # Component configurations
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging config")
    security: SecurityConfig = Field(default_factory=SecurityConfig, description="Security config")
    upgrade: UpgradeConfig = Field(default_factory=UpgradeConfig, description="Upgrade config")
    kubernetes: KubernetesConfig = Field(default_factory=KubernetesConfig, description="Kubernetes config")
    terraform: TerraformConfig = Field(default_factory=TerraformConfig, description="Terraform config")
    
    # Progress tracking and artifacts
    progress_tracking_enabled: bool = Field(default=True, description="Enable progress tracking")
    artifacts_directory: str = Field(default="./artifacts", description="Artifacts storage directory")
    artifacts_s3_bucket: Optional[str] = Field(None, description="S3 bucket for artifacts")
    artifacts_retention_days: int = Field(default=30, description="Artifacts retention in days")
    
    # Notification configuration
    notifications_enabled: bool = Field(default=False, description="Enable notifications")
    notification_channels: List[str] = Field(
        default_factory=list, description="Notification channels (slack, email, sns)"
    )
    slack_webhook_url: Optional[str] = Field(None, description="Slack webhook URL")
    email_recipients: List[str] = Field(default_factory=list, description="Email recipients")
    sns_topic_arn: Optional[str] = Field(None, description="SNS topic ARN")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        valid_envs = ["development", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v.lower()

    @model_validator(mode="after")
    def validate_config_consistency(self):
        """Validate configuration consistency across components."""
        # Ensure S3 bucket is specified if artifacts S3 is enabled
        if self.artifacts_s3_bucket and not self.aws_ai.aws_profile and not self.aws_ai.aws_access_key_id:
            if not os.getenv("AWS_PROFILE") and not os.getenv("AWS_ACCESS_KEY_ID"):
                raise ValueError("AWS credentials required when using S3 for artifacts")
        
        # Ensure CloudWatch log group is specified if CloudWatch logging is enabled
        if self.logging.cloudwatch_enabled and not self.logging.cloudwatch_log_group:
            raise ValueError("CloudWatch log group required when CloudWatch logging is enabled")
        
        # Ensure notification configuration is complete
        if self.notifications_enabled:
            if "slack" in self.notification_channels and not self.slack_webhook_url:
                raise ValueError("Slack webhook URL required when Slack notifications are enabled")
            if "email" in self.notification_channels and not self.email_recipients:
                raise ValueError("Email recipients required when email notifications are enabled")
            if "sns" in self.notification_channels and not self.sns_topic_arn:
                raise ValueError("SNS topic ARN required when SNS notifications are enabled")
        
        return self

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "AgentConfig":
        """
        Load configuration from a YAML file.
        
        Args:
            config_path: Path to the YAML configuration file
            
        Returns:
            AgentConfig instance
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            yaml.YAMLError: If the YAML file is invalid
            ValueError: If the configuration is invalid
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in configuration file: {e}")
        
        if config_data is None:
            config_data = {}
        
        # Create instance with file data, environment variables will override
        return cls(**config_data)

    @classmethod
    def from_ssm(cls, parameter_prefix: str = "/eks-upgrade-agent/", region: str = "us-east-1") -> "AgentConfig":
        """
        Load configuration from AWS Systems Manager Parameter Store.
        
        Args:
            parameter_prefix: SSM parameter prefix
            region: AWS region
            
        Returns:
            AgentConfig instance
            
        Raises:
            NoCredentialsError: If AWS credentials are not available
            ClientError: If SSM parameters cannot be retrieved
        """
        config_data = ConfigUtils.load_from_ssm(parameter_prefix, region)
        return cls(**config_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump()

    def to_yaml(self) -> str:
        """Convert configuration to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    def save_to_file(self, config_path: Union[str, Path]) -> None:
        """
        Save configuration to a YAML file.
        
        Args:
            config_path: Path where to save the configuration file
        """
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(self.to_yaml())

    def save_to_ssm(self, parameter_prefix: str = None, region: str = None) -> None:
        """
        Save configuration to AWS Systems Manager Parameter Store.
        
        Args:
            parameter_prefix: SSM parameter prefix (uses config default if None)
            region: AWS region (uses config default if None)
            
        Raises:
            NoCredentialsError: If AWS credentials are not available
            ClientError: If SSM parameters cannot be saved
        """
        if parameter_prefix is None:
            parameter_prefix = self.security.ssm_parameter_prefix
        if region is None:
            region = self.aws_ai.ssm_region
        
        ConfigUtils.save_to_ssm(self.to_dict(), parameter_prefix, region)

    def get_aws_session(self) -> boto3.Session:
        """
        Create a boto3 session using the configured AWS credentials.
        
        Returns:
            boto3.Session instance
        """
        session_kwargs = {}
        
        if self.aws_ai.aws_profile:
            session_kwargs["profile_name"] = self.aws_ai.aws_profile
        else:
            if self.aws_ai.aws_access_key_id:
                session_kwargs["aws_access_key_id"] = self.aws_ai.aws_access_key_id
            if self.aws_ai.aws_secret_access_key:
                session_kwargs["aws_secret_access_key"] = self.aws_ai.aws_secret_access_key
            if self.aws_ai.aws_session_token:
                session_kwargs["aws_session_token"] = self.aws_ai.aws_session_token
        
        return boto3.Session(**session_kwargs)

    def validate_aws_credentials(self) -> bool:
        """
        Validate AWS credentials by making a test API call.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        return ConfigUtils.validate_aws_credentials(
            self.aws_ai.aws_profile,
            self.aws_ai.aws_access_key_id,
            self.aws_ai.aws_secret_access_key,
            self.aws_ai.aws_session_token
        )

    def get_secret_from_ssm(self, parameter_name: str, region: str = None) -> Optional[str]:
        """
        Retrieve a secret from AWS Systems Manager Parameter Store.
        
        Args:
            parameter_name: Name of the SSM parameter
            region: AWS region (uses config default if None)
            
        Returns:
            Parameter value or None if not found
        """
        if region is None:
            region = self.aws_ai.ssm_region
        
        return ConfigUtils.get_secret_from_ssm(parameter_name, region)

    def __repr__(self) -> str:
        """String representation of the configuration."""
        return f"AgentConfig(agent_name='{self.agent_name}', environment='{self.environment}', version='{self.version}')"