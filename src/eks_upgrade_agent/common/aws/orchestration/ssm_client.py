"""
AWS Systems Manager Parameter Store integration for secure configuration.

This module provides a client for managing configuration parameters
and secrets through AWS Systems Manager Parameter Store.
"""

import json
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from pydantic import BaseModel, Field, field_validator

from ...logging import get_logger
from ...handler import AWSServiceError, ConfigurationError

logger = get_logger(__name__)


class ParameterConfig(BaseModel):
    """Configuration for SSM parameters."""
    
    name: str = Field(..., description="Parameter name")
    value: str = Field(..., description="Parameter value")
    type: str = Field(default="String", description="Parameter type")
    description: str = Field(default="", description="Parameter description")
    key_id: Optional[str] = Field(None, description="KMS key ID for SecureString")
    tier: str = Field(default="Standard", description="Parameter tier")
    policies: Optional[str] = Field(None, description="Parameter policies JSON")
    tags: Dict[str, str] = Field(default_factory=dict, description="Parameter tags")
    
    @field_validator("type")
    @classmethod
    def validate_type(cls, v):
        valid_types = ["String", "StringList", "SecureString"]
        if v not in valid_types:
            raise ValueError(f"Parameter type must be one of: {valid_types}")
        return v
    
    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v):
        valid_tiers = ["Standard", "Advanced", "Intelligent-Tiering"]
        if v not in valid_tiers:
            raise ValueError(f"Parameter tier must be one of: {valid_tiers}")
        return v


class ParameterResult(BaseModel):
    """Result of SSM parameter operations."""
    
    name: str = Field(..., description="Parameter name")
    value: str = Field(..., description="Parameter value")
    type: str = Field(..., description="Parameter type")
    version: int = Field(..., description="Parameter version")
    last_modified_date: datetime = Field(..., description="Last modified date")
    arn: str = Field(..., description="Parameter ARN")
    data_type: str = Field(default="text", description="Parameter data type")


