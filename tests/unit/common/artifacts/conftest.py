"""Shared fixtures for artifacts tests."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from src.eks_upgrade_agent.common.artifacts import TestArtifactsManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def artifacts_manager(temp_dir):
    """Create a TestArtifactsManager instance for testing."""
    return TestArtifactsManager(
        base_directory=temp_dir,
        s3_bucket="test-bucket",
        s3_prefix="test-prefix",
        retention_days=7,
        auto_upload=False
    )


@pytest.fixture
def test_file(temp_dir):
    """Create a test file for artifact testing."""
    test_file = temp_dir / "test_file.log"
    test_file.write_text("This is a test log file\nwith multiple lines\n")
    return test_file


@pytest.fixture
def mock_s3_client():
    """Mock S3 client for testing."""
    with patch('boto3.client') as mock_client:
        mock_s3 = Mock()
        mock_client.return_value = mock_s3
        yield mock_s3


@pytest.fixture
def sample_session(artifacts_manager):
    """Create a sample test session."""
    return artifacts_manager.create_session(
        upgrade_id="upgrade-123",
        cluster_name="test-cluster",
        session_name="Test Session",
        description="Test session description"
    )


@pytest.fixture
def sample_collection(artifacts_manager, sample_session):
    """Create a sample artifact collection."""
    return artifacts_manager.create_collection(
        session_id=sample_session.session_id,
        collection_name="Test Collection",
        description="Test collection description"
    )