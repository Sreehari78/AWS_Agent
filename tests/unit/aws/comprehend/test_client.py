"""Unit tests for main Comprehend client interface."""

import pytest
from unittest.mock import Mock, patch
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
            }
        ]
    }


class TestComprehendClientInterface:
    """Test cases for ComprehendClient main interface."""

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_initialization_success(self, mock_session, aws_config):
        """Test successful client initialization."""
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        
        assert client.config == aws_config
        assert client.aws_client is not None
        assert client.rate_limiter is not None
        assert client.analysis_engine is not None

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_detect_entities_success(self, mock_session, aws_config, mock_comprehend_response):
        """Test successful entity detection."""
        mock_client = Mock()
        mock_client.detect_entities.return_value = mock_comprehend_response
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        client.rate_limiter.wait_if_needed = Mock()
        client.rate_limiter.record_request = Mock()
        
        text = "Kubernetes v1.28 introduces new features"
        entities = client.detect_entities(text)
        
        assert len(entities) == 1
        assert entities[0].text == "Kubernetes"
        assert entities[0].type == "ORGANIZATION"
        assert entities[0].confidence == 0.95

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_detect_entities_empty_text(self, mock_session, aws_config):
        """Test entity detection with empty text."""
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        
        entities = client.detect_entities("")
        assert entities == []

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_analyze_kubernetes_text(self, mock_session, aws_config, mock_comprehend_response):
        """Test comprehensive Kubernetes text analysis."""
        mock_client = Mock()
        mock_client.detect_entities.return_value = mock_comprehend_response
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        client.rate_limiter.wait_if_needed = Mock()
        client.rate_limiter.record_request = Mock()
        
        text = "Kubernetes v1.28 deprecates the v1beta1 Ingress API"
        result = client.analyze_kubernetes_text(text)
        
        assert "analysis_id" in result
        assert "entities" in result
        assert "summary" in result

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_detect_breaking_changes(self, mock_session, aws_config, mock_comprehend_response):
        """Test breaking change detection."""
        mock_client = Mock()
        mock_client.detect_entities.return_value = mock_comprehend_response
        mock_session.return_value.client.return_value = mock_client
        
        client = ComprehendClient(aws_config)
        client.rate_limiter.wait_if_needed = Mock()
        client.rate_limiter.record_request = Mock()
        
        release_notes = "BREAKING CHANGE: The v1beta1 Ingress API is removed"
        result = client.detect_breaking_changes(release_notes)
        
        assert "analysis_id" in result
        assert "severity_assessment" in result

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

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_error_handling(self, mock_session, aws_config):
        """Test error handling in client methods."""
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