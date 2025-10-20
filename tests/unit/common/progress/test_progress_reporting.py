"""Tests for progress reporting functionality."""

import pytest


class TestProgressReporting:
    """Test cases for progress reporting operations."""

    def test_get_progress_summary_initial(self, progress_tracker, sample_tasks):
        """Test progress summary in initial state."""
        progress_tracker.add_tasks(sample_tasks)
        
        summary = progress_tracker.get_progress_summary()
        
        assert summary["upgrade_id"] == "test-upgrade-123"
        assert summary["cluster_name"] == "test-cluster"
        assert summary["status"] == "NOT_STARTED"
        assert summary["total_tasks"] == 3
        assert summary["completed_tasks"] == 0
        assert summary["progress_percentage"] == 0.0
        assert summary["current_task"] is None

    def test_get_progress_summary_in_progress(self, progress_tracker, sample_tasks):
        """Test progress summary during upgrade."""
        progress_tracker.add_tasks(sample_tasks)
        progress_tracker.start_upgrade("Test Phase")
        progress_tracker.start_task("task-1")
        
        summary = progress_tracker.get_progress_summary()
        
        assert summary["status"] == "IN_PROGRESS"
        assert summary["current_phase"] == "Test Phase"
        assert summary["current_task"]["task_id"] == "task-1"
        assert summary["progress_percentage"] == 0.0  # No tasks completed yet

    def test_get_progress_summary_with_completed_tasks(self, progress_tracker, sample_tasks):
        """Test progress summary with some completed tasks."""
        progress_tracker.add_tasks(sample_tasks)
        progress_tracker.start_upgrade("Test Phase")
        
        # Complete first task
        progress_tracker.start_task("task-1")
        progress_tracker.complete_task("task-1")
        
        # Start second task
        progress_tracker.start_task("task-2")
        
        summary = progress_tracker.get_progress_summary()
        
        assert summary["completed_tasks"] == 1
        assert abs(summary["progress_percentage"] - 33.33) < 0.1  # 1/3 * 100
        assert summary["current_task"]["task_id"] == "task-2"

    def test_get_progress_summary_with_failed_task(self, progress_tracker, sample_tasks):
        """Test progress summary with failed task."""
        progress_tracker.add_tasks(sample_tasks)
        progress_tracker.start_upgrade("Test Phase")
        
        # Start and fail a task
        progress_tracker.start_task("task-1")
        progress_tracker.complete_task("task-1")
        progress_tracker.start_task("task-2")
        progress_tracker.fail_task("task-2", "Test error")
        
        summary = progress_tracker.get_progress_summary()
        
        assert summary["completed_tasks"] == 1
        assert summary["failed_tasks"] == 1
        assert summary["current_task"]["status"] == "FAILED"

    def test_calculate_progress_percentage(self, progress_tracker, sample_tasks):
        """Test progress percentage calculation."""
        progress_tracker.add_tasks(sample_tasks)
        
        # No tasks completed
        assert progress_tracker.calculate_progress_percentage() == 0.0
        
        # Complete one task
        progress_tracker.start_task("task-1")
        progress_tracker.complete_task("task-1")
        assert abs(progress_tracker.calculate_progress_percentage() - 33.33) < 0.1
        
        # Complete two tasks
        progress_tracker.start_task("task-2")
        progress_tracker.complete_task("task-2")
        assert abs(progress_tracker.calculate_progress_percentage() - 66.67) < 0.1
        
        # Complete all tasks
        progress_tracker.start_task("task-3")
        progress_tracker.complete_task("task-3")
        assert progress_tracker.calculate_progress_percentage() == 100.0

    def test_get_current_task(self, progress_tracker, sample_tasks):
        """Test getting current task."""
        progress_tracker.add_tasks(sample_tasks)
        
        # No current task initially
        assert progress_tracker.get_current_task() is None
        
        # Start first task
        progress_tracker.start_task("task-1")
        current = progress_tracker.get_current_task()
        assert current.task_id == "task-1"
        
        # Complete first task, start second
        progress_tracker.complete_task("task-1")
        progress_tracker.start_task("task-2")
        current = progress_tracker.get_current_task()
        assert current.task_id == "task-2"

    def test_get_estimated_completion_time(self, progress_tracker, sample_tasks):
        """Test estimated completion time calculation."""
        progress_tracker.add_tasks(sample_tasks)
        
        # Should return None if no tasks started
        assert progress_tracker.get_estimated_completion_time() is None
        
        # Start upgrade and first task
        progress_tracker.start_upgrade("Test Phase")
        progress_tracker.start_task("task-1")
        
        # Make some progress to enable estimation
        progress_tracker.update_task_progress("task-1", 50.0, "Half way done")
        
        # Should return a datetime object
        estimated = progress_tracker.get_estimated_completion_time()
        assert estimated is not None

    def test_progress_summary_serialization(self, progress_tracker, sample_tasks):
        """Test that progress summary can be serialized to JSON."""
        progress_tracker.add_tasks(sample_tasks)
        progress_tracker.start_upgrade("Test Phase")
        progress_tracker.start_task("task-1")
        
        summary = progress_tracker.get_progress_summary()
        
        # Should be JSON serializable
        import json
        json_str = json.dumps(summary, default=str)
        assert json_str is not None
        
        # Should be deserializable
        deserialized = json.loads(json_str)
        assert deserialized["upgrade_id"] == "test-upgrade-123"