class SSMClient:
    """
    Client for AWS Systems Manager Parameter Store integration.
    
    Manages configuration parameters and secrets with proper encryption
    and access control for the EKS upgrade agent.
    """
    
    def __init__(
        self,
        region: str = "us-east-1",
        parameter_prefix: str = "/eks-upgrade-agent/",
        aws_profile: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None
    ):
        """
        Initialize SSM client.
        
        Args:
            region: AWS region
            parameter_prefix: Prefix for all parameters
            aws_profile: AWS profile name
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            aws_session_token: AWS session token
        """
        self.region = region
        self.parameter_prefix = parameter_prefix.rstrip("/") + "/"
        
        # Create boto3 session
        session_kwargs = {}
        if aws_profile:
            session_kwargs["profile_name"] = aws_profile
        else:
            if aws_access_key_id:
                session_kwargs["aws_access_key_id"] = aws_access_key_id
            if aws_secret_access_key:
                session_kwargs["aws_secret_access_key"] = aws_secret_access_key
            if aws_session_token:
                session_kwargs["aws_session_token"] = aws_session_token
        
        self.session = boto3.Session(**session_kwargs)
        self.client = self.session.client("ssm", region_name=region)
        
        logger.info(f"Initialized SSM client for region: {region}, prefix: {self.parameter_prefix}")
    
    def _get_full_parameter_name(self, name: str) -> str:
        """Get full parameter name with prefix."""
        if name.startswith(self.parameter_prefix):
            return name
        return f"{self.parameter_prefix}{name.lstrip('/')}"
    
    def put_parameter(self, config: ParameterConfig, overwrite: bool = True) -> str:
        """
        Store a parameter in SSM Parameter Store.
        
        Args:
            config: Parameter configuration
            overwrite: Whether to overwrite existing parameter
            
        Returns:
            Parameter version
            
        Raises:
            AWSServiceError: If parameter storage fails
        """
        try:
            full_name = self._get_full_parameter_name(config.name)
            logger.info(f"Storing parameter: {full_name}")
            
            kwargs = {
                "Name": full_name,
                "Value": config.value,
                "Type": config.type,
                "Overwrite": overwrite,
                "Tier": config.tier
            }
            
            if config.description:
                kwargs["Description"] = config.description
            
            if config.type == "SecureString" and config.key_id:
                kwargs["KeyId"] = config.key_id
            
            if config.policies:
                kwargs["Policies"] = config.policies
            
            if config.tags:
                kwargs["Tags"] = [{"Key": k, "Value": v} for k, v in config.tags.items()]
            
            response = self.client.put_parameter(**kwargs)
            
            version = str(response["Version"])
            logger.info(f"Stored parameter {full_name} version {version}")
            
            return version
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to store parameter {config.name}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def get_parameter(self, name: str, with_decryption: bool = True) -> ParameterResult:
        """
        Retrieve a parameter from SSM Parameter Store.
        
        Args:
            name: Parameter name
            with_decryption: Whether to decrypt SecureString parameters
            
        Returns:
            Parameter result
            
        Raises:
            AWSServiceError: If parameter retrieval fails
        """
        try:
            full_name = self._get_full_parameter_name(name)
            logger.debug(f"Retrieving parameter: {full_name}")
            
            response = self.client.get_parameter(
                Name=full_name,
                WithDecryption=with_decryption
            )
            
            parameter = response["Parameter"]
            
            result = ParameterResult(
                name=parameter["Name"],
                value=parameter["Value"],
                type=parameter["Type"],
                version=parameter["Version"],
                last_modified_date=parameter["LastModifiedDate"].replace(tzinfo=UTC),
                arn=parameter["ARN"],
                data_type=parameter.get("DataType", "text")
            )
            
            logger.debug(f"Retrieved parameter {full_name} version {result.version}")
            return result
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ParameterNotFound":
                error_msg = f"Parameter not found: {name}"
                logger.warning(error_msg)
                raise ConfigurationError(error_msg) from e
            else:
                error_msg = f"Failed to retrieve parameter {name}: {e}"
                logger.error(error_msg)
                raise AWSServiceError(error_msg) from e
        except BotoCoreError as e:
            error_msg = f"Failed to retrieve parameter {name}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def get_parameters_by_path(
        self,
        path: str,
        recursive: bool = True,
        with_decryption: bool = True,
        max_results: int = 50
    ) -> List[ParameterResult]:
        """
        Retrieve multiple parameters by path.
        
        Args:
            path: Parameter path
            recursive: Whether to retrieve recursively
            with_decryption: Whether to decrypt SecureString parameters
            max_results: Maximum number of results
            
        Returns:
            List of parameter results
            
        Raises:
            AWSServiceError: If parameter retrieval fails
        """
        try:
            full_path = self._get_full_parameter_name(path)
            logger.debug(f"Retrieving parameters by path: {full_path}")
            
            parameters = []
            next_token = None
            
            while True:
                kwargs = {
                    "Path": full_path,
                    "Recursive": recursive,
                    "WithDecryption": with_decryption,
                    "MaxResults": min(max_results - len(parameters), 10)
                }
                
                if next_token:
                    kwargs["NextToken"] = next_token
                
                response = self.client.get_parameters_by_path(**kwargs)
                
                for parameter in response.get("Parameters", []):
                    result = ParameterResult(
                        name=parameter["Name"],
                        value=parameter["Value"],
                        type=parameter["Type"],
                        version=parameter["Version"],
                        last_modified_date=parameter["LastModifiedDate"].replace(tzinfo=UTC),
                        arn=parameter["ARN"],
                        data_type=parameter.get("DataType", "text")
                    )
                    parameters.append(result)
                
                next_token = response.get("NextToken")
                if not next_token or len(parameters) >= max_results:
                    break
            
            logger.debug(f"Retrieved {len(parameters)} parameters from path {full_path}")
            return parameters
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to retrieve parameters by path {path}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def delete_parameter(self, name: str) -> None:
        """
        Delete a parameter from SSM Parameter Store.
        
        Args:
            name: Parameter name
            
        Raises:
            AWSServiceError: If parameter deletion fails
        """
        try:
            full_name = self._get_full_parameter_name(name)
            logger.info(f"Deleting parameter: {full_name}")
            
            self.client.delete_parameter(Name=full_name)
            
            logger.info(f"Deleted parameter: {full_name}")
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ParameterNotFound":
                logger.warning(f"Parameter not found for deletion: {name}")
            else:
                error_msg = f"Failed to delete parameter {name}: {e}"
                logger.error(error_msg)
                raise AWSServiceError(error_msg) from e
        except BotoCoreError as e:
            error_msg = f"Failed to delete parameter {name}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def delete_parameters(self, names: List[str]) -> Dict[str, str]:
        """
        Delete multiple parameters from SSM Parameter Store.
        
        Args:
            names: List of parameter names
            
        Returns:
            Dictionary of parameter names to deletion status
            
        Raises:
            AWSServiceError: If parameter deletion fails
        """
        try:
            full_names = [self._get_full_parameter_name(name) for name in names]
            logger.info(f"Deleting {len(full_names)} parameters")
            
            response = self.client.delete_parameters(Names=full_names)
            
            results = {}
            
            # Mark successful deletions
            for name in response.get("DeletedParameters", []):
                original_name = name.replace(self.parameter_prefix, "")
                results[original_name] = "deleted"
            
            # Mark failed deletions
            for name in response.get("InvalidParameters", []):
                original_name = name.replace(self.parameter_prefix, "")
                results[original_name] = "not_found"
            
            logger.info(f"Deleted {len(response.get('DeletedParameters', []))} parameters")
            
            return results
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to delete parameters: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def put_configuration(self, config_dict: Dict[str, Any], config_name: str = "config") -> Dict[str, str]:
        """
        Store a configuration dictionary as parameters.
        
        Args:
            config_dict: Configuration dictionary
            config_name: Configuration name prefix
            
        Returns:
            Dictionary of parameter names to versions
            
        Raises:
            AWSServiceError: If configuration storage fails
        """
        try:
            logger.info(f"Storing configuration: {config_name}")
            
            results = {}
            
            def store_nested_config(data: Dict[str, Any], prefix: str = ""):
                for key, value in data.items():
                    param_name = f"{config_name}/{prefix}{key}" if prefix else f"{config_name}/{key}"
                    
                    if isinstance(value, dict):
                        # Recursively store nested dictionaries
                        store_nested_config(value, f"{prefix}{key}/")
                    else:
                        # Determine parameter type based on key name
                        param_type = "SecureString" if any(
                            sensitive in key.lower() 
                            for sensitive in ["password", "secret", "key", "token", "credential"]
                        ) else "String"
                        
                        # Convert value to string
                        if isinstance(value, (dict, list)):
                            param_value = json.dumps(value)
                        else:
                            param_value = str(value)
                        
                        config = ParameterConfig(
                            name=param_name,
                            value=param_value,
                            type=param_type,
                            description=f"Configuration parameter for {config_name}",
                            tags={"ConfigName": config_name, "Component": "eks-upgrade-agent"}
                        )
                        
                        version = self.put_parameter(config)
                        results[param_name] = version
            
            store_nested_config(config_dict)
            
            logger.info(f"Stored {len(results)} configuration parameters for {config_name}")
            return results
            
        except Exception as e:
            error_msg = f"Failed to store configuration {config_name}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def get_configuration(self, config_name: str) -> Dict[str, Any]:
        """
        Retrieve a configuration dictionary from parameters.
        
        Args:
            config_name: Configuration name prefix
            
        Returns:
            Configuration dictionary
            
        Raises:
            AWSServiceError: If configuration retrieval fails
        """
        try:
            logger.info(f"Retrieving configuration: {config_name}")
            
            parameters = self.get_parameters_by_path(f"{config_name}/", recursive=True)
            
            config_dict = {}
            
            for param in parameters:
                # Remove prefix and config name from parameter name
                key_path = param.name.replace(self.parameter_prefix, "").replace(f"{config_name}/", "")
                
                # Parse JSON values if they look like JSON
                value = param.value
                if value.startswith(("{", "[")):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass  # Keep as string if not valid JSON
                
                # Build nested dictionary
                keys = key_path.split("/")
                current_dict = config_dict
                
                for key in keys[:-1]:
                    if key not in current_dict:
                        current_dict[key] = {}
                    current_dict = current_dict[key]
                
                current_dict[keys[-1]] = value
            
            logger.info(f"Retrieved configuration {config_name} with {len(parameters)} parameters")
            return config_dict
            
        except Exception as e:
            error_msg = f"Failed to retrieve configuration {config_name}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def list_parameters(
        self,
        path_prefix: Optional[str] = None,
        parameter_filters: Optional[List[Dict[str, Any]]] = None,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List parameters with optional filtering.
        
        Args:
            path_prefix: Optional path prefix filter
            parameter_filters: Optional parameter filters
            max_results: Maximum number of results
            
        Returns:
            List of parameter metadata
            
        Raises:
            AWSServiceError: If parameter listing fails
        """
        try:
            logger.debug("Listing parameters")
            
            parameters = []
            next_token = None
            
            while True:
                kwargs = {"MaxResults": min(max_results - len(parameters), 50)}
                
                if path_prefix:
                    full_prefix = self._get_full_parameter_name(path_prefix)
                    kwargs["ParameterFilters"] = [
                        {"Key": "Name", "Option": "BeginsWith", "Values": [full_prefix]}
                    ]
                
                if parameter_filters:
                    if "ParameterFilters" not in kwargs:
                        kwargs["ParameterFilters"] = []
                    kwargs["ParameterFilters"].extend(parameter_filters)
                
                if next_token:
                    kwargs["NextToken"] = next_token
                
                response = self.client.describe_parameters(**kwargs)
                
                parameters.extend(response.get("Parameters", []))
                
                next_token = response.get("NextToken")
                if not next_token or len(parameters) >= max_results:
                    break
            
            logger.debug(f"Listed {len(parameters)} parameters")
            return parameters
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to list parameters: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e


def create_default_agent_config() -> Dict[str, Any]:
    """
    Create default configuration for the EKS upgrade agent.
    
    Returns:
        Default configuration dictionary
    """
    return {
        "agent": {
            "name": "eks-upgrade-agent",
            "version": "1.0.0",
            "log_level": "INFO",
            "max_concurrent_upgrades": 1
        },
        "aws": {
            "region": "us-east-1",
            "bedrock": {
                "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
                "max_tokens": 4000,
                "temperature": 0.1
            },
            "comprehend": {
                "endpoint": None,
                "max_batch_size": 25
            },
            "step_functions": {
                "state_machine_name": "eks-upgrade-workflow",
                "execution_timeout": 3600
            },
            "eventbridge": {
                "bus_name": "default",
                "rule_prefix": "eks-upgrade"
            }
        },
        "upgrade": {
            "strategy": "blue_green",
            "traffic_shift_intervals": [10, 25, 50, 75, 100],
            "validation_timeout": 300,
            "rollback_timeout": 600
        },
        "security": {
            "kms_key_id": None,
            "encrypt_parameters": True,
            "audit_logging": True
        }
    }