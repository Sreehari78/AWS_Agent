"""
Unit tests for the ProgressTracker class.
"""

import json
import tempfile
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.eks_upgrade_agent.common.progress import ProgressTracker
from src.eks_upgrade_agent.common.models.progress import (
    ProgressStatus,
    TaskType,
    UpgradeProgress,
)


class TestProgressTracker:
    """Test cases for ProgressTracker."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def progress_tracker(self, temp_dir):
        """Create a ProgressTracker instance for testing."""
        return ProgressTracker(
            upgrade_id="test-upgrade-123",
            plan_id="test-plan-456",
            cluster_name="test-cluster",
            storage_path=temp_dir,
            eventbridge_bus_name="test-bus",
            enable_websocket=False
        )
    
    def test_initialization(self, progress_tracker, temp_dir):
        """Test ProgressTracker initialization."""
        assert progress_tracker.upgrade_id == "test-upgrade-123"
        assert progress_tracker.plan_id == "test-plan-456"
        assert progress_tracker.cluster_name == "test-cluster"
        assert progress_tracker.storage.storage_path == temp_dir
        assert progress_tracker.notifier.bus_name == "test-bus"
        
        # Check that progress object is initialized
        assert isinstance(progress_tracker.progress, UpgradeProgress)
        assert progress_tracker.progress.upgrade_id == "test-upgrade-123"
        assert progress_tracker.progress.plan_id == "test-plan-456"
        assert progress_tracker.progress.cluster_name == "test-cluster"
    
    def test_start_upgrade(self, progress_tracker):
        """Test starting upgrade tracking."""
        with patch.object(progress_tracker.notifier, 'send_upgrade_started') as mock_notify:
            progress_tracker.start_upgrade("Test Phase")
            
            assert progress_tracker.progress.status == ProgressStatus.IN_PROGRESS
            assert progress_tracker.progress.current_phase == "Test Phase"
            assert progress_tracker.progress.started_at is not None
            
            # Check EventBridge notification
            mock_notify.assert_called_once_with("test-upgrade-123", "test-cluster", "Test Phase")
    
    def test_complete_upgrade(self, progress_tracker):
        """Test completing upgrade tracking."""
        # Start upgrade first
        progress_tracker.start_upgrade()
        
        with patch.object(progress_tracker.notifier, 'send_upgrade_completed') as mock_notify:
            progress_tracker.complete_upgrade()
            
            assert progress_tracker.progress.status == ProgressStatus.COMPLETED
            assert progress_tracker.progress.completed_at is not None
            assert progress_tracker.progress.overall_percentage == 100.0
            
            # Check EventBridge notification
            mock_notify.assert_called_once()
            args = mock_notify.call_args[0]
            assert args[0] == "test-upgrade-123"
            assert args[1] == "test-cluster"
    
    def test_fail_upgrade(self, progress_tracker):
        """Test failing upgrade tracking."""
        error_message = "Test error occurred"
        
        with patch.object(progress_tracker.notifier, 'send_upgrade_failed') as mock_notify:
            progress_tracker.fail_upgrade(error_message)
            
            assert progress_tracker.progress.status == ProgressStatus.FAILED
            assert progress_tracker.progress.metadata["error_message"] == error_message
            
            # Check EventBridge notification
            mock_notify.assert_called_once_with("test-upgrade-123", "test-cluster", error_message)
    
    def test_add_task(self, progress_tracker):
        """Test adding a task."""
        task = progress_tracker.add_task(
            task_id="task-1",
            task_name="Test Task",
            task_type=TaskType.UPGRADE_STEP
        )
        
        assert task.task_id == "task-1"
        assert task.task_name == "Test Task"
        assert task.task_type == TaskType.UPGRADE_STEP
        assert task.status == ProgressStatus.NOT_STARTED
        
        # Check task is in progress object
        assert "task-1" in progress_tracker.progress.tasks
        assert progress_tracker.progress.tasks["task-1"] == task
    
    def test_start_task(self, progress_tracker):
        """Test starting a task."""
        # Add task first
        progress_tracker.add_task("task-1", "Test Task", TaskType.UPGRADE_STEP)
        
        event = progress_tracker.start_task("task-1", "Starting test task")
        
        assert event is not None
        assert event.task_id == "task-1"
        assert event.status == ProgressStatus.IN_PROGRESS
        assert event.message == "Starting test task"
        
        # Check task status
        task = progress_tracker.progress.get_task("task-1")
        assert task.status == ProgressStatus.IN_PROGRESS
        assert task.started_at is not None
    
    def test_complete_task(self, progress_tracker):
        """Test completing a task."""
        # Add and start task first
        progress_tracker.add_task("task-1", "Test Task", TaskType.UPGRADE_STEP)
        progress_tracker.start_task("task-1")
        
        event = progress_tracker.complete_task("task-1", "Task completed successfully")
        
        assert event is not None
        assert event.status == ProgressStatus.COMPLETED
        assert event.message == "Task completed successfully"
        
        # Check task status
        task = progress_tracker.progress.get_task("task-1")
        assert task.status == ProgressStatus.COMPLETED
        assert task.completed_at is not None
        assert task.percentage == 100.0
    
    def test_fail_task(self, progress_tracker):
        """Test failing a task."""
        # Add and start task first
        progress_tracker.add_task("task-1", "Test Task", TaskType.UPGRADE_STEP)
        progress_tracker.start_task("task-1")
        
        error_message = "Task failed due to error"
        event = progress_tracker.fail_task("task-1", error_message)
        
        assert event is not None
        assert event.status == ProgressStatus.FAILED
        assert "Task failed: " + error_message in event.message
        
        # Check task status
        task = progress_tracker.progress.get_task("task-1")
        assert task.status == ProgressStatus.FAILED
        assert task.error_message == error_message
    
    def test_update_task_progress(self, progress_tracker):
        """Test updating task progress."""
        # Add and start task first
        progress_tracker.add_task("task-1", "Test Task", TaskType.UPGRADE_STEP)
        progress_tracker.start_task("task-1")
        
        event = progress_tracker.update_task_progress(
            "task-1", 50.0, "Half way done", step="middle"
        )
        
        assert event is not None
        assert event.percentage == 50.0
        assert event.message == "Half way done"
        assert event.details["step"] == "middle"
        
        # Check task progress
        task = progress_tracker.progress.get_task("task-1")
        assert task.percentage == 50.0
    
    def test_set_current_phase(self, progress_tracker):
        """Test setting current phase."""
        with patch.object(progress_tracker.notifier, 'send_phase_changed') as mock_notify:
            progress_tracker.set_current_phase("Validation Phase")
            
            assert progress_tracker.progress.current_phase == "Validation Phase"
            
            # Check EventBridge notification
            mock_notify.assert_called_once_with("test-upgrade-123", "test-cluster", "Validation Phase")
    
    def test_get_progress_summary(self, progress_tracker):
        """Test getting progress summary."""
        # Add some tasks
        progress_tracker.add_task("task-1", "Active Task", TaskType.UPGRADE_STEP)
        progress_tracker.add_task("task-2", "Failed Task", TaskType.VALIDATION)
        
        progress_tracker.start_task("task-1")
        progress_tracker.fail_task("task-2", "Test error")
        
        summary = progress_tracker.get_progress_summary()
        
        assert summary["upgrade_id"] == "test-upgrade-123"
        assert summary["cluster_name"] == "test-cluster"
        assert summary["total_tasks"] == 2
        assert summary["active_tasks"] == 1
        assert summary["failed_tasks"] == 1
        assert "Active Task" in summary["active_task_names"]
        assert "Failed Task" in summary["failed_task_names"]
    
    def test_get_task_progress(self, progress_tracker):
        """Test getting task progress details."""
        # Add and update task
        progress_tracker.add_task("task-1", "Test Task", TaskType.UPGRADE_STEP)
        progress_tracker.start_task("task-1", "Starting")
        progress_tracker.update_task_progress("task-1", 25.0, "Quarter done")
        
        task_progress = progress_tracker.get_task_progress("task-1")
        
        assert task_progress is not None
        assert task_progress["task_id"] == "task-1"
        assert task_progress["task_name"] == "Test Task"
        assert task_progress["task_type"] == TaskType.UPGRADE_STEP
        assert task_progress["percentage"] == 25.0
        assert len(task_progress["recent_events"]) == 2  # start + update
    
    def test_nonexistent_task_operations(self, progress_tracker):
        """Test operations on nonexistent tasks."""
        # These should return None and log warnings
        assert progress_tracker.start_task("nonexistent") is None
        assert progress_tracker.complete_task("nonexistent") is None
        assert progress_tracker.fail_task("nonexistent", "error") is None
        assert progress_tracker.update_task_progress("nonexistent", 50.0, "msg") is None
        assert progress_tracker.get_task_progress("nonexistent") is None
    
    def test_persistence(self, progress_tracker, temp_dir):
        """Test progress persistence to disk."""
        # Add some data
        progress_tracker.start_upgrade("Test Phase")
        progress_tracker.add_task("task-1", "Test Task", TaskType.UPGRADE_STEP)
        progress_tracker.start_task("task-1")
        
        # Check that file was created
        progress_file = temp_dir / f"upgrade_{progress_tracker.upgrade_id}.json"
        assert progress_file.exists()
        
        # Check file content
        with open(progress_file, 'r') as f:
            data = json.load(f)
        
        assert data["upgrade_id"] == "test-upgrade-123"
        assert data["status"] == ProgressStatus.IN_PROGRESS
        assert "task-1" in data["tasks"]
    
    def test_load_existing_progress(self, temp_dir):
        """Test loading existing progress from disk."""
        # Create progress file manually
        upgrade_id = "existing-upgrade"
        progress_file = temp_dir / f"upgrade_{upgrade_id}.json"
        
        progress_data = {
            "upgrade_id": upgrade_id,
            "plan_id": "existing-plan",
            "cluster_name": "existing-cluster",
            "status": "in_progress",
            "current_phase": "Existing Phase",
            "tasks": {}
        }
        
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f)
        
        # Create tracker - should load existing data
        tracker = ProgressTracker(
            upgrade_id=upgrade_id,
            plan_id="existing-plan",
            cluster_name="existing-cluster",
            storage_path=temp_dir
        )
        
        assert tracker.progress.status == ProgressStatus.IN_PROGRESS
        assert tracker.progress.current_phase == "Existing Phase"
    
    def test_event_callbacks(self, progress_tracker):
        """Test event callbacks."""
        callback_events = []
        
        def event_callback(event):
            callback_events.append(event)
        
        progress_tracker.add_event_callback(event_callback)
        
        # Add and start task to generate events
        progress_tracker.add_task("task-1", "Test Task", TaskType.UPGRADE_STEP)
        progress_tracker.start_task("task-1", "Starting task")
        
        # Check that callback was called
        assert len(callback_events) == 1
        assert callback_events[0].task_id == "task-1"
        assert callback_events[0].message == "Starting task"
    
    def test_status_callbacks(self, progress_tracker):
        """Test status change callbacks."""
        completed_tasks = []
        
        def completion_callback(task):
            completed_tasks.append(task)
        
        progress_tracker.add_status_callback(ProgressStatus.COMPLETED, completion_callback)
        
        # Add, start, and complete task
        progress_tracker.add_task("task-1", "Test Task", TaskType.UPGRADE_STEP)
        progress_tracker.start_task("task-1")
        progress_tracker.complete_task("task-1")
        
        # Check that callback was called
        assert len(completed_tasks) == 1
        assert completed_tasks[0].task_id == "task-1"
        assert completed_tasks[0].status == ProgressStatus.COMPLETED
    
    @patch('boto3.client')
    def test_eventbridge_integration(self, mock_boto_client, progress_tracker):
        """Test EventBridge integration."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        # Force client creation
        progress_tracker.notifier._client = None
        client = progress_tracker.notifier.client
        
        # Start upgrade to trigger notification
        progress_tracker.start_upgrade("Test Phase")
        
        # Check that EventBridge was called
        mock_client.put_events.assert_called_once()
        call_args = mock_client.put_events.call_args[1]
        entries = call_args['Entries']
        
        assert len(entries) == 1
        entry = entries[0]
        assert entry['Source'] == 'eks-upgrade-agent'
        assert entry['DetailType'] == 'upgrade.started'
        assert entry['EventBusName'] == 'test-bus'
    
    def test_cleanup(self, progress_tracker):
        """Test cleanup functionality."""
        # Add some callbacks
        progress_tracker.add_event_callback(lambda x: None)
        progress_tracker.add_status_callback(ProgressStatus.COMPLETED, lambda x: None)
        
        # Cleanup
        progress_tracker.cleanup()
        
        # Check that callbacks were cleared
        callback_counts = progress_tracker.callbacks.get_callback_counts()
        assert callback_counts["event_callbacks"] == 0
        assert len(callback_counts["status_callbacks"]) == 0