"""Tests for Lambda function templates."""

import json
import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from botocore.exceptions import ClientError, BotoCoreError

from src.eks_upgrade_agent.common.aws.orchestration.lambda_templates import (
    LambdaTemplateManager,
    LambdaFunction,
    LambdaDeployment,
    create_perception_lambda,
    create_reasoning_lambda,
    create_execution_lambda,
    create_validation_lambda,
    create_rollback_lambda,
    get_all_lambda_templates
)
from src.eks_upgrade_agent.common.handler import AWSServiceError


class TestLambdaFunction:
    """Test LambdaFunction model."""
    
    def test_valid_function(self):
        """Test valid Lambda function configuration."""
        function = LambdaFunction(
            function_name="test-function",
            description="Test function",
            handler="lambda_function.lambda_handler",
            role_arn="arn:aws:iam::123456789012:role/test-role",
            code="def lambda_handler(event, context): return {'statusCode': 200}"
        )
        
        assert function.function_name == "test-function"
        assert function.runtime == "python3.12"
        assert function.timeout == 300
        assert function.memory_size == 512
        assert function.environment_variables == {}
    
    def test_invalid_runtime(self):
        """Test invalid runtime validation."""
        with pytest.raises(ValueError, match="Runtime must be one of"):
            LambdaFunction(
                function_name="test-function",
                description="Test function",
                handler="lambda_function.lambda_handler",
                role_arn="arn:aws:iam::123456789012:role/test-role",
                code="test code",
                runtime="invalid-runtime"
            )
    
    def test_invalid_timeout(self):
        """Test invalid timeout validation."""
        with pytest.raises(ValueError, match="Timeout must be between 1 and 900 seconds"):
            LambdaFunction(
                function_name="test-function",
                description="Test function",
                handler="lambda_function.lambda_handler",
                role_arn="arn:aws:iam::123456789012:role/test-role",
                code="test code",
                timeout=1000
            )
    
    def test_invalid_memory_size(self):
        """Test invalid memory size validation."""
        with pytest.raises(ValueError, match="Memory size must be between 128 and 10240 MB"):
            LambdaFunction(
                function_name="test-function",
                description="Test function",
                handler="lambda_function.lambda_handler",
                role_arn="arn:aws:iam::123456789012:role/test-role",
                code="test code",
                memory_size=100
            )
    
    def test_valid_runtimes(self):
        """Test all valid runtimes."""
        valid_runtimes = [
            "python3.8", "python3.9", "python3.10", "python3.11", "python3.12",
            "nodejs18.x", "nodejs20.x", "java11", "java17", "java21",
            "dotnet6", "dotnet8", "go1.x", "ruby3.2", "provided.al2023"
        ]
        
        for runtime in valid_runtimes:
            function = LambdaFunction(
                function_name="test-function",
                description="Test function",
                handler="lambda_function.lambda_handler",
                role_arn="arn:aws:iam::123456789012:role/test-role",
                code="test code",
                runtime=runtime
            )
            assert function.runtime == runtime


