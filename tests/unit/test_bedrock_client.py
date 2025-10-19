"""
Unit tests for Amazon Bedrock client integration.
"""

import json
from unittest.mock import Mock, patch

import pytest

from src.eks_upgrade_agent.common.aws_ai.bedrock_client import BedrockClient
from src.eks_upgrade_agent.common.models.aws_ai import AWSAIConfig, BedrockAnalysisResult


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
def mock_components():
    """Mock all component dependencies."""
    with patch("src.eks_upgrade_agent.common.aws_ai.bedrock_client.RateLimiter") as mock_rate_limiter, \
         patch("src.eks_upgrade_agent.common.aws_ai.bedrock_client.CostTracker") as mock_cost_tracker, \
         patch("src.eks_upgrade_agent.common.aws_ai.bedrock_client.ModelInvoker") as mock_model_invoker:
        
        yield {
            "rate_limiter": mock_rate_limiter.return_value,
            "cost_tracker": mock_cost_tracker.return_value,
            "model_invoker": mock_model_invoker.return_value,
        }


@pytest.fixture
def bedrock_client(aws_ai_config, mock_components):
    """Create BedrockClient instance with mocked dependencies."""
    return BedrockClient(aws_ai_config)


class TestBedrockClientInitialization:
    """Test BedrockClient initialization."""

    def test_init_with_config(self, aws_ai_config, mock_components):
        """Test initialization with configuration."""
        client = BedrockClient(aws_ai_config)
        
        assert client.config == aws_ai_config
        assert client.rate_limiter is not None
        assert client.cost_tracker is not None
        assert client.model_invoker is not None


class TestTextAnalysis:
    """Test text analysis functionality."""

    def test_analyze_text_success(self, bedrock_client, mock_components):
        """Test successful text analysis."""
        # Mock successful response
        response_body = {
            "content": [{"text": json.dumps({
                "findings": ["Breaking change detected"],
                "breaking_changes": ["API v1 removed"],
                "deprecations": ["API v2 deprecated"],
                "recommendations": ["Migrate to v3"],
                "severity_score": 7.5,
                "confidence": 0.9,
            })}],
            "usage": {"input_tokens": 200, "output_tokens": 100},
        }
        
        mock_components["model_invoker"].invoke_model.return_value = response_body
        
        result = bedrock_client.analyze_text(
            text="Test release notes",
            prompt_template="Analyze: {text}",
        )
        
        assert isinstance(result, BedrockAnalysisResult)
        assert result.findings == ["Breaking change detected"]
        assert result.breaking_changes == ["API v1 removed"]
        assert result.deprecations == ["API v2 deprecated"]
        assert result.recommendations == ["Migrate to v3"]
        assert result.severity_score == 7.5
        assert result.confidence == 0.9

    def test_analyze_text_fallback_parsing(self, bedrock_client, mock_components):
        """Test text analysis with fallback parsing for non-JSON response."""
        # Mock response with plain text (not JSON)
        response_body = {
            "content": [{"text": "This is a plain text analysis result"}],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
        
        mock_components["model_invoker"].invoke_model.return_value = response_body
        
        result = bedrock_client.analyze_text(
            text="Test text",
            prompt_template="Analyze: {text}",
        )
        
        assert isinstance(result, BedrockAnalysisResult)
        assert result.findings == ["This is a plain text analysis result"]
        assert result.severity_score == 5.0  # Default fallback
        assert result.confidence == 0.8  # Default fallback

    def test_analyze_text_custom_parameters(self, bedrock_client, mock_components):
        """Test text analysis with custom parameters."""
        response_body = {
            "content": [{"text": '{"findings": ["test"]}'}],
            "usage": {"input_tokens": 50, "output_tokens": 25},
        }
        
        mock_components["model_invoker"].invoke_model.return_value = response_body
        
        result = bedrock_client.analyze_text(
            text="Test text",
            prompt_template="Custom prompt: {text}",
            model_id="custom-model",
            max_tokens=2048,
            temperature=0.5,
        )
        
        # Verify model invoker was called with correct model ID
        mock_components["model_invoker"].invoke_model.assert_called_once()
        call_args = mock_components["model_invoker"].invoke_model.call_args
        assert call_args[0][0] == "custom-model"  # model_id
        
        # Verify body contains custom parameters
        body = call_args[0][1]
        assert body["max_tokens"] == 2048
        assert body["temperature"] == 0.5


class TestSpecializedAnalysis:
    """Test specialized analysis methods."""

    def test_analyze_release_notes(self, bedrock_client):
        """Test release notes analysis."""
        # Mock the analyze_text method
        with patch.object(bedrock_client, "analyze_text") as mock_analyze:
            mock_result = Mock(spec=BedrockAnalysisResult)
            mock_analyze.return_value = mock_result
            
            result = bedrock_client.analyze_release_notes(
                release_notes="Test release notes",
                source_version="1.27",
                target_version="1.28",
            )
            
            assert result == mock_result
            mock_analyze.assert_called_once()

    def test_make_upgrade_decision(self, bedrock_client):
        """Test upgrade decision making."""
        # Create mock analysis results
        analysis_results = [
            Mock(
                findings=["finding1"],
                breaking_changes=["break1"],
                deprecations=["dep1"],
            ),
            Mock(
                findings=["finding2"],
                breaking_changes=["break2"],
                deprecations=["dep2"],
            ),
        ]
        
        with patch.object(bedrock_client, "analyze_text") as mock_analyze:
            mock_result = Mock(spec=BedrockAnalysisResult)
            mock_analyze.return_value = mock_result
            
            result = bedrock_client.make_upgrade_decision(
                cluster_state="healthy cluster",
                analysis_results=analysis_results,
                target_version="1.28",
            )
            
            assert result == mock_result
            mock_analyze.assert_called_once()


class TestCostSummary:
    """Test cost and usage summary."""

    def test_get_cost_summary(self, bedrock_client, mock_components):
        """Test cost summary generation."""
        # Mock component responses
        mock_components["cost_tracker"].get_cost_summary.return_value = {
            "daily_cost_usd": 5.5,
            "cost_threshold_usd": 10.0,
            "last_cost_reset": "2024-01-01T00:00:00Z",
        }
        mock_components["rate_limiter"].get_current_usage.return_value = 3
        
        summary = bedrock_client.get_cost_summary()
        
        assert summary["daily_cost_usd"] == 5.5
        assert summary["cost_threshold_usd"] == 10.0
        assert summary["requests_last_minute"] == 3
        assert summary["rate_limit"] == 5
        assert "last_cost_reset" in summary