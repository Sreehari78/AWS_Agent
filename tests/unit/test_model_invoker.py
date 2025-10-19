"""
Unit tests for model invoker functionality.
"""

import json
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError, BotoCoreError

from src.eks_upgrade_agent.common.aws.bedrock.model_invoker import ModelInvoker
from src.eks_upgrade_agent.common.aws.bedrock.rate_limiter import RateLimiter, BedrockRateLimitError
from src.eks_upgrade_agent.common.aws.bedrock.cost_tracker import CostTracker, BedrockCostThresholdError
from src.eks_upgrade_agent.common.models.aws_ai import AWSAIConfig
from src.eks_upgrade_agent.common.handler.aws_service import AWSServiceError


@pytest.fixture
def aws_ai_config():
    """Create test AWS AI configuration."""
    return AWSAIConfig(
        bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        bedrock_region="us-east-1",
        max_bedrock_requests_per_minute=5,
        cost_threshold_usd=10.0,
    )


@pytest.fixture
def rate_limiter():
    """Create rate limiter."""
    return RateLimiter(max_requests_per_minute=5)


@pytest.fixture
def cost_tracker():
    """Create cost tracker."""
    return CostTracker(cost_threshold_usd=10.0)


@pytest.fixture
def mock_boto3_client():
    """Mock boto3 client."""
    with patch("boto3.Session") as mock_session:
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client
        yield mock_client


@pytest.fixture
def model_invoker(aws_ai_config, rate_limiter, cost_tracker, mock_boto3_client):
    """Create ModelInvoker instance with mocked dependencies."""
    invoker = ModelInvoker(aws_ai_config, rate_limiter, cost_tracker)
    invoker.client = mock_boto3_client
    return invoker


class TestModelInvoker:
    """Test model invoker functionality."""

    def test_init(self, aws_ai_config, rate_limiter, cost_tracker, mock_boto3_client):
        """Test model invoker initialization."""
        invoker = ModelInvoker(aws_ai_config, rate_limiter, cost_tracker)
        
        assert invoker.config == aws_ai_config
        assert invoker.rate_limiter == rate_limiter
        assert invoker.cost_tracker == cost_tracker

    def test_invoke_model_success(self, model_invoker, mock_boto3_client):
        """Test successful model invocation."""
        # Mock successful response
        response_body = {
            "content": [{"text": "test response"}],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
        
        mock_response = {"body": Mock()}
        mock_response["body"].read.return_value = json.dumps(response_body)
        mock_boto3_client.invoke_model.return_value = mock_response
        
        body = {"messages": [{"role": "user", "content": "test"}]}
        result = model_invoker.invoke_model("test-model", body)
        
        assert result == response_body
        mock_boto3_client.invoke_model.assert_called_once()

    def test_invoke_model_client_error(self, model_invoker, mock_boto3_client):
        """Test model invocation with ClientError."""
        error_response = {
            "Error": {"Code": "ValidationException", "Message": "Invalid input"}
        }
        mock_boto3_client.invoke_model.side_effect = ClientError(
            error_response, "InvokeModel"
        )
        
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with pytest.raises(AWSServiceError):
            model_invoker.invoke_model("test-model", body)

    def test_invoke_model_boto_error(self, model_invoker, mock_boto3_client):
        """Test model invocation with BotoCoreError."""
        mock_boto3_client.invoke_model.side_effect = BotoCoreError()
        
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with pytest.raises(AWSServiceError):
            model_invoker.invoke_model("test-model", body)

    def test_invoke_model_rate_limit_error(self, model_invoker, mock_boto3_client):
        """Test model invocation with rate limit exceeded."""
        # Mock rate limiter to raise exception
        model_invoker.rate_limiter.check_rate_limit = Mock(
            side_effect=BedrockRateLimitError("Rate limit exceeded")
        )
        
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with pytest.raises(BedrockRateLimitError):
            model_invoker.invoke_model("test-model", body)

    def test_invoke_model_cost_threshold_error(self, model_invoker, mock_boto3_client):
        """Test model invocation with cost threshold exceeded."""
        # Mock cost tracker to raise exception
        model_invoker.cost_tracker.check_cost_threshold = Mock(
            side_effect=BedrockCostThresholdError("Cost threshold exceeded")
        )
        
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with pytest.raises(BedrockCostThresholdError):
            model_invoker.invoke_model("test-model", body)

    def test_invoke_model_with_cost_tracking(self, model_invoker, mock_boto3_client):
        """Test model invocation with cost tracking update."""
        response_body = {
            "content": [{"text": "test response"}],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
        
        mock_response = {"body": Mock()}
        mock_response["body"].read.return_value = json.dumps(response_body)
        mock_boto3_client.invoke_model.return_value = mock_response
        
        # Mock cost tracker update method
        model_invoker.cost_tracker.update_cost_tracking = Mock()
        
        body = {"messages": [{"role": "user", "content": "test"}]}
        model_invoker.invoke_model("test-model", body)
        
        # Verify cost tracking was called
        model_invoker.cost_tracker.update_cost_tracking.assert_called_once_with(
            {"input_tokens": 100, "output_tokens": 50}
        )

    def test_invoke_model_without_usage_info(self, model_invoker, mock_boto3_client):
        """Test model invocation without usage information."""
        response_body = {
            "content": [{"text": "test response"}],
            # No usage information
        }
        
        mock_response = {"body": Mock()}
        mock_response["body"].read.return_value = json.dumps(response_body)
        mock_boto3_client.invoke_model.return_value = mock_response
        
        # Mock cost tracker update method
        model_invoker.cost_tracker.update_cost_tracking = Mock()
        
        body = {"messages": [{"role": "user", "content": "test"}]}
        result = model_invoker.invoke_model("test-model", body)
        
        assert result == response_body
        # Cost tracking should not be called without usage info
        model_invoker.cost_tracker.update_cost_tracking.assert_not_called()