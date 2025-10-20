"""Tests for S3 upload operations."""

import pytest
from unittest.mock import Mock, patch

from src.eks_upgrade_agent.common.models.artifacts import ArtifactStatus


class TestS3Operations:
    """Test cases for S3 upload operations."""

    def test_upload_artifact_success(self, artifacts_manager, sample_session, sample_collection, test_file):
        """Test successful artifact upload to S3."""
        # Mock the S3 client on the manager instance
        mock_s3_client = Mock()
        
        # Create a side effect that actually calls mark_uploaded on the artifact
        def mock_upload_side_effect(artifact):
            artifact.mark_uploaded(f"s3://test-bucket/test-key/{artifact.artifact_id}")
            return True
        
        mock_s3_client.upload_artifact.side_effect = mock_upload_side_effect
        artifacts_manager.s3_client = mock_s3_client
        
        # Add artifact
        artifact = artifacts_manager.add_artifact(
            sample_session.session_id,
            sample_collection.collection_id,
            test_file
        )
        
        # Upload artifact
        result = artifacts_manager.upload_artifact(sample_session.session_id, artifact.artifact_id)
        assert result is True
        
        # Verify upload was called
        mock_s3_client.upload_artifact.assert_called_once()
        
        # Check artifact status by searching
        artifacts = artifacts_manager.search_artifacts(session_id=sample_session.session_id)
        uploaded_artifact = next((a for a in artifacts if a.artifact_id == artifact.artifact_id), None)
        assert uploaded_artifact is not None
        assert uploaded_artifact.status == ArtifactStatus.UPLOADED

    def test_upload_artifact_no_s3_client(self, artifacts_manager, sample_session, sample_collection, test_file):
        """Test artifact upload without S3 client configured."""
        # Add artifact
        artifact = artifacts_manager.add_artifact(
            sample_session.session_id,
            sample_collection.collection_id,
            test_file
        )
        
        # Upload should fail gracefully
        result = artifacts_manager.upload_artifact(sample_session.session_id, artifact.artifact_id)
        assert result is False

    def test_upload_artifact_failure(self, artifacts_manager, sample_session, sample_collection, test_file):
        """Test artifact upload failure."""
        # Mock the S3 client on the manager instance to fail
        mock_s3_client = Mock()
        mock_s3_client.upload_artifact.return_value = False
        artifacts_manager.s3_client = mock_s3_client
        
        # Add artifact
        artifact = artifacts_manager.add_artifact(
            sample_session.session_id,
            sample_collection.collection_id,
            test_file
        )
        
        # Upload should fail
        result = artifacts_manager.upload_artifact(sample_session.session_id, artifact.artifact_id)
        assert result is False
        
        # Check artifact status - it should remain CREATED when upload fails with mock
        artifacts = artifacts_manager.search_artifacts(session_id=sample_session.session_id)
        failed_artifact = next((a for a in artifacts if a.artifact_id == artifact.artifact_id), None)
        assert failed_artifact is not None
        # When S3 client returns False, the artifact status should remain unchanged
        assert failed_artifact.status == ArtifactStatus.CREATED

    def test_upload_nonexistent_artifact(self, artifacts_manager, sample_session):
        """Test uploading nonexistent artifact."""
        result = artifacts_manager.upload_artifact(sample_session.session_id, "nonexistent")
        assert result is False

    def test_upload_all_artifacts(self, artifacts_manager, sample_session, sample_collection, test_file, temp_dir):
        """Test uploading all artifacts in a session."""
        # Mock the S3 client on the manager instance
        mock_s3_client = Mock()
        mock_s3_client.upload_artifact.return_value = True
        artifacts_manager.s3_client = mock_s3_client
        
        # Add multiple artifacts
        artifact1 = artifacts_manager.add_artifact(
            sample_session.session_id,
            sample_collection.collection_id,
            test_file
        )
        
        test_file2 = temp_dir / "test_file2.log"
        test_file2.write_text("Second test file")
        
        artifact2 = artifacts_manager.add_artifact(
            sample_session.session_id,
            sample_collection.collection_id,
            test_file2
        )
        
        # Upload all artifacts using session upload method
        results = artifacts_manager.upload_session_artifacts(sample_session.session_id)
        
        # Should have 2 successful uploads
        assert len(results) == 2
        assert all(results.values())
        
        # Verify both uploads were called
        assert mock_s3_client.upload_artifact.call_count == 2