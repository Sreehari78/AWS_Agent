"""Tests for SSM Parameter Store integration."""

import json
import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError, BotoCoreError

from src.eks_upgrade_agent.common.aws.orchestration.ssm_client import (
    SSMClient,
    ParameterConfig,
    ParameterResult,
    create_default_agent_config
)
from src.eks_upgrade_agent.common.handler import AWSServiceError, ConfigurationError


class TestParameterConfig:
    """Test ParameterConfig model."""
    
    def test_valid_config(self):
        """Test valid parameter configuration."""
        config = ParameterConfig(
            name="test-param",
            value="test-value",
            type="String",
            description="Test parameter"
        )
        
        assert config.name == "test-param"
        assert config.value == "test-value"
        assert config.type == "String"
        assert config.tier == "Standard"
        assert config.tags == {}
    
    def test_invalid_type(self):
        """Test invalid parameter type validation."""
        with pytest.raises(ValueError, match="Parameter type must be one of"):
            ParameterConfig(
                name="test-param",
                value="test-value",
                type="InvalidType"
            )
    
    def test_invalid_tier(self):
        """Test invalid parameter tier validation."""
        with pytest.raises(ValueError, match="Parameter tier must be one of"):
            ParameterConfig(
                name="test-param",
                value="test-value",
                tier="InvalidTier"
            )
    
    def test_valid_types(self):
        """Test all valid parameter types."""
        valid_types = ["String", "StringList", "SecureString"]
        
        for param_type in valid_types:
            config = ParameterConfig(
                name="test-param",
                value="test-value",
                type=param_type
            )
            assert config.type == param_type
    
    def test_valid_tiers(self):
        """Test all valid parameter tiers."""
        valid_tiers = ["Standard", "Advanced", "Intelligent-Tiering"]
        
        for tier in valid_tiers:
            config = ParameterConfig(
                name="test-param",
                value="test-value",
                tier=tier
            )
            assert config.tier == tier


