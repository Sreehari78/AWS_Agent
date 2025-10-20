"""Tests for Step Functions integration."""

import json
import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, patch, MagicMock

from botocore.exceptions import ClientError, BotoCoreError

from src.eks_upgrade_agent.common.aws.orchestration.step_functions import (
    StepFunctionsClient,
    StateMachineDefinition,
    ExecutionResult,
    create_upgrade_state_machine_definition
)
from src.eks_upgrade_agent.common.handler import AWSServiceError, ExecutionError


class TestStateMachineDefinition:
    """Test StateMachineDefinition model."""
    
    def test_valid_definition(self):
        """Test valid state machine definition."""
        definition = StateMachineDefinition(
            name="test-state-machine",
            definition={"Comment": "Test", "StartAt": "Pass", "States": {"Pass": {"Type": "Pass", "End": True}}},
            role_arn="arn:aws:iam::123456789012:role/test-role"
        )
        
        assert definition.name == "test-state-machine"
        assert definition.timeout_seconds == 3600
        assert definition.tags == {}
    
    def test_invalid_timeout(self):
        """Test invalid timeout validation."""
        with pytest.raises(ValueError, match="Timeout must be between 60 and 86400 seconds"):
            StateMachineDefinition(
                name="test",
                definition={},
                role_arn="arn:aws:iam::123456789012:role/test-role",
                timeout_seconds=30
            )


class TestStepFunctionsClient:
    """Test StepFunctionsClient."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock boto3 Step Functions client."""
        with patch('boto3.Session') as mock_session:
            mock_sf_client = Mock()
            mock_session.return_value.client.return_value = mock_sf_client
            
            client = StepFunctionsClient(region="us-east-1")
            client.client = mock_sf_client
            
            yield client, mock_sf_client
    
    def test_initialization(self):
        """Test client initialization."""
        with patch('boto3.Session') as mock_session:
            mock_sf_client = Mock()
            mock_session.return_value.client.return_value = mock_sf_client
            
            client = StepFunctionsClient(
                region="us-west-2",
                aws_access_key_id="test-key",
                aws_secret_access_key="test-secret"
            )
            
            assert client.region == "us-west-2"
            mock_session.assert_called_once()
    
    def test_create_state_machine_success(self, mock_client):
        """Test successful state machine creation."""
        client, mock_sf_client = mock_client
        
        definition = StateMachineDefinition(
            name="test-state-machine",
            definition={"Comment": "Test"},
            role_arn="arn:aws:iam::123456789012:role/test-role"
        )
        
        mock_sf_client.create_state_machine.return_value = {
            "stateMachineArn": "arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine"
        }
        
        result = client.create_state_machine(definition)
        
        assert result == "arn:aws:states:us-east-1:123456789012:stateMachine:test-state-machine"
        mock_sf_client.create_state_machine.assert_called_once()
    
    def test_create_state_machine_failure(self, mock_client):
        """Test state machine creation failure."""
        client, mock_sf_client = mock_client
        
        definition = StateMachineDefinition(
            name="test-state-machine",
            definition={"Comment": "Test"},
            role_arn="arn:aws:iam::123456789012:role/test-role"
        )
        
        mock_sf_client.create_state_machine.side_effect = ClientError(
            {"Error": {"Code": "InvalidParameterValue", "Message": "Invalid role"}},
            "CreateStateMachine"
        )
        
        with pytest.raises(AWSServiceError, match="Failed to create state machine"):
            client.create_state_machine(definition)
    
    def test_start_execution_success(self, mock_client):
        """Test successful execution start."""
        client, mock_sf_client = mock_client
        
        mock_sf_client.start_execution.return_value = {
            "executionArn": "arn:aws:states:us-east-1:123456789012:execution:test:exec-123"
        }
        
        result = client.start_execution(
            "arn:aws:states:us-east-1:123456789012:stateMachine:test",
            {"cluster_name": "test-cluster"}
        )
        
        assert result == "arn:aws:states:us-east-1:123456789012:execution:test:exec-123"
        mock_sf_client.start_execution.assert_called_once()
    
    def test_get_execution_status_success(self, mock_client):
        """Test successful execution status retrieval."""
        client, mock_sf_client = mock_client
        
        mock_sf_client.describe_execution.return_value = {
            "executionArn": "arn:aws:states:us-east-1:123456789012:execution:test:exec-123",
            "status": "SUCCEEDED",
            "startDate": datetime.now(UTC),
            "stopDate": datetime.now(UTC),
            "input": '{"cluster_name": "test"}',
            "output": '{"success": true}'
        }
        
        result = client.get_execution_status("arn:aws:states:us-east-1:123456789012:execution:test:exec-123")
        
        assert isinstance(result, ExecutionResult)
        assert result.status == "SUCCEEDED"
        assert result.input_data == {"cluster_name": "test"}
        assert result.output_data == {"success": True}
    
    def test_wait_for_execution_success(self, mock_client):
        """Test successful execution wait."""
        client, mock_sf_client = mock_client
        
        # Mock execution that completes after 2 polls
        mock_responses = [
            {
                "executionArn": "arn:aws:states:us-east-1:123456789012:execution:test:exec-123",
                "status": "RUNNING",
                "startDate": datetime.now(UTC),
                "input": '{"cluster_name": "test"}'
            },
            {
                "executionArn": "arn:aws:states:us-east-1:123456789012:execution:test:exec-123",
                "status": "SUCCEEDED",
                "startDate": datetime.now(UTC),
                "stopDate": datetime.now(UTC),
                "input": '{"cluster_name": "test"}',
                "output": '{"success": true}'
            }
        ]
        
        mock_sf_client.describe_execution.side_effect = mock_responses
        
        with patch('time.sleep'):
            result = client.wait_for_execution(
                "arn:aws:states:us-east-1:123456789012:execution:test:exec-123",
                max_wait_seconds=60,
                poll_interval=1
            )
        
        assert result.status == "SUCCEEDED"
    
    def test_wait_for_execution_timeout(self, mock_client):
        """Test execution wait timeout."""
        client, mock_sf_client = mock_client
        
        mock_sf_client.describe_execution.return_value = {
            "executionArn": "arn:aws:states:us-east-1:123456789012:execution:test:exec-123",
            "status": "RUNNING",
            "startDate": datetime.now(UTC),
            "input": '{"cluster_name": "test"}'
        }
        
        with patch('time.sleep'), patch('time.time', side_effect=[0, 0, 70]):
            with pytest.raises(ExecutionError, match="timed out"):
                client.wait_for_execution(
                    "arn:aws:states:us-east-1:123456789012:execution:test:exec-123",
                    max_wait_seconds=60,
                    poll_interval=1
                )
    
    def test_stop_execution_success(self, mock_client):
        """Test successful execution stop."""
        client, mock_sf_client = mock_client
        
        client.stop_execution("arn:aws:states:us-east-1:123456789012:execution:test:exec-123")
        
        mock_sf_client.stop_execution.assert_called_once_with(
            executionArn="arn:aws:states:us-east-1:123456789012:execution:test:exec-123",
            error="Manual stop",
            cause="Stopped by user"
        )
    
    def test_list_executions_success(self, mock_client):
        """Test successful execution listing."""
        client, mock_sf_client = mock_client
        
        mock_sf_client.list_executions.return_value = {
            "executions": [
                {
                    "executionArn": "arn:aws:states:us-east-1:123456789012:execution:test:exec-123",
                    "status": "SUCCEEDED",
                    "startDate": datetime.now(UTC),
                    "stopDate": datetime.now(UTC)
                }
            ]
        }
        
        result = client.list_executions("arn:aws:states:us-east-1:123456789012:stateMachine:test")
        
        assert len(result) == 1
        assert isinstance(result[0], ExecutionResult)
        assert result[0].status == "SUCCEEDED"
    
    def test_delete_state_machine_success(self, mock_client):
        """Test successful state machine deletion."""
        client, mock_sf_client = mock_client
        
        client.delete_state_machine("arn:aws:states:us-east-1:123456789012:stateMachine:test")
        
        mock_sf_client.delete_state_machine.assert_called_once_with(
            stateMachineArn="arn:aws:states:us-east-1:123456789012:stateMachine:test"
        )


