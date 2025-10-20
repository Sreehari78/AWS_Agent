"""Unit tests for AWS Comprehend client initialization."""

import pytest
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError

from src.eks_upgrade_agent.common.aws.comprehend.aws_client import AWSComprehendClient
from src.eks_upgrade_agent.common.models.aws_ai import AWSAIConfig
from src.eks_upgrade_agent.common.handler import AWSServiceError


@pytest.fixture
def aws_config():
    """Create test AWS AI configuration."""
    return AWSAIConfig(
        comprehend_region="us-east-1",
        comprehend_language_code="en"
    )


class TestAWSComprehendClient:
    """Test cases for AWSComprehendClient."""

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_initialization_success(self, mock_session, aws_config):
        """Test successful client initialization."""
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client
        
        aws_client = AWSComprehendClient(aws_config)
        
        assert aws_client.config == aws_config
        assert aws_client.client == mock_client
        assert aws_client.is_initialized() is True

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_initialization_with_profile(self, mock_session, aws_config):
        """Test client initialization with AWS profile."""
        aws_config.aws_profile = "test-profile"
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client
        
        aws_client = AWSComprehendClient(aws_config)
        
        mock_session.assert_called_with(profile_name="test-profile")
        assert aws_client.client == mock_client

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_initialization_failure(self, mock_session, aws_config):
        """Test client initialization failure."""
        mock_session.side_effect = Exception("AWS credentials not found")
        
        with pytest.raises(AWSServiceError, match="Failed to initialize Comprehend client"):
            AWSComprehendClient(aws_config)

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_client_property_not_initialized(self, mock_session, aws_config):
        """Test client property when not initialized."""
        mock_session.side_effect = Exception("Failed")
        
        with pytest.raises(AWSServiceError):
            aws_client = AWSComprehendClient(aws_config)

    @patch('src.eks_upgrade_agent.common.aws.comprehend.aws_client.boto3.Session')
    def test_is_initialized(self, mock_session, aws_config):
        """Test is_initialized method."""
        mock_client = Mock()
        mock_session.return_value.client.return_value = mock_client
        
        aws_client = AWSComprehendClient(aws_config)
        
        assert aws_client.is_initialized() is True