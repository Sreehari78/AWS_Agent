"""Tests for session management functionality."""

import pytest
from pathlib import Path

from src.eks_upgrade_agent.common.models.artifacts import TestSession


class TestSessionManagement:
    """Test cases for session management operations."""

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

    def test_complete_session_success(self, artifacts_manager, sample_session):
        """Test successful session completion."""
        result = artifacts_manager.complete_session(sample_session.session_id)
        assert result is True
        
        # Verify session is marked as completed
        session = artifacts_manager.get_session(sample_session.session_id)
        assert session.completed_at is not None

    def test_complete_session_invalid(self, artifacts_manager):
        """Test completing nonexistent session."""
        result = artifacts_manager.complete_session("nonexistent")
        assert result is False

    def test_list_sessions(self, artifacts_manager):
        """Test that sessions can be retrieved individually."""
        # Create sessions
        session1 = artifacts_manager.create_session("upgrade-1", "cluster-1")
        session2 = artifacts_manager.create_session("upgrade-2", "cluster-2")
        
        # Verify sessions can be retrieved
        retrieved1 = artifacts_manager.get_session(session1.session_id)
        retrieved2 = artifacts_manager.get_session(session2.session_id)
        
        assert retrieved1 is not None
        assert retrieved2 is not None
        assert retrieved1.upgrade_id == "upgrade-1"
        assert retrieved2.upgrade_id == "upgrade-2"

    def test_session_directory_creation(self, artifacts_manager, temp_dir):
        """Test that session directories are created properly."""
        session = artifacts_manager.create_session("upgrade-123", "test-cluster")
        
        session_dir = temp_dir / session.session_id
        assert session_dir.exists()
        assert session_dir.is_dir()
        
        # Session should be retrievable
        retrieved_session = artifacts_manager.get_session(session.session_id)
        assert retrieved_session is not None
        assert retrieved_session.session_id == session.session_id