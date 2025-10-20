"""Tests for task management functionality."""

import pytest
from datetime import datetime

from src.eks_upgrade_agent.common.models.progress import ProgressStatus, TaskType


class TestTaskManagement:
    """Test cases for task management operations."""

    def test_add_tasks(self, progress_tracker, sample_tasks):
        """Test adding tasks to progress tracker."""
        for task in sample_tasks:
            progress_tracker.add_task(task.task_id, task.task_name, task.task_type)
        
        assert len(progress_tracker.progress.tasks) == 3
        assert "task-1" in progress_tracker.progress.tasks
        assert "task-2" in progress_tracker.progress.tasks
        assert "task-3" in progress_tracker.progress.tasks

    def test_start_task_success(self, progress_tracker, sample_tasks, mock_eventbridge):
        """Test successful task start."""
        for task in sample_tasks:
            progress_tracker.add_task(task.task_id, task.task_name, task.task_type)
        
        event = progress_tracker.start_task("task-1")
        
        # Check task status
        task = progress_tracker.progress.get_task("task-1")
        assert task.status == ProgressStatus.IN_PROGRESS
        assert task.started_at is not None
        
        # Check event
        assert event.task_id == "task-1"
        assert event.status == ProgressStatus.IN_PROGRESS

    def test_start_nonexistent_task(self, progress_tracker):
        """Test starting nonexistent task."""
        result = progress_tracker.start_task("nonexistent")
        assert result is None

    def test_complete_task_success(self, progress_tracker, sample_tasks, mock_eventbridge):
        """Test successful task completion."""
        for task in sample_tasks:
            progress_tracker.add_task(task.task_id, task.task_name, task.task_type)
        progress_tracker.start_task("task-1")
        
        event = progress_tracker.complete_task("task-1")
        
        # Check task status
        task = progress_tracker.progress.get_task("task-1")
        assert task.status == ProgressStatus.COMPLETED
        assert task.completed_at is not None
        
        # Check event
        assert event.task_id == "task-1"
        assert event.status == ProgressStatus.COMPLETED

    def test_fail_task(self, progress_tracker, sample_tasks, mock_eventbridge):
        """Test task failure."""
        for task in sample_tasks:
            progress_tracker.add_task(task.task_id, task.task_name, task.task_type)
        progress_tracker.start_task("task-1")
        
        error_message = "Task failed due to error"
        event = progress_tracker.fail_task("task-1", error_message)
        
        # Check task status
        task = progress_tracker.progress.get_task("task-1")
        assert task.status == ProgressStatus.FAILED
        assert task.error_message == error_message
        
        # Check event
        assert event.task_id == "task-1"
        assert event.status == ProgressStatus.FAILED

    def test_get_task(self, progress_tracker, sample_tasks):
        """Test getting task by ID."""
        for task in sample_tasks:
            progress_tracker.add_task(task.task_id, task.task_name, task.task_type)
        
        task = progress_tracker.progress.get_task("task-2")
        assert task is not None
        assert task.task_id == "task-2"
        assert task.task_name == "Second Task"
        
        # Test nonexistent task
        assert progress_tracker.progress.get_task("nonexistent") is None

    def test_task_duration_calculation(self, progress_tracker, sample_tasks):
        """Test task duration calculation."""
        for task in sample_tasks:
            progress_tracker.add_task(task.task_id, task.task_name, task.task_type)
        
        # Start task
        progress_tracker.start_task("task-1")
        
        # Complete task
        progress_tracker.complete_task("task-1")
        
        task = progress_tracker.progress.get_task("task-1")
        # Duration should be calculated
        assert task.duration is not None
        assert task.duration.total_seconds() >= 0

    def test_task_status_transitions(self, progress_tracker, sample_tasks):
        """Test valid task status transitions."""
        for task in sample_tasks:
            progress_tracker.add_task(task.task_id, task.task_name, task.task_type)
        
        task = progress_tracker.progress.get_task("task-1")
        
        # Initial state
        assert task.status == ProgressStatus.NOT_STARTED
        
        # Start task
        progress_tracker.start_task("task-1")
        assert task.status == ProgressStatus.IN_PROGRESS
        
        # Complete task
        progress_tracker.complete_task("task-1")
        assert task.status == ProgressStatus.COMPLETED

    def test_multiple_task_workflow(self, progress_tracker, sample_tasks):
        """Test workflow with multiple tasks."""
        for task in sample_tasks:
            progress_tracker.add_task(task.task_id, task.task_name, task.task_type)
        
        # Complete first task
        progress_tracker.start_task("task-1")
        progress_tracker.complete_task("task-1")
        task1 = progress_tracker.progress.get_task("task-1")
        assert task1.status == ProgressStatus.COMPLETED
        
        # Complete second task
        progress_tracker.start_task("task-2")
        progress_tracker.complete_task("task-2")
        task2 = progress_tracker.progress.get_task("task-2")
        assert task2.status == ProgressStatus.COMPLETED
        
        # Complete third task
        progress_tracker.start_task("task-3")
        progress_tracker.complete_task("task-3")
        task3 = progress_tracker.progress.get_task("task-3")
        assert task3.status == ProgressStatus.COMPLETED