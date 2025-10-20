"""Tests for EventBridge integration functionality."""

import pytest
from unittest.mock import Mock, patch


class TestEventBridgeIntegration:
    """Test cases for EventBridge integration."""

    def test_eventbridge_integration(self, progress_tracker, mock_eventbridge):
        """Test EventBridge notifications are sent correctly."""
        # Start upgrade
        progress_tracker.start_upgrade("Test Phase")
        
        # Verify upgrade started notification
        mock_eventbridge.send_upgrade_started.assert_called_once_with(
            "test-upgrade-123", "test-cluster", "Test Phase"
        )

    def test_eventbridge_task_notifications(self, progress_tracker, sample_tasks, mock_eventbridge):
        """Test EventBridge task notifications."""
        progress_tracker.add_tasks(sample_tasks)
        
        # Start task
        progress_tracker.start_task("task-1")
        mock_eventbridge.send_task_started.assert_called_once()
        
        # Complete task
        progress_tracker.complete_task("task-1")
        mock_eventbridge.send_task_completed.assert_called_once()
        
        # Fail task
        progress_tracker.start_task("task-2")
        progress_tracker.fail_task("task-2", "Test error")
        mock_eventbridge.send_task_failed.assert_called_once()

    def test_eventbridge_upgrade_completion(self, progress_tracker, mock_eventbridge):
        """Test EventBridge upgrade completion notification."""
        progress_tracker.start_upgrade("Test Phase")
        progress_tracker.complete_upgrade()
        
        mock_eventbridge.send_upgrade_completed.assert_called_once()

    def test_eventbridge_upgrade_failure(self, progress_tracker, mock_eventbridge):
        """Test EventBridge upgrade failure notification."""
        progress_tracker.start_upgrade("Test Phase")
        progress_tracker.fail_upgrade("Test error")
        
        mock_eventbridge.send_upgrade_failed.assert_called_once()

    @patch('src.eks_upgrade_agent.common.progress.tracker.EventBridgeNotifier')
    def test_eventbridge_notification_failure_handling(self, mock_eb_class, mock_logger, tmp_path):
        """Test handling of EventBridge notification failures."""
        # Setup mock to fail
        mock_instance = Mock()
        mock_instance.send_upgrade_started.side_effect = Exception("EventBridge error")
        mock_eb_class.return_value = mock_instance
        
        # Create tracker (should handle EventBridge failure gracefully)
        from src.eks_upgrade_agent.common.progress.tracker import ProgressTracker
        tracker = ProgressTracker("test-upgrade", "test-plan", "test-cluster", storage_path=str(tmp_path))
        
        # This should not raise an exception
        tracker.start_upgrade("Test Phase")
        
        # Verify error was logged
        mock_logger.error.assert_called()

    def test_eventbridge_disabled_scenario(self, mock_logger, tmp_path):
        """Test behavior when EventBridge is disabled."""
        with patch('src.eks_upgrade_agent.common.progress.tracker.EventBridgeNotifier') as mock_eb:
            # Simulate EventBridge being disabled/unavailable
            mock_eb.return_value = None
            
            from src.eks_upgrade_agent.common.progress.tracker import ProgressTracker
            tracker = ProgressTracker("test-upgrade", "test-plan", "test-cluster", storage_path=str(tmp_path))
            
            # Should work without EventBridge
            tracker.start_upgrade("Test Phase")
            assert tracker.progress.status.value == "in_progress"