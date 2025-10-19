"""
Progress tracking models for upgrade execution monitoring.
"""

from datetime import datetime, timedelta, UTC
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class ProgressStatus(str, Enum):
    """Progress status enumeration."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Task type enumeration."""
    UPGRADE_PLAN = "upgrade_plan"
    UPGRADE_STEP = "upgrade_step"
    VALIDATION = "validation"
    ROLLBACK = "rollback"
    CLEANUP = "cleanup"


class ProgressEvent(BaseModel):
    """Individual progress event."""
    
    model_config = ConfigDict(use_enum_values=True)
    
    event_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique event ID"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Event timestamp"
    )
    task_id: str = Field(..., description="Associated task ID")
    task_type: TaskType = Field(..., description="Type of task")
    status: ProgressStatus = Field(..., description="Progress status")
    message: str = Field(..., description="Progress message")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional event details"
    )
    percentage: Optional[float] = Field(
        None, ge=0, le=100, description="Completion percentage"
    )
    
    @field_validator("percentage")
    @classmethod
    def validate_percentage(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Percentage must be between 0 and 100")
        return v


class TaskProgress(BaseModel):
    """Progress tracking for individual tasks."""
    
    model_config = ConfigDict(use_enum_values=True)
    
    task_id: str = Field(..., description="Unique task ID")
    task_name: str = Field(..., description="Task name")
    task_type: TaskType = Field(..., description="Type of task")
    parent_task_id: Optional[str] = Field(None, description="Parent task ID")
    
    # Status tracking
    status: ProgressStatus = Field(
        default=ProgressStatus.NOT_STARTED, description="Current status"
    )
    started_at: Optional[datetime] = Field(None, description="Task start time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")
    duration: Optional[timedelta] = Field(None, description="Task duration")
    
    # Progress metrics
    percentage: float = Field(default=0.0, ge=0, le=100, description="Completion percentage")
    current_step: Optional[str] = Field(None, description="Current step description")
    total_steps: Optional[int] = Field(None, ge=0, description="Total number of steps")
    completed_steps: int = Field(default=0, ge=0, description="Completed steps")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, ge=0, description="Number of retries")
    
    # Events and logs
    events: List[ProgressEvent] = Field(
        default_factory=list, description="Progress events"
    )
    
    @model_validator(mode="after")
    def validate_progress_consistency(self):
        # Calculate duration if both timestamps are available
        if self.started_at and self.completed_at:
            self.duration = self.completed_at - self.started_at
        
        # Update percentage based on completed steps
        if self.total_steps and self.total_steps > 0:
            self.percentage = min(100.0, (self.completed_steps / self.total_steps) * 100)
        
        # Ensure status consistency
        if self.status == ProgressStatus.COMPLETED and self.percentage < 100:
            self.percentage = 100.0
        
        return self
    
    def add_event(self, status: ProgressStatus, message: str, **details) -> ProgressEvent:
        """Add a progress event."""
        event = ProgressEvent(
            task_id=self.task_id,
            task_type=self.task_type,
            status=status,
            message=message,
            details=details,
            percentage=self.percentage
        )
        self.events.append(event)
        self.status = status
        return event
    
    def start(self, message: str = "Task started") -> ProgressEvent:
        """Mark task as started."""
        self.started_at = datetime.now(UTC)
        return self.add_event(ProgressStatus.IN_PROGRESS, message)
    
    def complete(self, message: str = "Task completed") -> ProgressEvent:
        """Mark task as completed."""
        self.completed_at = datetime.now(UTC)
        self.percentage = 100.0
        return self.add_event(ProgressStatus.COMPLETED, message)
    
    def fail(self, error_message: str) -> ProgressEvent:
        """Mark task as failed."""
        self.error_message = error_message
        return self.add_event(ProgressStatus.FAILED, f"Task failed: {error_message}")
    
    def update_progress(self, percentage: float, message: str, **details) -> ProgressEvent:
        """Update task progress."""
        self.percentage = max(0, min(100, percentage))
        return self.add_event(ProgressStatus.IN_PROGRESS, message, **details)


class UpgradeProgress(BaseModel):
    """Overall upgrade progress tracking."""
    
    model_config = ConfigDict(use_enum_values=True)
    
    upgrade_id: str = Field(..., description="Unique upgrade ID")
    plan_id: str = Field(..., description="Associated plan ID")
    cluster_name: str = Field(..., description="Target cluster name")
    
    # Overall status
    status: ProgressStatus = Field(
        default=ProgressStatus.NOT_STARTED, description="Overall status"
    )
    started_at: Optional[datetime] = Field(None, description="Upgrade start time")
    completed_at: Optional[datetime] = Field(None, description="Upgrade completion time")
    duration: Optional[timedelta] = Field(None, description="Total duration")
    
    # Progress metrics
    overall_percentage: float = Field(default=0.0, ge=0, le=100, description="Overall completion")
    current_phase: Optional[str] = Field(None, description="Current phase")
    
    # Task tracking
    tasks: Dict[str, TaskProgress] = Field(
        default_factory=dict, description="Individual task progress"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    
    @model_validator(mode="after")
    def validate_upgrade_progress(self):
        # Calculate overall duration
        if self.started_at and self.completed_at:
            self.duration = self.completed_at - self.started_at
        
        # Calculate overall percentage from tasks
        if self.tasks:
            total_percentage = sum(task.percentage for task in self.tasks.values())
            self.overall_percentage = min(100.0, total_percentage / len(self.tasks))
        
        return self
    
    def add_task(self, task_id: str, task_name: str, task_type: TaskType, 
                 parent_task_id: Optional[str] = None) -> TaskProgress:
        """Add a new task to track."""
        task = TaskProgress(
            task_id=task_id,
            task_name=task_name,
            task_type=task_type,
            parent_task_id=parent_task_id
        )
        self.tasks[task_id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[TaskProgress]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def start_upgrade(self, phase: str = "Initialization") -> None:
        """Start the upgrade process."""
        self.started_at = datetime.now(UTC)
        self.status = ProgressStatus.IN_PROGRESS
        self.current_phase = phase
    
    def complete_upgrade(self) -> None:
        """Complete the upgrade process."""
        self.completed_at = datetime.now(UTC)
        self.status = ProgressStatus.COMPLETED
        self.overall_percentage = 100.0
    
    def fail_upgrade(self, error_message: str) -> None:
        """Mark upgrade as failed."""
        self.status = ProgressStatus.FAILED
        self.metadata["error_message"] = error_message
    
    def get_active_tasks(self) -> List[TaskProgress]:
        """Get all currently active tasks."""
        return [
            task for task in self.tasks.values()
            if task.status == ProgressStatus.IN_PROGRESS
        ]
    
    def get_failed_tasks(self) -> List[TaskProgress]:
        """Get all failed tasks."""
        return [
            task for task in self.tasks.values()
            if task.status == ProgressStatus.FAILED
        ]