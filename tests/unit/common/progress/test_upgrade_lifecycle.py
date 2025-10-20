"""Tests for upgrade lifecycle management."""

import pytest
from datetime import datetime, UTC

from src.eks_upgrade_agent.common.models.progress import ProgressStatus


class TestUpgradeLifecycle:
    """Test cases for upgrade lifecycle operations."""

    def test_initialization(self, progress_tracker):
        """Test ProgressTracker initialization."""
        assert progress_tracker.upgrade_id == "test-upgrade-123"
        assert progress_tracker.plan_id == "test-plan-123"
        assert progress_tracker.cluster_name == "test-cluster"
        assert progress_tracker.progress.status == ProgressStatus.NOT_STARTED
        assert len(progress_tracker.progress.tasks) == 0

    def test_start_upgrade(self, progress_tracker, mock_eventbridge):
        """Test starting an upgrade."""
        phase = "Test Phase"
        progress_tracker.start_upgrade(phase)
        
        assert progress_tracker.progress.status == ProgressStatus.IN_PROGRESS
        assert progress_tracker.progress.current_phase == phase
        assert progress_tracker.progress.started_at is not None
        assert isinstance(progress_tracker.progress.started_at, datetime)
        
        # Verify EventBridge notification
        mock_eventbridge.send_upgrade_started.assert_called_once_with(
            "test-upgrade-123", "test-cluster", phase
        )

    def test_complete_upgrade_success(self, progress_tracker, mock_eventbridge):
        """Test successful upgrade completion."""
        # Start upgrade first
        progress_tracker.start_upgrade("Test Phase")
        
        # Complete upgrade
        progress_tracker.complete_upgrade()
        
        assert progress_tracker.progress.status == ProgressStatus.COMPLETED
        assert progress_tracker.progress.completed_at is not None
        assert isinstance(progress_tracker.progress.completed_at, datetime)
        assert progress_tracker.progress.overall_percentage == 100.0
        
        # Verify EventBridge notification
        mock_eventbridge.send_upgrade_completed.assert_called_once()

    def test_fail_upgrade(self, progress_tracker, mock_eventbridge):
        """Test upgrade failure."""
        # Start upgrade first
        progress_tracker.start_upgrade("Test Phase")
        
        error_message = "Test error occurred"
        progress_tracker.fail_upgrade(error_message)
        
        assert progress_tracker.progress.status == ProgressStatus.FAILED
        assert progress_tracker.progress.metadata["error_message"] == error_message
        
        # Verify EventBridge notification
        mock_eventbridge.send_upgrade_failed.assert_called_once()

    def test_upgrade_duration_calculation(self, progress_tracker):
        """Test upgrade duration calculation."""
        # Before starting
        assert progress_tracker.progress.duration is None
        
        # Start upgrade
        progress_tracker.start_upgrade("Test Phase")
        
        # Complete upgrade
        progress_tracker.complete_upgrade()
        
        # Duration should be calculated
        assert progress_tracker.progress.duration is not None
        assert progress_tracker.progress.duration.total_seconds() >= 0

    def test_upgrade_status_transitions(self, progress_tracker):
        """Test valid upgrade status transitions."""
        # Initial state
        assert progress_tracker.progress.status == ProgressStatus.NOT_STARTED
        
        # Start upgrade
        progress_tracker.start_upgrade("Test Phase")
        assert progress_tracker.progress.status == ProgressStatus.IN_PROGRESS
        
        # Complete upgrade
        progress_tracker.complete_upgrade()
        assert progress_tracker.progress.status == ProgressStatus.COMPLETED

    def test_upgrade_failure_from_in_progress(self, progress_tracker):
        """Test upgrade failure from in-progress state."""
        # Start upgrade
        progress_tracker.start_upgrade("Test Phase")
        assert progress_tracker.progress.status == ProgressStatus.IN_PROGRESS
        
        # Fail upgrade
        progress_tracker.fail_upgrade("Test error")
        assert progress_tracker.progress.status == ProgressStatus.FAILED