class TestSSMClient:
    """Test SSMClient."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock boto3 SSM client."""
        with patch('boto3.Session') as mock_session:
            mock_ssm_client = Mock()
            mock_session.return_value.client.return_value = mock_ssm_client
            
            client = SSMClient(
                region="us-east-1",
                parameter_prefix="/test-agent/"
            )
            client.client = mock_ssm_client
            
            yield client, mock_ssm_client
    
    def test_initialization(self):
        """Test client initialization."""
        with patch('boto3.Session') as mock_session:
            mock_ssm_client = Mock()
            mock_session.return_value.client.return_value = mock_ssm_client
            
            client = SSMClient(
                region="us-west-2",
                parameter_prefix="/custom-prefix/",
                aws_access_key_id="test-key"
            )
            
            assert client.region == "us-west-2"
            assert client.parameter_prefix == "/custom-prefix/"
    
    def test_get_full_parameter_name(self, mock_client):
        """Test parameter name prefixing."""
        client, _ = mock_client
        
        # Test with relative name
        full_name = client._get_full_parameter_name("config/database")
        assert full_name == "/test-agent/config/database"
        
        # Test with already prefixed name
        full_name = client._get_full_parameter_name("/test-agent/config/database")
        assert full_name == "/test-agent/config/database"
        
        # Test with leading slash
        full_name = client._get_full_parameter_name("/config/database")
        assert full_name == "/test-agent/config/database"
    
    def test_put_parameter_success(self, mock_client):
        """Test successful parameter storage."""
        client, mock_ssm_client = mock_client
        
        config = ParameterConfig(
            name="test-param",
            value="test-value",
            type="String",
            description="Test parameter",
            tags={"Environment": "test"}
        )
        
        mock_ssm_client.put_parameter.return_value = {"Version": 1}
        
        result = client.put_parameter(config)
        
        assert result == "1"
        mock_ssm_client.put_parameter.assert_called_once()
        
        # Verify call arguments
        call_args = mock_ssm_client.put_parameter.call_args[1]
        assert call_args["Name"] == "/test-agent/test-param"
        assert call_args["Value"] == "test-value"
        assert call_args["Type"] == "String"
        assert call_args["Description"] == "Test parameter"
        assert call_args["Overwrite"] is True
        assert call_args["Tags"] == [{"Key": "Environment", "Value": "test"}]
    
    def test_put_parameter_secure_string(self, mock_client):
        """Test storing SecureString parameter."""
        client, mock_ssm_client = mock_client
        
        config = ParameterConfig(
            name="secret-param",
            value="secret-value",
            type="SecureString",
            key_id="alias/test-key"
        )
        
        mock_ssm_client.put_parameter.return_value = {"Version": 1}
        
        client.put_parameter(config)
        
        # Verify KMS key is included for SecureString
        call_args = mock_ssm_client.put_parameter.call_args[1]
        assert call_args["Type"] == "SecureString"
        assert call_args["KeyId"] == "alias/test-key"
    
    def test_put_parameter_failure(self, mock_client):
        """Test parameter storage failure."""
        client, mock_ssm_client = mock_client
        
        config = ParameterConfig(name="test-param", value="test-value")
        
        mock_ssm_client.put_parameter.side_effect = ClientError(
            {"Error": {"Code": "ParameterLimitExceeded", "Message": "Too many parameters"}},
            "PutParameter"
        )
        
        with pytest.raises(AWSServiceError, match="Failed to store parameter"):
            client.put_parameter(config)
    
    def test_get_parameter_success(self, mock_client):
        """Test successful parameter retrieval."""
        client, mock_ssm_client = mock_client
        
        mock_ssm_client.get_parameter.return_value = {
            "Parameter": {
                "Name": "/test-agent/test-param",
                "Value": "test-value",
                "Type": "String",
                "Version": 1,
                "LastModifiedDate": datetime.now(UTC),
                "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/test-agent/test-param",
                "DataType": "text"
            }
        }
        
        result = client.get_parameter("test-param")
        
        assert isinstance(result, ParameterResult)
        assert result.name == "/test-agent/test-param"
        assert result.value == "test-value"
        assert result.type == "String"
        assert result.version == 1
    
    def test_get_parameter_not_found(self, mock_client):
        """Test parameter not found error."""
        client, mock_ssm_client = mock_client
        
        mock_ssm_client.get_parameter.side_effect = ClientError(
            {"Error": {"Code": "ParameterNotFound", "Message": "Parameter not found"}},
            "GetParameter"
        )
        
        with pytest.raises(ConfigurationError, match="Parameter not found"):
            client.get_parameter("nonexistent-param")
    
    def test_get_parameters_by_path_success(self, mock_client):
        """Test successful parameters by path retrieval."""
        client, mock_ssm_client = mock_client
        
        mock_ssm_client.get_parameters_by_path.return_value = {
            "Parameters": [
                {
                    "Name": "/test-agent/config/database/host",
                    "Value": "localhost",
                    "Type": "String",
                    "Version": 1,
                    "LastModifiedDate": datetime.now(UTC),
                    "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/test-agent/config/database/host"
                },
                {
                    "Name": "/test-agent/config/database/port",
                    "Value": "5432",
                    "Type": "String",
                    "Version": 1,
                    "LastModifiedDate": datetime.now(UTC),
                    "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/test-agent/config/database/port"
                }
            ]
        }
        
        result = client.get_parameters_by_path("config/database")
        
        assert len(result) == 2
        assert all(isinstance(param, ParameterResult) for param in result)
        assert result[0].value == "localhost"
        assert result[1].value == "5432"
    
    def test_delete_parameter_success(self, mock_client):
        """Test successful parameter deletion."""
        client, mock_ssm_client = mock_client
        
        client.delete_parameter("test-param")
        
        mock_ssm_client.delete_parameter.assert_called_once_with(
            Name="/test-agent/test-param"
        )
    
    def test_delete_parameter_not_found(self, mock_client):
        """Test deleting non-existent parameter."""
        client, mock_ssm_client = mock_client
        
        mock_ssm_client.delete_parameter.side_effect = ClientError(
            {"Error": {"Code": "ParameterNotFound", "Message": "Parameter not found"}},
            "DeleteParameter"
        )
        
        # Should not raise exception for not found
        client.delete_parameter("nonexistent-param")
    
    def test_delete_parameters_success(self, mock_client):
        """Test successful multiple parameter deletion."""
        client, mock_ssm_client = mock_client
        
        mock_ssm_client.delete_parameters.return_value = {
            "DeletedParameters": ["/test-agent/param1", "/test-agent/param2"],
            "InvalidParameters": ["/test-agent/param3"]
        }
        
        result = client.delete_parameters(["param1", "param2", "param3"])
        
        assert result["param1"] == "deleted"
        assert result["param2"] == "deleted"
        assert result["param3"] == "not_found"
    
    def test_put_configuration_success(self, mock_client):
        """Test successful configuration storage."""
        client, mock_ssm_client = mock_client
        
        config_dict = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "password": "secret123"
            },
            "api": {
                "timeout": 30,
                "retries": 3
            }
        }
        
        mock_ssm_client.put_parameter.return_value = {"Version": 1}
        
        result = client.put_configuration(config_dict, "app-config")
        
        # Should create parameters for each config value
        assert len(result) == 5  # host, port, password, timeout, retries
        assert "app-config/database/host" in result
        assert "app-config/database/password" in result
        
        # Verify password is stored as SecureString
        calls = mock_ssm_client.put_parameter.call_args_list
        password_call = next(call for call in calls if "password" in call[1]["Name"])
        assert password_call[1]["Type"] == "SecureString"
    
    def test_get_configuration_success(self, mock_client):
        """Test successful configuration retrieval."""
        client, mock_ssm_client = mock_client
        
        mock_ssm_client.get_parameters_by_path.return_value = {
            "Parameters": [
                {
                    "Name": "/test-agent/app-config/database/host",
                    "Value": "localhost",
                    "Type": "String",
                    "Version": 1,
                    "LastModifiedDate": datetime.now(UTC),
                    "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/test-agent/app-config/database/host"
                },
                {
                    "Name": "/test-agent/app-config/database/port",
                    "Value": "5432",
                    "Type": "String",
                    "Version": 1,
                    "LastModifiedDate": datetime.now(UTC),
                    "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/test-agent/app-config/database/port"
                },
                {
                    "Name": "/test-agent/app-config/features",
                    "Value": '["feature1", "feature2"]',
                    "Type": "String",
                    "Version": 1,
                    "LastModifiedDate": datetime.now(UTC),
                    "ARN": "arn:aws:ssm:us-east-1:123456789012:parameter/test-agent/app-config/features"
                }
            ]
        }
        
        result = client.get_configuration("app-config")
        
        assert result["database"]["host"] == "localhost"
        assert result["database"]["port"] == "5432"
        assert result["features"] == ["feature1", "feature2"]  # JSON parsed
    
    def test_list_parameters_success(self, mock_client):
        """Test successful parameter listing."""
        client, mock_ssm_client = mock_client
        
        mock_ssm_client.describe_parameters.return_value = {
            "Parameters": [
                {"Name": "/test-agent/param1", "Type": "String"},
                {"Name": "/test-agent/param2", "Type": "SecureString"}
            ]
        }
        
        result = client.list_parameters("config/")
        
        assert len(result) == 2
        assert result[0]["Name"] == "/test-agent/param1"
        assert result[1]["Type"] == "SecureString"


