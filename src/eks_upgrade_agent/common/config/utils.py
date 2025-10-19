"""
Configuration utility functions for the EKS Upgrade Agent.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Any, Dict, Optional


class ConfigUtils:
    """Utility functions for configuration management."""
    
    @staticmethod
    def flatten_to_nested(flat_dict: Dict[str, Any]) -> Dict[str, Any]:
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

    @staticmethod
    def nested_to_flat(nested_dict: Dict[str, Any], parent_key: str = "", sep: str = "/") -> Dict[str, Any]:
        """Convert nested dict to flat dot-notation dict."""
        items = []
        for k, v in nested_dict.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(ConfigUtils.nested_to_flat(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def load_from_ssm(parameter_prefix: str = "/eks-upgrade-agent/", region: str = "us-east-1") -> Dict[str, Any]:
        """
        Load configuration from AWS Systems Manager Parameter Store.
        
        Args:
            parameter_prefix: SSM parameter prefix
            region: AWS region
            
        Returns:
            Configuration dictionary
            
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
            return ConfigUtils.flatten_to_nested(parameters)
            
        except NoCredentialsError:
            raise NoCredentialsError("AWS credentials not found. Configure credentials to use SSM parameters.")
        except ClientError as e:
            raise ClientError(f"Failed to retrieve SSM parameters: {e}")

    @staticmethod
    def save_to_ssm(config_dict: Dict[str, Any], parameter_prefix: str = "/eks-upgrade-agent/", region: str = "us-east-1") -> None:
        """
        Save configuration to AWS Systems Manager Parameter Store.
        
        Args:
            config_dict: Configuration dictionary to save
            parameter_prefix: SSM parameter prefix
            region: AWS region
            
        Raises:
            NoCredentialsError: If AWS credentials are not available
            ClientError: If SSM parameters cannot be saved
        """
        try:
            ssm_client = boto3.client("ssm", region_name=region)
            
            # Convert config to flat parameter structure
            flat_params = ConfigUtils.nested_to_flat(config_dict)
            
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
    def get_secret_from_ssm(parameter_name: str, region: str = "us-east-1") -> Optional[str]:
        """
        Retrieve a secret from AWS Systems Manager Parameter Store.
        
        Args:
            parameter_name: Name of the SSM parameter
            region: AWS region
            
        Returns:
            Parameter value or None if not found
        """
        try:
            ssm_client = boto3.client("ssm", region_name=region)
            
            response = ssm_client.get_parameter(
                Name=parameter_name,
                WithDecryption=True
            )
            return response["Parameter"]["Value"]
            
        except ClientError as e:
            if e.response["Error"]["Code"] == "ParameterNotFound":
                return None
            raise

    @staticmethod
    def validate_aws_credentials(aws_profile: Optional[str] = None, 
                               aws_access_key_id: Optional[str] = None,
                               aws_secret_access_key: Optional[str] = None,
                               aws_session_token: Optional[str] = None) -> bool:
        """
        Validate AWS credentials by making a test API call.
        
        Args:
            aws_profile: AWS profile name
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            aws_session_token: AWS session token
            
        Returns:
            True if credentials are valid, False otherwise
        """
        try:
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
            
            session = boto3.Session(**session_kwargs)
            sts_client = session.client("sts")
            sts_client.get_caller_identity()
            return True
        except Exception:
            return False