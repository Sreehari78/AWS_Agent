"""
Unit tests for the exception hierarchy in the EKS Upgrade Agent.

Tests the custom exception classes, error context preservation,
and structured error data functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from src.eks_upgrade_agent.common.exceptions import (
    EKSUpgradeAgentError,
    PerceptionError,
    PlanningError,
    ExecutionError,
    ValidationError,
    ConfigurationError,
    AWSServiceError,
    RollbackError,
    create_perception_error,
    create_execution_error,
    create_validation_error,
)


class TestEKSUpgradeAgentError:
    """Test the base exception class."""
    
    def test_basic_exception_creation(self):
        """Test creating a basic exception."""
        error = EKSUpgradeAgentError("Test error message")
        
        assert str(error) == "[EKSUpgradeAgentError] Test error message"
        assert error.message == "Test error message"
        assert error.error_code == "EKSUpgradeAgentError"
        assert error.context == {}
        assert error.recoverable is False
        assert isinstance(error.timestamp, datetime)
    
    def test_exception_with_context(self):
        """Test exception with additional context."""
        context = {"cluster_name": "test-cluster", "version": "1.28"}
        error = EKSUpgradeAgentError(
            "Test error",
            error_code="TEST_ERROR",
            context=context,
            recoverable=True
        )
        
        assert error.error_code == "TEST_ERROR"
        assert error.context == context
        assert error.recoverable is True
        assert "Context: {'cluster_name': 'test-cluster', 'version': '1.28'}" in str(error)
    
    def test_exception_with_cause(self):
        """Test exception with original cause."""
        original_error = ValueError("Original error")
        error = EKSUpgradeAgentError("Wrapped error", cause=original_error)
        
        assert error.cause == original_error
        assert error.__cause__ == original_error
    
    def test_to_dict_method(self):
        """Test converting exception to dictionary."""
        context = {"key": "value"}
        error = EKSUpgradeAgentError(
            "Test message",
            error_code="TEST_CODE",
            context=context,
            recoverable=True
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["error_type"] == "EKSUpgradeAgentError"
        assert error_dict["error_code"] == "TEST_CODE"
        assert error_dict["message"] == "Test message"
        assert error_dict["context"] == context
        assert error_dict["recoverable"] is True
        assert "timestamp" in error_dict
    
    def test_add_context_method(self):
        """Test adding context to exception."""
        error = EKSUpgradeAgentError("Test error")
        
        result = error.add_context("key1", "value1")
        error.add_context("key2", "value2")
        
        assert result is error  # Should return self for chaining
        assert error.context == {"key1": "value1", "key2": "value2"}


class TestPerceptionError:
    """Test the PerceptionError class."""
    
    def test_perception_error_creation(self):
        """Test creating a PerceptionError."""
        api_error = Exception("API failed")
        error = PerceptionError(
            "Failed to collect data",
            source="aws_api",
            api_error=api_error
        )
        
        assert isinstance(error, EKSUpgradeAgentError)
        assert error.context["source"] == "aws_api"
        assert error.context["api_error_type"] == "Exception"
        assert error.context["api_error_message"] == "API failed"
        assert error.cause == api_error


class TestPlanningError:
    """Test the PlanningError class."""
    
    def test_planning_error_creation(self):
        """Test creating a PlanningError."""
        invalid_config = {"strategy": "invalid"}
        error = PlanningError(
            "Invalid strategy",
            planning_phase="strategy_selection",
            invalid_config=invalid_config
        )
        
        assert isinstance(error, EKSUpgradeAgentError)
        assert error.context["planning_phase"] == "strategy_selection"
        assert error.context["invalid_config"] == invalid_config


class TestExecutionError:
    """Test the ExecutionError class."""
    
    def test_execution_error_creation(self):
        """Test creating an ExecutionError."""
        error = ExecutionError(
            "Command failed",
            execution_step="provision_cluster",
            command="terraform apply",
            exit_code=1,
            stdout="Output",
            stderr="Error output"
        )
        
        assert isinstance(error, EKSUpgradeAgentError)
        assert error.context["execution_step"] == "provision_cluster"
        assert error.context["command"] == "terraform apply"
        assert error.context["exit_code"] == 1
        assert error.context["stdout"] == "Output"
        assert error.context["stderr"] == "Error output"
    
    def test_execution_error_truncates_long_output(self):
        """Test that long stdout/stderr is truncated."""
        long_output = "x" * 2000
        error = ExecutionError(
            "Command failed",
            stdout=long_output,
            stderr=long_output
        )
        
        assert len(error.context["stdout"]) == 1000
        assert len(error.context["stderr"]) == 1000


class TestValidationError:
    """Test the ValidationError class."""
    
    def test_validation_error_creation(self):
        """Test creating a ValidationError."""
        failed_checks = ["health_check", "metrics_check"]
        metrics = {"error_rate": 0.05, "latency": 200}
        threshold_violations = {"error_rate": {"threshold": 0.01, "actual": 0.05}}
        
        error = ValidationError(
            "Validation failed",
            validation_type="health_check",
            failed_checks=failed_checks,
            metrics=metrics,
            threshold_violations=threshold_violations
        )
        
        assert isinstance(error, EKSUpgradeAgentError)
        assert error.context["validation_type"] == "health_check"
        assert error.context["failed_checks"] == failed_checks
        assert error.context["metrics"] == metrics
        assert error.context["threshold_violations"] == threshold_violations


class TestConfigurationError:
    """Test the ConfigurationError class."""
    
    def test_configuration_error_creation(self):
        """Test creating a ConfigurationError."""
        missing_keys = ["aws_region", "cluster_name"]
        invalid_values = {"timeout": -1}
        
        error = ConfigurationError(
            "Invalid configuration",
            config_file="config.yaml",
            missing_keys=missing_keys,
            invalid_values=invalid_values
        )
        
        assert isinstance(error, EKSUpgradeAgentError)
        assert error.context["config_file"] == "config.yaml"
        assert error.context["missing_keys"] == missing_keys
        assert error.context["invalid_values"] == invalid_values


class TestAWSServiceError:
    """Test the AWSServiceError class."""
    
    def test_aws_service_error_creation(self):
        """Test creating an AWSServiceError."""
        error = AWSServiceError(
            "Bedrock API failed",
            service_name="bedrock",
            operation="invoke_model",
            aws_error_code="ThrottlingException",
            aws_error_message="Rate limit exceeded"
        )
        
        assert isinstance(error, EKSUpgradeAgentError)
        assert error.context["service_name"] == "bedrock"
        assert error.context["operation"] == "invoke_model"
        assert error.context["aws_error_code"] == "ThrottlingException"
        assert error.context["aws_error_message"] == "Rate limit exceeded"


class TestRollbackError:
    """Test the RollbackError class."""
    
    def test_rollback_error_creation(self):
        """Test creating a RollbackError."""
        original_error = ExecutionError("Deployment failed")
        error = RollbackError(
            "Rollback failed",
            rollback_step="traffic_redirect",
            original_error=original_error
        )
        
        assert isinstance(error, EKSUpgradeAgentError)
        assert error.context["rollback_step"] == "traffic_redirect"
        assert error.context["original_error_type"] == "ExecutionError"
        assert error.context["original_error_message"] == str(original_error)
        assert error.cause == original_error
        assert error.recoverable is False  # Rollback errors are not recoverable


class TestConvenienceFunctions:
    """Test the convenience functions for creating exceptions."""
    
    def test_create_perception_error(self):
        """Test create_perception_error function."""
        api_error = Exception("API error")
        error = create_perception_error(
            "Data collection failed",
            source="k8s_api",
            api_error=api_error,
            cluster_name="test-cluster"
        )
        
        assert isinstance(error, PerceptionError)
        assert error.message == "Data collection failed"
        assert error.context["source"] == "k8s_api"
        assert error.context["cluster_name"] == "test-cluster"
        assert error.cause == api_error
    
    def test_create_execution_error(self):
        """Test create_execution_error function."""
        error = create_execution_error(
            "Command execution failed",
            step="deploy_apps",
            command="kubectl apply",
            exit_code=1,
            namespace="default"
        )
        
        assert isinstance(error, ExecutionError)
        assert error.message == "Command execution failed"
        assert error.context["execution_step"] == "deploy_apps"
        assert error.context["command"] == "kubectl apply"
        assert error.context["exit_code"] == 1
        assert error.context["namespace"] == "default"
    
    def test_create_validation_error(self):
        """Test create_validation_error function."""
        failed_checks = ["pod_ready", "service_healthy"]
        error = create_validation_error(
            "Health checks failed",
            validation_type="health_check",
            failed_checks=failed_checks,
            cluster_name="test-cluster"
        )
        
        assert isinstance(error, ValidationError)
        assert error.message == "Health checks failed"
        assert error.context["validation_type"] == "health_check"
        assert error.context["failed_checks"] == failed_checks
        assert error.context["cluster_name"] == "test-cluster"