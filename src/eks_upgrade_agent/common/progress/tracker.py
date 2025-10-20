"""
Main progress tracker implementation.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..models.progress import (
    ProgressEvent,
    ProgressStatus,
    TaskProgress,
    TaskType,
    UpgradeProgress,
)
from .storage import ProgressStorage
from .eventbridge_notifier import EventBridgeNotifier
from .callback_manager import CallbackManager
from .websocket_server import WebSocketServer

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Main progress tracking system with modular components.
    
    Features:
    - Real-time progress updates
    - WebSocket-based status streaming
    - AWS EventBridge integration for notifications
    - Persistent progress storage
    - Event callbacks and hooks
    """
    
    def __init__(
        self,
        upgrade_id: str,
        plan_id: str,
        cluster_name: str,
        storage_path: Optional[Union[str, Path]] = None,
        eventbridge_bus_name: Optional[str] = None,
        aws_region: str = "us-east-1",
        enable_websocket: bool = False,
        websocket_port: int = 8765
    ):
        """
        Initialize the progress tracker.
        
        Args:
            upgrade_id: Unique upgrade identifier
            plan_id: Associated upgrade plan ID
            cluster_name: Target cluster name
            storage_path: Local storage path for progress data
            eventbridge_bus_name: EventBridge bus name for notifications
            aws_region: AWS region for EventBridge
            enable_websocket: Enable WebSocket server for real-time updates
            websocket_port: WebSocket server port
        """
        self.upgrade_id = upgrade_id
        self.plan_id = plan_id
        self.cluster_name = cluster_name
        
        # Initialize progress tracking
        self.progress = UpgradeProgress(
            upgrade_id=upgrade_id,
            plan_id=plan_id,
            cluster_name=cluster_name
        )
        
        # Initialize components
        storage_path = storage_path or "./data"
        self.storage = ProgressStorage(storage_path, upgrade_id)
        self.notifier = EventBridgeNotifier(eventbridge_bus_name, aws_region)
        self.callbacks = CallbackManager()
        self.websocket = WebSocketServer(
            port=websocket_port,
            enabled=enable_websocket
        )
        
        # Set up WebSocket progress provider
        self.websocket.set_progress_summary_provider(self.get_progress_summary)
        
        # Load existing progress if available
        existing_progress = self.storage.load_progress()
        if existing_progress:
            self.progress = existing_progress
        
        logger.info(f"ProgressTracker initialized for upgrade {upgrade_id}")
    
    def start_upgrade(self, phase: str = "Initialization") -> None:
        """Start tracking the upgrade process."""
        self.progress.start_upgrade(phase)
        self.storage.save_progress(self.progress)
        
        # Send notification (with error handling)
        try:
            if self.notifier:
                self.notifier.send_upgrade_started(self.upgrade_id, self.cluster_name, phase)
        except Exception as e:
            logger.error(f"Failed to send upgrade started notification: {e}")
        
        logger.info(f"Started upgrade tracking for {self.upgrade_id}")
    
    def complete_upgrade(self) -> None:
        """Complete the upgrade process."""
        self.progress.complete_upgrade()
        self.storage.save_progress(self.progress)
        
        # Send notification (with error handling)
        try:
            if self.notifier:
                duration_str = str(self.progress.duration) if self.progress.duration else None
                self.notifier.send_upgrade_completed(self.upgrade_id, self.cluster_name, duration_str)
        except Exception as e:
            logger.error(f"Failed to send upgrade completed notification: {e}")
        
        logger.info(f"Completed upgrade tracking for {self.upgrade_id}")
    
    def fail_upgrade(self, error_message: str) -> None:
        """Mark upgrade as failed."""
        self.progress.fail_upgrade(error_message)
        self.storage.save_progress(self.progress)
        
        # Send notification (with error handling)
        try:
            if self.notifier:
                self.notifier.send_upgrade_failed(self.upgrade_id, self.cluster_name, error_message)
        except Exception as e:
            logger.error(f"Failed to send upgrade failed notification: {e}")
        
        logger.error(f"Upgrade {self.upgrade_id} failed: {error_message}")
    
    def add_task(
        self,
        task_id: str,
        task_name: str,
        task_type: TaskType,
        parent_task_id: Optional[str] = None
    ) -> TaskProgress:
        """Add a new task to track."""
        task = self.progress.add_task(task_id, task_name, task_type, parent_task_id)
        self.storage.save_progress(self.progress)
        
        logger.debug(f"Added task {task_id}: {task_name}")
        return task
    
    def add_tasks(self, tasks: list[TaskProgress]) -> None:
        """Add multiple tasks to track."""
        for task in tasks:
            self.progress.add_task(
                task.task_id, 
                task.task_name, 
                task.task_type, 
                task.parent_task_id
            )
        self.storage.save_progress(self.progress)
        
        logger.debug(f"Added {len(tasks)} tasks")
    
    def start_task(self, task_id: str, message: str = "Task started") -> Optional[ProgressEvent]:
        """Start a task."""
        task = self.progress.get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return None
        
        event = task.start(message)
        self.storage.save_progress(self.progress)
        self._notify_event(event)
        self.callbacks.notify_status_change(task)
        
        # Send EventBridge notification
        try:
            if self.notifier:
                self.notifier.send_task_started(self.upgrade_id, self.cluster_name, task_id, task.task_name)
        except Exception as e:
            logger.error(f"Failed to send task started notification: {e}")
        
        logger.info(f"Started task {task_id}: {message}")
        return event
    
    def complete_task(self, task_id: str, message: str = "Task completed") -> Optional[ProgressEvent]:
        """Complete a task."""
        task = self.progress.get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return None
        
        event = task.complete(message)
        
        # Recalculate overall progress
        self._update_overall_progress()
        
        self.storage.save_progress(self.progress)
        self._notify_event(event)
        self.callbacks.notify_status_change(task)
        
        # Send EventBridge notification
        try:
            if self.notifier:
                duration_str = str(task.duration) if task.duration else None
                self.notifier.send_task_completed(self.upgrade_id, self.cluster_name, task_id, task.task_name, duration_str)
        except Exception as e:
            logger.error(f"Failed to send task completed notification: {e}")
        
        logger.info(f"Completed task {task_id}: {message}")
        return event
    
    def fail_task(self, task_id: str, error_message: str) -> Optional[ProgressEvent]:
        """Mark a task as failed."""
        task = self.progress.get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return None
        
        event = task.fail(error_message)
        self.storage.save_progress(self.progress)
        self._notify_event(event)
        self.callbacks.notify_status_change(task)
        
        # Send EventBridge notification
        try:
            if self.notifier:
                self.notifier.send_task_failed(self.upgrade_id, self.cluster_name, task_id, task.task_name, error_message)
        except Exception as e:
            logger.error(f"Failed to send task failed notification: {e}")
        
        logger.error(f"Task {task_id} failed: {error_message}")
        return event
    
    def update_task_progress(
        self,
        task_id: str,
        percentage: float,
        message: str,
        **details
    ) -> Optional[ProgressEvent]:
        """Update task progress."""
        task = self.progress.get_task(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
            return None
        
        event = task.update_progress(percentage, message, **details)
        
        # Recalculate overall progress
        self._update_overall_progress()
        
        self.storage.save_progress(self.progress)
        self._notify_event(event)
        
        logger.debug(f"Updated task {task_id} progress: {percentage}% - {message}")
        return event
    
    def set_current_phase(self, phase: str) -> None:
        """Set the current upgrade phase."""
        self.progress.current_phase = phase
        self.storage.save_progress(self.progress)
        
        # Send notification
        self.notifier.send_phase_changed(self.upgrade_id, self.cluster_name, phase)
        
        logger.info(f"Upgrade phase changed to: {phase}")
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get a summary of the current progress."""
        active_tasks = self.progress.get_active_tasks()
        failed_tasks = self.progress.get_failed_tasks()
        completed_tasks = self.progress.get_completed_tasks()
        
        # Get current task (most recent active or failed task)
        current_task = None
        if active_tasks:
            current_task = {
                "task_id": active_tasks[0].task_id,
                "task_name": active_tasks[0].task_name,
                "status": active_tasks[0].status.value.upper(),
                "percentage": active_tasks[0].percentage
            }
        elif failed_tasks:
            current_task = {
                "task_id": failed_tasks[-1].task_id,
                "task_name": failed_tasks[-1].task_name,
                "status": failed_tasks[-1].status.value.upper(),
                "percentage": failed_tasks[-1].percentage
            }
        
        return {
            "upgrade_id": self.upgrade_id,
            "cluster_name": self.cluster_name,
            "status": self.progress.status.value.upper(),
            "overall_percentage": self.progress.overall_percentage,
            "progress_percentage": self.progress.overall_percentage,  # Alias for compatibility
            "current_phase": self.progress.current_phase,
            "current_task": current_task,
            "started_at": self.progress.started_at,
            "duration": str(self.progress.duration) if self.progress.duration else None,
            "total_tasks": len(self.progress.tasks),
            "active_tasks": len(active_tasks),
            "failed_tasks": len(failed_tasks),
            "completed_tasks": len(completed_tasks),
            "active_task_names": [task.task_name for task in active_tasks],
            "failed_task_names": [task.task_name for task in failed_tasks]
        }
    
    def get_task_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed progress for a specific task."""
        task = self.progress.get_task(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "task_name": task.task_name,
            "task_type": task.task_type,
            "status": task.status,
            "percentage": task.percentage,
            "current_step": task.current_step,
            "completed_steps": task.completed_steps,
            "total_steps": task.total_steps,
            "started_at": task.started_at,
            "duration": str(task.duration) if task.duration else None,
            "error_message": task.error_message,
            "recent_events": [
                {
                    "timestamp": event.timestamp,
                    "status": event.status,
                    "message": event.message,
                    "percentage": event.percentage
                }
                for event in task.events[-5:]  # Last 5 events
            ]
        }
    
    def calculate_progress_percentage(self) -> float:
        """Calculate overall progress percentage."""
        return self.progress.overall_percentage
    
    def get_current_task(self) -> Optional[TaskProgress]:
        """Get the currently active task."""
        active_tasks = self.progress.get_active_tasks()
        return active_tasks[0] if active_tasks else None
    
    def get_estimated_completion_time(self) -> Optional[str]:
        """Get estimated completion time based on current progress."""
        if not self.progress.started_at:
            return None
        
        # If no progress yet, return None
        if self.progress.overall_percentage <= 0:
            return None
        
        # Simple estimation based on current progress rate
        from datetime import datetime, timedelta
        now = datetime.now()
        started_at = self.progress.started_at.replace(tzinfo=None) if self.progress.started_at.tzinfo else self.progress.started_at
        elapsed = now - started_at
        
        if self.progress.overall_percentage > 0:
            total_estimated = elapsed * (100 / self.progress.overall_percentage)
            remaining = total_estimated - elapsed
            estimated_completion = now + remaining
            return estimated_completion.isoformat()
        
        return None
    
    # Callback management methods
    def add_event_callback(self, callback) -> None:
        """Add a callback for progress events."""
        self.callbacks.add_event_callback(callback)
    
    def add_status_callback(self, status: ProgressStatus, callback) -> None:
        """Add a callback for specific status changes."""
        self.callbacks.add_status_callback(status, callback)
    
    # WebSocket server methods
    async def start_websocket_server(self) -> bool:
        """Start WebSocket server for real-time updates."""
        return await self.websocket.start()
    
    async def stop_websocket_server(self) -> None:
        """Stop WebSocket server."""
        await self.websocket.stop()
    
    def _notify_event(self, event: ProgressEvent) -> None:
        """Notify event callbacks and WebSocket clients."""
        # Call event callbacks
        self.callbacks.notify_event(event)
        
        # Send to WebSocket clients
        if self.websocket.get_client_count() > 0:
            asyncio.create_task(self.websocket.broadcast_event(event))
    
    def _update_overall_progress(self) -> None:
        """Update overall progress percentage based on task completion."""
        if not self.progress.tasks:
            return
        
        total_percentage = sum(task.percentage for task in self.progress.tasks.values())
        self.progress.overall_percentage = min(100.0, total_percentage / len(self.progress.tasks))
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get information about the progress tracking system."""
        return {
            "upgrade_id": self.upgrade_id,
            "plan_id": self.plan_id,
            "cluster_name": self.cluster_name,
            "storage": self.storage.get_storage_info(),
            "eventbridge": {
                "enabled": self.notifier.is_enabled(),
                "bus_name": self.notifier.bus_name
            },
            "websocket": self.websocket.get_server_info(),
            "callbacks": self.callbacks.get_callback_counts()
        }
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        # Stop WebSocket server
        if self.websocket.is_running():
            asyncio.create_task(self.websocket.stop())
        
        # Clear callbacks
        self.callbacks.clear_all_callbacks()
        
        logger.info(f"ProgressTracker cleanup completed for upgrade {self.upgrade_id}")