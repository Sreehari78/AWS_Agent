"""Unit tests for Amazon Comprehend client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError, BotoCoreError

from src.eks_upgrade_agent.common.aws.comprehend import ComprehendClient
from src.eks_upgrade_agent.common.models.aws_ai import AWSAIConfig, ComprehendEntity
from src.eks_upgrade_agent.common.handler import AWSServiceError


@pytest.fixture
def aws_config():
    """Create test AWS AI configuration."""
    return AWSAIConfig(
        comprehend_region="us-east-1",
        comprehend_language_code="en",
        max_comprehend_requests_per_minute=100
    )


@pytest.fixture
def mock_comprehend_response():
    """Mock Comprehend API response."""
    return {
        'Entities': [
            {
                'Text': 'Kubernetes',
                'Type': 'ORGANIZATION',
                'Score': 0.95,
                'BeginOffset': 0,
                'EndOffset': 10
            },
            {
                'Text': 'v1.28',
                'Type': 'OTHER',
                'Score': 0.85,
                'BeginOffset': 20,
                'EndOffset': 25
            }
        ]
    }


class TestComprehendClient:
    """Test cases for ComprehendClient."""

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_initialization_success(self, mock_session, aws_config):
        """Test successful client initialization."""
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        
        assert client.config == aws_config
        assert client.aws_client.client == mock_client
        assert client.rate_limiter is not None
        assert client.analysis_engine is not None

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_initialization_with_profile(self, mock_session, aws_config):
        """Test client initialization with AWS profile."""
        aws_config.aws_profile = "test-profile"
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        
        mock_session.assert_called_with(profile_name="test-profile")
        assert client.aws_client.client == mock_client

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_initialization_failure(self, mock_session, aws_config):
        """Test client initialization failure."""
        mock_session.side_effect = Exception("AWS credentials not found")
        
        with pytest.raises(AWSServiceError, match="Failed to initialize Comprehend client"):
            ComprehendClient(aws_config)

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_detect_entities_success(self, mock_session, aws_config, mock_comprehend_response):
        """Test successful entity detection."""
        mock_client = Mock()
        mock_client.detect_entities.return_value = mock_comprehend_response
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        
        # Mock rate limiter to avoid delays
        client.rate_limiter.wait_if_needed = Mock()
        client.rate_limiter.record_request = Mock()
        
        text = "Kubernetes v1.28 introduces new features"
        entities = client.detect_entities(text)
        
        assert len(entities) == 2
        assert entities[0].text == "Kubernetes"
        assert entities[0].type == "ORGANIZATION"
        assert entities[0].confidence == 0.95
        assert entities[1].text == "v1.28"
        assert entities[1].type == "OTHER"
        assert entities[1].confidence == 0.85

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_detect_entities_empty_text(self, mock_session, aws_config):
        """Test entity detection with empty text."""
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        
        entities = client.detect_entities("")
        assert entities == []
        
        entities = client.detect_entities("   ")
        assert entities == []

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_detect_entities_client_error(self, mock_session, aws_config):
        """Test entity detection with Comprehend API error."""
        mock_client = Mock()
        mock_client.detect_entities.side_effect = ClientError(
            error_response={'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}},
            operation_name='DetectEntities'
        )
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        client.rate_limiter.wait_if_needed = Mock()
        
        with pytest.raises(AWSServiceError, match="Comprehend API error"):
            client.detect_entities("test text")

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_detect_entities_boto_error(self, mock_session, aws_config):
        """Test entity detection with boto3 error."""
        mock_client = Mock()
        mock_client.detect_entities.side_effect = BotoCoreError()
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        client.rate_limiter.wait_if_needed = Mock()
        
        with pytest.raises(AWSServiceError, match="Boto3 error"):
            client.detect_entities("test text")

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_analyze_kubernetes_text(self, mock_session, aws_config, mock_comprehend_response):
        """Test comprehensive Kubernetes text analysis."""
        mock_client = Mock()
        mock_client.detect_entities.return_value = mock_comprehend_response
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        client.rate_limiter.wait_if_needed = Mock()
        client.rate_limiter.record_request = Mock()
        
        text = "Kubernetes v1.28 deprecates the v1beta1 Ingress API. This is a breaking change."
        result = client.analyze_kubernetes_text(text)
        
        assert "analysis_id" in result
        assert result["input_text_length"] == len(text)
        assert "entities" in result
        assert "classifications" in result
        assert "kubernetes_context" in result
        assert "breaking_changes" in result
        assert "api_deprecations" in result
        assert "action_items" in result
        assert "validation" in result
        assert "summary" in result

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_detect_breaking_changes(self, mock_session, aws_config, mock_comprehend_response):
        """Test breaking change detection in release notes."""
        mock_client = Mock()
        mock_client.detect_entities.return_value = mock_comprehend_response
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        client.rate_limiter.wait_if_needed = Mock()
        client.rate_limiter.record_request = Mock()
        
        release_notes = """
        Kubernetes v1.28 Release Notes:
        - BREAKING CHANGE: The v1beta1 Ingress API is removed
        - Deprecated: PodSecurityPolicy will be removed in v1.29
        - Migration required for all Ingress resources
        """
        
        result = client.detect_breaking_changes(release_notes)
        
        assert "analysis_id" in result
        assert "breaking_changes" in result
        assert "api_deprecations" in result
        assert "critical_actions" in result
        assert "kubernetes_components" in result
        assert "severity_assessment" in result
        assert result["severity_assessment"]["overall_score"] >= 0

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_get_usage_statistics(self, mock_session, aws_config):
        """Test usage statistics retrieval."""
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        
        stats = client.get_usage_statistics()
        
        assert "rate_limiting" in stats
        assert "configuration" in stats
        assert "client_status" in stats
        assert stats["configuration"]["region"] == "us-east-1"
        assert stats["configuration"]["language_code"] == "en"
        assert stats["client_status"] == "active"

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_calculate_severity_score(self, mock_session, aws_config):
        """Test severity score calculation."""
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        
        # Mock analysis with various severity levels
        analysis = {
            "breaking_changes": [{"indicator": "breaking change"}],
            "api_deprecations": [{"indicator": "deprecated"}],
            "action_items": [
                {"severity": "CRITICAL", "priority": 0.9},
                {"severity": "HIGH", "priority": 0.8},
                {"severity": "MEDIUM", "priority": 0.6}
            ]
        }
        
        score = client.analysis_engine.result_processor._calculate_severity_score(analysis)
        
        # Should be: 1 breaking change (3.0) + 1 deprecation (2.0) + 1 critical (2.0) + 1 high (1.0) = 8.0
        assert score == 8.0

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_rate_limiting_integration(self, mock_session, aws_config, mock_comprehend_response):
        """Test rate limiting integration."""
        mock_client = Mock()
        mock_client.detect_entities.return_value = mock_comprehend_response
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        
        # Mock rate limiter methods
        wait_called = []
        record_called = []
        
        def mock_wait():
            wait_called.append(True)
            
        def mock_record():
            record_called.append(True)
        
        client.rate_limiter.wait_if_needed = mock_wait
        client.rate_limiter.record_request = mock_record
        
        client.detect_entities("test text")
        
        assert len(wait_called) == 1
        assert len(record_called) == 1