class TestUpgradeStateMachineDefinition:
    """Test upgrade state machine definition creation."""
    
    def test_create_upgrade_state_machine_definition(self):
        """Test creating upgrade state machine definition."""
        definition = create_upgrade_state_machine_definition(
            cluster_name="test-cluster",
            target_version="1.29",
            strategy="blue_green"
        )
        
        assert "Comment" in definition
        assert "StartAt" in definition
        assert "States" in definition
        assert definition["StartAt"] == "PerceptionPhase"
        
        # Check all required states exist
        required_states = [
            "PerceptionPhase", "ReasoningPhase", "ExecutionPhase", 
            "ValidationPhase", "CheckValidationResult", "UpgradeSuccess",
            "TriggerRollback", "HandleFailure", "UpgradeFailure"
        ]
        
        for state in required_states:
            assert state in definition["States"]
        
        # Check perception phase configuration
        perception_phase = definition["States"]["PerceptionPhase"]
        assert perception_phase["Type"] == "Task"
        assert perception_phase["Resource"] == "arn:aws:states:::lambda:invoke"
        assert "eks-upgrade-agent-perception" in perception_phase["Parameters"]["FunctionName"]
        assert perception_phase["Next"] == "ReasoningPhase"
        
        # Check error handling
        assert "Catch" in perception_phase
        assert perception_phase["Catch"][0]["Next"] == "HandleFailure"