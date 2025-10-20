"""Tests for artifact operations functionality."""

import pytest
from pathlib import Path

from src.eks_upgrade_agent.common.models.artifacts import (
    ArtifactStatus,
    ArtifactType,
    TestArtifact
)


class TestArtifactOperations:
    """Test cases for artifact operations."""

    def test_add_artifact_success(self, artifacts_manager, sample_session, sample_collection, test_file):
        """Test successful artifact addition."""
        artifact = artifacts_manager.add_artifact(
            session_id=sample_session.session_id,
            collection_id=sample_collection.collection_id,
            file_path=test_file,
            artifact_type=ArtifactType.LOG_FILE,
            description="Test log file"
        )
        
        assert isinstance(artifact, TestArtifact)
        assert artifact.name == test_file.name
        assert artifact.artifact_type == ArtifactType.LOG_FILE
        assert artifact.description == "Test log file"
        assert artifact.status == ArtifactStatus.CREATED
        assert artifact.file_size > 0

    def test_add_artifact_invalid_session(self, artifacts_manager, test_file):
        """Test adding artifact with invalid session."""
        artifact = artifacts_manager.add_artifact(
            session_id="nonexistent",
            collection_id="any",
            file_path=test_file
        )
        assert artifact is None

    def test_add_artifact_invalid_collection(self, artifacts_manager, sample_session, test_file):
        """Test adding artifact with invalid collection."""
        artifact = artifacts_manager.add_artifact(
            session_id=sample_session.session_id,
            collection_id="nonexistent",
            file_path=test_file
        )
        assert artifact is None

    def test_add_artifact_nonexistent_file(self, artifacts_manager, sample_session, sample_collection):
        """Test adding nonexistent file as artifact."""
        nonexistent_file = Path("nonexistent") / "file.log"
        
        artifact = artifacts_manager.add_artifact(
            session_id=sample_session.session_id,
            collection_id=sample_collection.collection_id,
            file_path=nonexistent_file
        )
        assert artifact is None

    def test_get_artifact(self, artifacts_manager, sample_session, sample_collection, test_file):
        """Test getting an artifact by ID using search functionality."""
        artifact = artifacts_manager.add_artifact(
            sample_session.session_id,
            sample_collection.collection_id,
            test_file
        )
        
        # Use search to find the artifact
        found_artifacts = artifacts_manager.search_artifacts(session_id=sample_session.session_id)
        assert len(found_artifacts) == 1
        assert found_artifacts[0].artifact_id == artifact.artifact_id
        
        # Test with nonexistent session
        no_artifacts = artifacts_manager.search_artifacts(session_id="nonexistent")
        assert len(no_artifacts) == 0

    def test_list_artifacts(self, artifacts_manager, sample_session, sample_collection, test_file, temp_dir):
        """Test listing artifacts using search functionality."""
        # Initially empty
        artifacts = artifacts_manager.search_artifacts(session_id=sample_session.session_id)
        assert len(artifacts) == 0
        
        # Add artifacts
        artifact1 = artifacts_manager.add_artifact(
            sample_session.session_id,
            sample_collection.collection_id,
            test_file
        )
        
        # Create second test file
        test_file2 = temp_dir / "test_file2.log"
        test_file2.write_text("Second test file")
        
        artifact2 = artifacts_manager.add_artifact(
            sample_session.session_id,
            sample_collection.collection_id,
            test_file2
        )
        
        artifacts = artifacts_manager.search_artifacts(session_id=sample_session.session_id)
        assert len(artifacts) == 2
        
        # Check that both artifacts are found
        artifact_ids = [a.artifact_id for a in artifacts]
        assert artifact1.artifact_id in artifact_ids
        assert artifact2.artifact_id in artifact_ids

    def test_artifact_file_copying(self, artifacts_manager, sample_session, sample_collection, test_file):
        """Test that artifact files are copied to the collection directory."""
        artifact = artifacts_manager.add_artifact(
            sample_session.session_id,
            sample_collection.collection_id,
            test_file
        )
        
        # Check that file was copied
        copied_file = Path(artifact.local_path)
        assert copied_file.exists()
        assert copied_file.read_text() == test_file.read_text()
        
        # Check it's in the session directory structure
        session_dir = Path(sample_session.base_directory)
        assert str(copied_file).startswith(str(session_dir))