class TestLambdaTemplateManager:
    """Test LambdaTemplateManager."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock boto3 Lambda client."""
        with patch('boto3.Session') as mock_session:
            mock_lambda_client = Mock()
            mock_session.return_value.client.return_value = mock_lambda_client
            
            manager = LambdaTemplateManager(region="us-east-1")
            manager.lambda_client = mock_lambda_client
            
            yield manager, mock_lambda_client
    
    def test_initialization(self):
        """Test manager initialization."""
        with patch('boto3.Session') as mock_session:
            mock_lambda_client = Mock()
            mock_session.return_value.client.return_value = mock_lambda_client
            
            manager = LambdaTemplateManager(
                region="us-west-2",
                aws_access_key_id="test-key"
            )
            
            assert manager.region == "us-west-2"
    
    def test_create_function_zip(self, mock_client):
        """Test creating function zip file."""
        manager, _ = mock_client
        
        code_content = "def lambda_handler(event, context): return {'statusCode': 200}"
        requirements = ["boto3==1.26.0", "requests==2.28.0"]
        
        zip_content = manager.create_function_zip(code_content, requirements)
        
        assert isinstance(zip_content, bytes)
        assert len(zip_content) > 0
        
        # Verify zip content by reading it back
        import zipfile
        with zipfile.ZipFile(BytesIO(zip_content), 'r') as zip_file:
            files = zip_file.namelist()
            assert "lambda_function.py" in files
            assert "requirements.txt" in files
            
            # Verify file contents
            lambda_code = zip_file.read("lambda_function.py").decode()
            assert "lambda_handler" in lambda_code
            
            requirements_content = zip_file.read("requirements.txt").decode()
            assert "boto3==1.26.0" in requirements_content
            assert "requests==2.28.0" in requirements_content
    
    def test_deploy_function_success(self, mock_client):
        """Test successful function deployment."""
        manager, mock_lambda_client = mock_client
        
        function_config = LambdaFunction(
            function_name="test-function",
            description="Test function",
            handler="lambda_function.lambda_handler",
            role_arn="arn:aws:iam::123456789012:role/test-role",
            code="def lambda_handler(event, context): return {'statusCode': 200}",
            environment_variables={"LOG_LEVEL": "INFO"},
            tags={"Environment": "test"}
        )
        
        mock_lambda_client.create_function.return_value = {
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:test-function",
            "FunctionName": "test-function",
            "Version": "1",
            "LastModified": "2024-01-01T00:00:00.000+0000",
            "CodeSha256": "abc123",
            "State": "Active"
        }
        
        result = manager.deploy_function(function_config)
        
        assert isinstance(result, LambdaDeployment)
        assert result.function_name == "test-function"
        assert result.version == "1"
        assert result.state == "Active"
        
        # Verify function creation call
        mock_lambda_client.create_function.assert_called_once()
        call_args = mock_lambda_client.create_function.call_args[1]
        assert call_args["FunctionName"] == "test-function"
        assert call_args["Runtime"] == "python3.12"
        assert call_args["Environment"]["Variables"]["LOG_LEVEL"] == "INFO"
        assert call_args["Tags"]["Environment"] == "test"
    
    def test_deploy_function_already_exists(self, mock_client):
        """Test deploying function that already exists."""
        manager, mock_lambda_client = mock_client
        
        function_config = LambdaFunction(
            function_name="existing-function",
            description="Existing function",
            handler="lambda_function.lambda_handler",
            role_arn="arn:aws:iam::123456789012:role/test-role",
            code="def lambda_handler(event, context): return {'statusCode': 200}"
        )
        
        # Mock function already exists error
        mock_lambda_client.create_function.side_effect = ClientError(
            {"Error": {"Code": "ResourceConflictException", "Message": "Function already exists"}},
            "CreateFunction"
        )
        
        # Mock update function responses
        mock_lambda_client.update_function_code.return_value = {
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:existing-function",
            "Version": "2",
            "CodeSha256": "def456"
        }
        
        mock_lambda_client.update_function_configuration.return_value = {
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:existing-function",
            "FunctionName": "existing-function",
            "LastModified": "2024-01-01T00:00:00.000+0000",
            "State": "Active"
        }
        
        result = manager.deploy_function(function_config)
        
        assert isinstance(result, LambdaDeployment)
        assert result.function_name == "existing-function"
        assert result.version == "2"
        
        # Verify update calls were made
        mock_lambda_client.update_function_code.assert_called_once()
        mock_lambda_client.update_function_configuration.assert_called_once()
    
    def test_deploy_function_failure(self, mock_client):
        """Test function deployment failure."""
        manager, mock_lambda_client = mock_client
        
        function_config = LambdaFunction(
            function_name="test-function",
            description="Test function",
            handler="lambda_function.lambda_handler",
            role_arn="arn:aws:iam::123456789012:role/invalid-role",
            code="def lambda_handler(event, context): return {'statusCode': 200}"
        )
        
        mock_lambda_client.create_function.side_effect = ClientError(
            {"Error": {"Code": "InvalidParameterValueException", "Message": "Invalid role"}},
            "CreateFunction"
        )
        
        with pytest.raises(AWSServiceError, match="Failed to deploy function"):
            manager.deploy_function(function_config)
    
    def test_invoke_function_success(self, mock_client):
        """Test successful function invocation."""
        manager, mock_lambda_client = mock_client
        
        # Mock successful invocation response
        mock_response = Mock()
        mock_response.read.return_value = b'{"result": "success"}'
        
        mock_lambda_client.invoke.return_value = {
            "StatusCode": 200,
            "ExecutedVersion": "1",
            "LogResult": "base64-encoded-logs",
            "Payload": mock_response
        }
        
        payload = {"cluster_name": "test-cluster", "target_version": "1.29"}
        result = manager.invoke_function("test-function", payload)
        
        assert result["status_code"] == 200
        assert result["execution_result"] == "1"
        assert result["payload"] == {"result": "success"}
        
        # Verify invocation call
        mock_lambda_client.invoke.assert_called_once_with(
            FunctionName="test-function",
            InvocationType="RequestResponse",
            Payload=json.dumps(payload)
        )
    
    def test_invoke_function_async(self, mock_client):
        """Test asynchronous function invocation."""
        manager, mock_lambda_client = mock_client
        
        mock_lambda_client.invoke.return_value = {
            "StatusCode": 202,
            "ExecutedVersion": "1"
        }
        
        payload = {"cluster_name": "test-cluster"}
        result = manager.invoke_function("test-function", payload, "Event")
        
        assert result["status_code"] == 202
        assert result["payload"] is None
        
        # Verify async invocation
        call_args = mock_lambda_client.invoke.call_args[1]
        assert call_args["InvocationType"] == "Event"
    
    def test_delete_function_success(self, mock_client):
        """Test successful function deletion."""
        manager, mock_lambda_client = mock_client
        
        manager.delete_function("test-function")
        
        mock_lambda_client.delete_function.assert_called_once_with(
            FunctionName="test-function"
        )
    
    def test_list_functions_success(self, mock_client):
        """Test successful function listing."""
        manager, mock_lambda_client = mock_client
        
        mock_lambda_client.list_functions.return_value = {
            "Functions": [
                {"FunctionName": "function1", "Runtime": "python3.12"},
                {"FunctionName": "function2", "Runtime": "nodejs18.x"}
            ]
        }
        
        result = manager.list_functions()
        
        assert len(result) == 2
        assert result[0]["FunctionName"] == "function1"
        assert result[1]["Runtime"] == "nodejs18.x"


