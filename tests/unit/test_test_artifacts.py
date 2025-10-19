"""
Unit tests for the TestArtifactsManager class.
"""

import json
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.eks_upgrade_agent.common.artifacts import TestArtifactsManager
from src.eks_upgrade_agent.common.models.artifacts import (
    ArtifactStatus,
    ArtifactType,
    TestArtifact,
    TestSession,
)


class TestTestArtifactsManager:
    """Test cases for TestArtifactsManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def artifacts_manager(self, temp_dir):
        """Create a TestArtifactsManager instance for testing."""
        return TestArtifactsManager(
            base_directory=temp_dir,
            s3_bucket="test-bucket",
            s3_prefix="test-prefix",
            retention_days=7,
            auto_upload=False
        )
    
    @pytest.fixture
    def test_file(self, temp_dir):
        """Create a test file for artifact testing."""
        test_file = temp_dir / "test_file.log"
        test_file.write_text("This is a test log file\nwith multiple lines\n")
        return test_file
    
    def test_initialization(self, artifacts_manager, temp_dir):
        """Test TestArtifactsManager initialization."""
        assert artifacts_manager.base_directory == temp_dir
        assert artifacts_manager.s3_bucket == "test-bucket"
        assert artifacts_manager.s3_prefix == "test-prefix"
        assert artifacts_manager.session_manager.retention_days == 7
        assert artifacts_manager.auto_upload is False
        
        # Check that base directory exists
        assert temp_dir.exists()
        assert temp_dir.is_dir()
    
    def test_create_session(self, artifacts_manager):
        """Test creating a test session."""
        session = artifacts_manager.create_session(
            upgrade_id="upgrade-123",
            cluster_name="test-cluster",
            session_name="Test Session",
            description="Test session description"
        )
        
        assert isinstance(session, TestSession)
        assert session.upgrade_id == "upgrade-123"
        assert session.cluster_name == "test-cluster"
        assert session.name == "Test Session"
        assert session.description == "Test session description"
        assert session.s3_bucket == "test-bucket"
        
        # Check session is stored
        assert session.session_id in artifacts_manager.session_manager._sessions
        
        # Check session directory was created
        session_dir = Path(session.base_directory)
        assert session_dir.exists()
        assert session_dir.is_dir()
    
    def test_get_session(self, artifacts_manager):
        """Test getting a session by ID."""
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        session_id = session.session_id
        
        retrieved_session = artifacts_manager.get_session(session_id)
        assert retrieved_session == session
        
        # Test nonexistent session
        assert artifacts_manager.get_session("nonexistent") is None
    
    def test_create_collection(self, artifacts_manager):
        """Test creating an artifact collection."""
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        
        collection = artifacts_manager.create_collection(
            session_id=session.session_id,
            collection_name="Test Collection",
            description="Test collection description",
            task_id="task-456"
        )
        
        assert collection is not None
        assert collection.name == "Test Collection"
        assert collection.description == "Test collection description"
        assert collection.task_id == "task-456"
        assert collection.upgrade_id == "upgrade-123"
        
        # Check collection is in session
        assert collection.collection_id in session.collections
    
    def test_create_collection_invalid_session(self, artifacts_manager):
        """Test creating collection with invalid session ID."""
        collection = artifacts_manager.create_collection(
            session_id="nonexistent",
            collection_name="Test Collection"
        )
        
        assert collection is None
    
    def test_add_artifact(self, artifacts_manager, test_file):
        """Test adding an artifact to a collection."""
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        collection = artifacts_manager.create_collection(
            session_id=session.session_id,
            collection_name="Test Collection"
        )
        
        artifact = artifacts_manager.add_artifact(
            session_id=session.session_id,
            collection_id=collection.collection_id,
            file_path=test_file,
            artifact_name="Test Log",
            artifact_type=ArtifactType.LOG_FILE,
            description="Test log file",
            task_id="task-789",
            tags=["test", "log"]
        )
        
        assert artifact is not None
        assert artifact.name == "Test Log"
        assert artifact.artifact_type == ArtifactType.LOG_FILE
        assert artifact.description == "Test log file"
        assert artifact.task_id == "task-789"
        assert artifact.upgrade_id == "upgrade-123"
        assert "test" in artifact.tags
        assert "log" in artifact.tags
        assert artifact.file_size > 0
        assert artifact.file_hash is not None
        
        # Check artifact is in collection
        assert artifact in collection.artifacts
        
        # Check file was copied to session directory
        session_dir = Path(session.base_directory)
        copied_file = Path(artifact.local_path)
        assert copied_file.exists()
        assert copied_file.is_relative_to(session_dir)
    
    def test_add_artifact_invalid_session(self, artifacts_manager, test_file):
        """Test adding artifact with invalid session ID."""
        artifact = artifacts_manager.add_artifact(
            session_id="nonexistent",
            collection_id="collection-123",
            file_path=test_file
        )
        
        assert artifact is None
    
    def test_add_artifact_invalid_collection(self, artifacts_manager, test_file):
        """Test adding artifact with invalid collection ID."""
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        
        artifact = artifacts_manager.add_artifact(
            session_id=session.session_id,
            collection_id="nonexistent",
            file_path=test_file
        )
        
        assert artifact is None
    
    def test_add_artifact_nonexistent_file(self, artifacts_manager):
        """Test adding artifact with nonexistent file."""
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        collection = artifacts_manager.create_collection(
            session_id=session.session_id,
            collection_name="Test Collection"
        )
        
        artifact = artifacts_manager.add_artifact(
            session_id=session.session_id,
            collection_id=collection.collection_id,
            file_path="/nonexistent/file.log"
        )
        
        assert artifact is None
    
    @patch('boto3.client')
    def test_upload_artifact(self, mock_boto_client, artifacts_manager, test_file):
        """Test uploading an artifact to S3."""
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        
        # Create session and artifact
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        collection = artifacts_manager.create_collection(
            session_id=session.session_id,
            collection_name="Test Collection"
        )
        artifact = artifacts_manager.add_artifact(
            session_id=session.session_id,
            collection_id=collection.collection_id,
            file_path=test_file,
            artifact_name="Test Log"
        )
        
        # Force S3 client creation
        artifacts_manager._s3_client = mock_s3_client
        
        # Upload artifact
        result = artifacts_manager.upload_artifact(session.session_id, artifact.artifact_id)
        
        assert result is True
        assert artifact.status == ArtifactStatus.UPLOADED
        assert artifact.s3_url is not None
        assert artifact.uploaded_at is not None
        
        # Check S3 upload was called
        mock_s3_client.upload_file.assert_called_once()
        call_args = mock_s3_client.upload_file.call_args
        assert call_args[0][0] == artifact.local_path  # local file
        assert call_args[0][1] == artifact.s3_bucket   # bucket
        assert call_args[0][2] == artifact.s3_key      # key
    
    def test_upload_artifact_no_s3_client(self, artifacts_manager, test_file):
        """Test uploading artifact without S3 client."""
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        collection = artifacts_manager.create_collection(
            session_id=session.session_id,
            collection_name="Test Collection"
        )
        artifact = artifacts_manager.add_artifact(
            session_id=session.session_id,
            collection_id=collection.collection_id,
            file_path=test_file
        )
        
        # Ensure no S3 client
        artifacts_manager._s3_client = None
        artifacts_manager.s3_bucket = None
        
        result = artifacts_manager.upload_artifact(session.session_id, artifact.artifact_id)
        
        assert result is False
    
    @patch('boto3.client')
    def test_upload_session_artifacts(self, mock_boto_client, artifacts_manager, test_file, temp_dir):
        """Test uploading all artifacts in a session."""
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client
        artifacts_manager._s3_client = mock_s3_client
        
        # Create session with multiple artifacts
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        collection = artifacts_manager.create_collection(
            session_id=session.session_id,
            collection_name="Test Collection"
        )
        
        # Create additional test file
        test_file2 = temp_dir / "test_file2.log"
        test_file2.write_text("Another test file")
        
        artifact1 = artifacts_manager.add_artifact(
            session_id=session.session_id,
            collection_id=collection.collection_id,
            file_path=test_file,
            artifact_name="Test Log 1"
        )
        
        artifact2 = artifacts_manager.add_artifact(
            session_id=session.session_id,
            collection_id=collection.collection_id,
            file_path=test_file2,
            artifact_name="Test Log 2"
        )
        
        # Upload all artifacts
        results = artifacts_manager.upload_session_artifacts(session.session_id)
        
        assert len(results) == 2
        assert all(results.values())  # All uploads successful
        assert artifact1.status == ArtifactStatus.UPLOADED
        assert artifact2.status == ArtifactStatus.UPLOADED
        
        # Check S3 upload was called twice
        assert mock_s3_client.upload_file.call_count == 2
    
    def test_complete_session(self, artifacts_manager):
        """Test completing a test session."""
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        
        result = artifacts_manager.complete_session(session.session_id)
        
        assert result is True
        assert session.completed_at is not None
    
    def test_complete_session_invalid(self, artifacts_manager):
        """Test completing invalid session."""
        result = artifacts_manager.complete_session("nonexistent")
        
        assert result is False
    
    def test_get_session_summary(self, artifacts_manager, test_file):
        """Test getting session summary."""
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        collection = artifacts_manager.create_collection(
            session_id=session.session_id,
            collection_name="Test Collection"
        )
        artifacts_manager.add_artifact(
            session_id=session.session_id,
            collection_id=collection.collection_id,
            file_path=test_file
        )
        
        summary = artifacts_manager.get_session_summary(session.session_id)
        
        assert summary is not None
        assert summary["session_id"] == session.session_id
        assert summary["upgrade_id"] == "upgrade-123"
        assert summary["cluster_name"] == "test-cluster"
        assert summary["collections_count"] == 1
        assert summary["total_artifacts"] == 1
        assert summary["total_size_bytes"] > 0
    
    def test_search_artifacts(self, artifacts_manager, test_file, temp_dir):
        """Test searching for artifacts."""
        # Create session with multiple artifacts
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        collection = artifacts_manager.create_collection(
            session_id=session.session_id,
            collection_name="Test Collection"
        )
        
        # Create different types of artifacts
        test_file2 = temp_dir / "test_report.json"
        test_file2.write_text('{"test": "data"}')
        
        artifact1 = artifacts_manager.add_artifact(
            session_id=session.session_id,
            collection_id=collection.collection_id,
            file_path=test_file,
            artifact_type=ArtifactType.LOG_FILE,
            task_id="task-1",
            tags=["test", "log"]
        )
        
        artifact2 = artifacts_manager.add_artifact(
            session_id=session.session_id,
            collection_id=collection.collection_id,
            file_path=test_file2,
            artifact_type=ArtifactType.REPORT,
            task_id="task-2",
            tags=["test", "report"]
        )
        
        # Search by type
        log_artifacts = artifacts_manager.search_artifacts(artifact_type=ArtifactType.LOG_FILE)
        assert len(log_artifacts) == 1
        assert log_artifacts[0] == artifact1
        
        # Search by task ID
        task1_artifacts = artifacts_manager.search_artifacts(task_id="task-1")
        assert len(task1_artifacts) == 1
        assert task1_artifacts[0] == artifact1
        
        # Search by tags
        test_artifacts = artifacts_manager.search_artifacts(tags=["test"])
        assert len(test_artifacts) == 2
        
        log_tag_artifacts = artifacts_manager.search_artifacts(tags=["test", "log"])
        assert len(log_tag_artifacts) == 1
        assert log_tag_artifacts[0] == artifact1
        
        # Search by session
        session_artifacts = artifacts_manager.search_artifacts(session_id=session.session_id)
        assert len(session_artifacts) == 2
    
    def test_cleanup_expired_sessions(self, artifacts_manager, temp_dir):
        """Test cleaning up expired sessions."""
        # Create a session and complete it
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        artifacts_manager.complete_session(session.session_id)
        
        # Manually set completion time to past retention period
        from datetime import timedelta
        session.completed_at = datetime.now(UTC) - timedelta(days=artifacts_manager.session_manager.retention_days + 1)
        artifacts_manager.session_manager._save_session(session)
        
        # Check session directory exists
        session_dir = Path(session.base_directory)
        assert session_dir.exists()
        
        # Cleanup expired sessions
        cleaned = artifacts_manager.cleanup_expired_sessions()
        
        assert session.session_id in cleaned
        assert session.session_id not in artifacts_manager.session_manager._sessions
        
        # Check session directory was removed
        assert not session_dir.exists()
    
    def test_persistence(self, artifacts_manager):
        """Test session persistence to disk."""
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        
        # Check session file was created
        session_file = artifacts_manager.base_directory / f"session_{session.session_id}.json"
        assert session_file.exists()
        
        # Check file content
        with open(session_file, 'r') as f:
            data = json.load(f)
        
        assert data["session_id"] == session.session_id
        assert data["upgrade_id"] == "upgrade-123"
        assert data["cluster_name"] == "test-cluster"
    
    def test_load_existing_sessions(self, temp_dir):
        """Test loading existing sessions from disk."""
        # Create session file manually
        session_id = "existing-session"
        session_file = temp_dir / f"session_{session_id}.json"
        
        session_data = {
            "session_id": session_id,
            "name": "Existing Session",
            "upgrade_id": "existing-upgrade",
            "cluster_name": "existing-cluster",
            "base_directory": str(temp_dir / session_id),
            "collections": {},
            "retention_days": 30
        }
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, default=str)
        
        # Create manager - should load existing session
        manager = TestArtifactsManager(base_directory=temp_dir)
        
        assert session_id in manager.session_manager._sessions
        session = manager.session_manager._sessions[session_id]
        assert session.name == "Existing Session"
        assert session.upgrade_id == "existing-upgrade"
    
    def test_file_hash_calculation(self, artifacts_manager, test_file):
        """Test file hash calculation."""
        hash_value = artifacts_manager.file_handler.calculate_file_hash(str(test_file))
        
        assert hash_value is not None
        assert len(hash_value) == 64  # SHA256 hex digest length
        
        # Hash should be consistent
        hash_value2 = artifacts_manager.file_handler.calculate_file_hash(str(test_file))
        assert hash_value == hash_value2
    
    def test_cleanup(self, artifacts_manager):
        """Test cleanup functionality."""
        # Create some sessions
        session1 = artifacts_manager.create_session("upgrade-1", "cluster-1")
        session2 = artifacts_manager.create_session("upgrade-2", "cluster-2")
        
        # Cleanup
        artifacts_manager.cleanup()
        
        # Check that sessions were saved (files should exist)
        session1_file = artifacts_manager.session_manager.base_directory / f"session_{session1.session_id}.json"
        session2_file = artifacts_manager.session_manager.base_directory / f"session_{session2.session_id}.json"
        
        assert session1_file.exists()
        assert session2_file.exists()