class TestDefaultAgentConfig:
    """Test default agent configuration creation."""
    
    def test_create_default_agent_config(self):
        """Test creating default agent configuration."""
        config = create_default_agent_config()
        
        # Verify main sections exist
        assert "agent" in config
        assert "aws" in config
        assert "upgrade" in config
        assert "security" in config
        
        # Verify agent configuration
        assert config["agent"]["name"] == "eks-upgrade-agent"
        assert config["agent"]["version"] == "1.0.0"
        assert config["agent"]["log_level"] == "INFO"
        
        # Verify AWS configuration
        aws_config = config["aws"]
        assert aws_config["region"] == "us-east-1"
        assert "bedrock" in aws_config
        assert "comprehend" in aws_config
        assert "step_functions" in aws_config
        assert "eventbridge" in aws_config
        
        # Verify Bedrock configuration
        bedrock_config = aws_config["bedrock"]
        assert "anthropic.claude-3-sonnet" in bedrock_config["model_id"]
        assert bedrock_config["max_tokens"] == 4000
        assert bedrock_config["temperature"] == 0.1
        
        # Verify upgrade configuration
        upgrade_config = config["upgrade"]
        assert upgrade_config["strategy"] == "blue_green"
        assert upgrade_config["traffic_shift_intervals"] == [10, 25, 50, 75, 100]
        
        # Verify security configuration
        security_config = config["security"]
        assert security_config["encrypt_parameters"] is True
        assert security_config["audit_logging"] is True