class TestLambdaTemplateCreators:
    """Test Lambda template creator functions."""
    
    def test_create_perception_lambda(self):
        """Test creating perception Lambda template."""
        function = create_perception_lambda()
        
        assert function.function_name == "eks-upgrade-agent-perception"
        assert "Perception Phase" in function.description
        assert function.handler == "lambda_function.lambda_handler"
        assert function.timeout == 300
        assert function.memory_size == 512
        assert "perception" in function.tags["Phase"]
        
        # Verify code contains expected functionality
        assert "def lambda_handler" in function.code
        assert "cluster_name" in function.code
        assert "eks_client" in function.code
        assert "perception_data" in function.code
    
    def test_create_reasoning_lambda(self):
        """Test creating reasoning Lambda template."""
        function = create_reasoning_lambda()
        
        assert function.function_name == "eks-upgrade-agent-reasoning"
        assert "Reasoning Phase" in function.description
        assert function.timeout == 600
        assert function.memory_size == 1024
        assert "reasoning" in function.tags["Phase"]
        
        # Verify code contains expected functionality
        assert "bedrock_client" in function.code
        assert "upgrade_plan" in function.code
        assert "steps" in function.code
    
    def test_create_execution_lambda(self):
        """Test creating execution Lambda template."""
        function = create_execution_lambda()
        
        assert function.function_name == "eks-upgrade-agent-execution"
        assert "Execution Phase" in function.description
        assert function.timeout == 900
        assert function.memory_size == 1024
        assert "execution" in function.tags["Phase"]
        
        # Verify code contains expected functionality
        assert "execution_results" in function.code
        assert "step_result" in function.code
        assert "iac_executor" in function.code
    
    def test_create_validation_lambda(self):
        """Test creating validation Lambda template."""
        function = create_validation_lambda()
        
        assert function.function_name == "eks-upgrade-agent-validation"
        assert "Validation Phase" in function.description
        assert function.timeout == 600
        assert function.memory_size == 512
        assert "validation" in function.tags["Phase"]
        
        # Verify code contains expected functionality
        assert "validation_results" in function.code
        assert "cluster_health" in function.code
        assert "overall_success" in function.code
    
    def test_create_rollback_lambda(self):
        """Test creating rollback Lambda template."""
        function = create_rollback_lambda()
        
        assert function.function_name == "eks-upgrade-agent-rollback"
        assert "Rollback Handler" in function.description
        assert function.timeout == 600
        assert function.memory_size == 512
        assert "rollback" in function.tags["Phase"]
        
        # Verify code contains expected functionality
        assert "rollback_steps" in function.code
        assert "redirect_traffic" in function.code
        assert "rollback_reason" in function.code
    
    def test_get_all_lambda_templates(self):
        """Test getting all Lambda templates."""
        templates = get_all_lambda_templates()
        
        assert len(templates) == 5
        
        function_names = [template.function_name for template in templates]
        expected_names = [
            "eks-upgrade-agent-perception",
            "eks-upgrade-agent-reasoning",
            "eks-upgrade-agent-execution",
            "eks-upgrade-agent-validation",
            "eks-upgrade-agent-rollback"
        ]
        
        for expected_name in expected_names:
            assert expected_name in function_names
        
        # Verify all templates are valid LambdaFunction instances
        for template in templates:
            assert isinstance(template, LambdaFunction)
            assert template.function_name.startswith("eks-upgrade-agent-")
            assert len(template.code) > 100  # Should have substantial code
            assert "lambda_handler" in template.code