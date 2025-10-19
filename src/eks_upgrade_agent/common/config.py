"""
Configuration management system for the EKS Upgrade Agent.

This module provides comprehensive configuration management including:
- YAML configuration file parsing and validation
- AWS AI services configuration support (Bedrock, Comprehend, Step Functions)
- Environment variable overrides and validation
- Secure credential handling integration with AWS Systems Manager
- Pydantic-based validation and type safety
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models.aws_ai import AWSAIConfig


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


class SecurityConfig(BaseModel):
    """Security configuration."""
    
    use_ssm_parameters: bool = Field(default=True, description="Use AWS SSM for secrets")
    ssm_parameter_prefix: str = Field(
        default="/eks-upgrade-agent/",
        description="SSM parameter prefix"
    )
    encrypt_sensitive_data: bool = Field(default=True, description="Encrypt sensitive data")
    kms_key_id: Optional[str] = Field(None, description="KMS key ID for encryption")
    credential_rotation_enabled: bool = Field(
        default=False, description="Enable credential rotation"
    )
    credential_rotation_interval_hours: int = Field(
        default=24, description="Credential rotation interval in hours"
    )


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


class KubernetesConfig(BaseModel):
    """Kubernetes configuration."""
    
    kubeconfig_path: Optional[str] = Field(None, description="Path to kubeconfig file")
    context: Optional[str] = Field(None, description="Kubernetes context to use")
    namespace: str = Field(default="default", description="Default namespace")
    timeout_seconds: int = Field(default=300, description="Kubernetes API timeout")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")


class TerraformConfig(BaseModel):
    """Terraform configuration."""
    
    binary_path: str = Field(default="terraform", description="Path to terraform binary")
    working_directory: str = Field(default="./terraform", description="Terraform working directory")
    state_backend: str = Field(default="s3", description="Terraform state backend")
    state_bucket: Optional[str] = Field(None, description="S3 bucket for state")
    state_key_prefix: str = Field(
        default="eks-upgrade-agent/", description="S3 key prefix for state"
    )
    state_region: str = Field(default="us-east-1", description="AWS region for state")
    lock_table: Optional[str] = Field(None, description="DynamoDB table for state locking")
    auto_approve: bool = Field(default=False, description="Auto-approve terraform apply")
    parallelism: int = Field(default=10, description="Terraform parallelism")


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
        try:
            ssm_client = boto3.client("ssm", region_name=region)
            
            # Get all parameters with the specified prefix
            paginator = ssm_client.get_paginator("get_parameters_by_path")
            parameters = {}
            
            for page in paginator.paginate(
                Path=parameter_prefix,
                Recursive=True,
                WithDecryption=True
            ):
                for param in page["Parameters"]:
                    # Convert parameter name to config key
                    key = param["Name"].replace(parameter_prefix, "").replace("/", ".")
                    parameters[key] = param["Value"]
            
            # Convert flat parameter structure to nested dict
            config_data = cls._flatten_to_nested(parameters)
            
            return cls(**config_data)
            
        except NoCredentialsError:
            raise NoCredentialsError("AWS credentials not found. Configure credentials to use SSM parameters.")
        except ClientError as e:
            raise ClientError(f"Failed to retrieve SSM parameters: {e}")

    @staticmethod
    def _flatten_to_nested(flat_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert flat dot-notation dict to nested dict."""
        nested = {}
        for key, value in flat_dict.items():
            keys = key.split(".")
            current = nested
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value
        return nested

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
        
        try:
            ssm_client = boto3.client("ssm", region_name=region)
            
            # Convert config to flat parameter structure
            flat_params = self._nested_to_flat(self.to_dict())
            
            # Save each parameter
            for key, value in flat_params.items():
                parameter_name = f"{parameter_prefix.rstrip('/')}/{key}"
                
                # Determine if parameter should be encrypted
                is_sensitive = any(sensitive_key in key.lower() for sensitive_key in [
                    "password", "secret", "key", "token", "credential"
                ])
                
                ssm_client.put_parameter(
                    Name=parameter_name,
                    Value=str(value),
                    Type="SecureString" if is_sensitive else "String",
                    Overwrite=True,
                    Description=f"EKS Upgrade Agent configuration: {key}"
                )
                
        except NoCredentialsError:
            raise NoCredentialsError("AWS credentials not found. Configure credentials to save SSM parameters.")
        except ClientError as e:
            raise ClientError(f"Failed to save SSM parameters: {e}")

    @staticmethod
    def _nested_to_flat(nested_dict: Dict[str, Any], parent_key: str = "", sep: str = "/") -> Dict[str, Any]:
        """Convert nested dict to flat dot-notation dict."""
        items = []
        for k, v in nested_dict.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(AgentConfig._nested_to_flat(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

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
        try:
            session = self.get_aws_session()
            sts_client = session.client("sts")
            sts_client.get_caller_identity()
            return True
        except Exception:
            return False

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
        
        try:
            session = self.get_aws_session()
            ssm_client = session.client("ssm", region_name=region)
            
            response = ssm_client.get_parameter(
                Name=parameter_name,
                WithDecryption=True
            )
            return response["Parameter"]["Value"]
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ParameterNotFound":
                return None
            raise

    def __repr__(self) -> str:
        """String representation of the configuration."""
        return f"AgentConfig(agent_name='{self.agent_name}', environment='{self.environment}', version='{self.version}')"