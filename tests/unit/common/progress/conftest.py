"""Shared fixtures for progress tracker tests."""

from unittest.mock import Mock, patch
import pytest

from src.eks_upgrade_agent.common.progress.tracker import ProgressTracker
from src.eks_upgrade_agent.common.models.progress import TaskProgress, TaskType, ProgressStatus


@pytest.fixture
def mock_logger():
    """Mock logger to avoid logging issues in tests."""
    with patch('src.eks_upgrade_agent.common.progress.tracker.logger') as mock_log:
        # Configure mock to handle level comparisons
        mock_log.level = 20  # INFO level
        mock_log.error = Mock()
        mock_log.warning = Mock()
        mock_log.info = Mock()
        mock_log.debug = Mock()
        yield mock_log


@pytest.fixture
def mock_eventbridge():
    """Mock EventBridge notifier."""
    with patch('src.eks_upgrade_agent.common.progress.tracker.EventBridgeNotifier') as mock_eb:
        mock_instance = Mock()
        mock_instance.send_upgrade_started.return_value = True
        mock_instance.send_upgrade_completed.return_value = True
        mock_instance.send_upgrade_failed.return_value = True
        mock_instance.send_task_started.return_value = True
        mock_instance.send_task_completed.return_value = True
        mock_instance.send_task_failed.return_value = True
        mock_instance.is_enabled.return_value = True
        mock_eb.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def progress_tracker(mock_logger, mock_eventbridge, tmp_path):
    """Create a ProgressTracker instance for testing."""
    # Use temporary path to avoid loading existing progress data
    return ProgressTracker(
        upgrade_id="test-upgrade-123",
        plan_id="test-plan-123",
        cluster_name="test-cluster",
        storage_path=str(tmp_path),
        eventbridge_bus_name="test-bus"
    )


@pytest.fixture
def sample_tasks():
    """Create sample task progress objects."""
    return [
        TaskProgress(
            task_id="task-1",
            task_name="First Task",
            task_type=TaskType.UPGRADE_STEP
        ),
        TaskProgress(
            task_id="task-2", 
            task_name="Second Task",
            task_type=TaskType.UPGRADE_STEP
        ),
        TaskProgress(
            task_id="task-3",
            task_name="Third Task", 
            task_type=TaskType.VALIDATION
        )
    ]