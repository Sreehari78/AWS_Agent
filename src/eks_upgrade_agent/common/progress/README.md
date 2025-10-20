# Progress Tracking System

A modular progress tracking system for real-time upgrade monitoring with WebSocket streaming and AWS EventBridge notifications.

## Architecture

The progress tracking system is organized into focused, maintainable modules:

```
progress/
├── __init__.py              # Module exports
├── tracker.py               # Main ProgressTracker class
├── storage.py               # Persistent storage management
├── eventbridge_notifier.py  # AWS EventBridge integration
├── callback_manager.py      # Event callback system
├── websocket_server.py      # Real-time WebSocket streaming
└── README.md               # This documentation
```

## Components

### ProgressTracker (`tracker.py`)

Main orchestrator that coordinates all components:

- Task and upgrade lifecycle management
- Progress summary and reporting
- Component coordination and cleanup

### ProgressStorage (`storage.py`)

Handles persistent storage of progress data:

- JSON-based local storage
- Automatic file management
- Error handling and recovery

### EventBridgeNotifier (`eventbridge_notifier.py`)

AWS EventBridge integration for notifications:

- Structured event publishing
- Multiple event types (started, completed, failed, phase_changed)
- Error handling and fallback

### CallbackManager (`callback_manager.py`)

Event callback system:

- Event callback registration
- Status-specific callbacks
- Safe callback execution with error handling

### WebSocketServer (`websocket_server.py`)

Real-time progress streaming:

- WebSocket server for live updates
- Client connection management
- Automatic cleanup of disconnected clients

## Usage

### Basic Usage

```python
from eks_upgrade_agent.common.progress import ProgressTracker
from eks_upgrade_agent.common.models.progress import TaskType

# Initialize tracker
tracker = ProgressTracker(
    upgrade_id="upgrade-123",
    plan_id="plan-456",
    cluster_name="my-cluster",
    storage_path="./data",
    eventbridge_bus_name="upgrade-events",
    enable_websocket=True
)

# Start upgrade
tracker.start_upgrade("Initialization")

# Add and manage tasks
task = tracker.add_task("task-1", "Deploy Infrastructure", TaskType.UPGRADE_STEP)
tracker.start_task("task-1")
tracker.update_task_progress("task-1", 50.0, "Half complete")
tracker.complete_task("task-1")

# Complete upgrade
tracker.complete_upgrade()
```

### WebSocket Integration

```python
import asyncio

# Start WebSocket server
await tracker.start_websocket_server()

# Clients can connect to ws://localhost:8765
# Server automatically broadcasts progress events
```

### Event Callbacks

```python
# Add event callback
def on_progress(event):
    print(f"Progress: {event.message}")

tracker.add_event_callback(on_progress)

# Add status-specific callback
def on_completion(task):
    print(f"Task completed: {task.task_name}")

tracker.add_status_callback(ProgressStatus.COMPLETED, on_completion)
```

### Component Access

```python
# Access individual components
storage_info = tracker.storage.get_storage_info()
is_eventbridge_enabled = tracker.notifier.is_enabled()
websocket_info = tracker.websocket.get_server_info()
callback_counts = tracker.callbacks.get_callback_counts()
```

## Benefits of Modular Design

### Maintainability

- **Single Responsibility**: Each module has a focused purpose
- **Clear Interfaces**: Well-defined boundaries between components
- **Easy Testing**: Individual components can be tested in isolation

### Readability

- **Organized Code**: Related functionality grouped together
- **Smaller Files**: Each file is focused and manageable
- **Clear Dependencies**: Import structure shows component relationships

### Extensibility

- **Pluggable Components**: Easy to replace or extend individual components
- **New Features**: Add new notification channels or storage backends
- **Configuration**: Enable/disable components as needed

### Testability

- **Unit Testing**: Test each component independently
- **Mocking**: Mock individual components for integration tests
- **Isolation**: Test failures are easier to diagnose

## Configuration

### Storage Configuration

```python
# Custom storage path
tracker = ProgressTracker(
    upgrade_id="upgrade-123",
    plan_id="plan-456",
    cluster_name="my-cluster",
    storage_path="/custom/path"
)

# Access storage component
tracker.storage.save_progress(tracker.progress)
```

### EventBridge Configuration

```python
# EventBridge settings
tracker = ProgressTracker(
    upgrade_id="upgrade-123",
    plan_id="plan-456",
    cluster_name="my-cluster",
    eventbridge_bus_name="my-event-bus",
    aws_region="us-west-2"
)

# Check if enabled
if tracker.notifier.is_enabled():
    print("EventBridge notifications enabled")
```

### WebSocket Configuration

```python
# WebSocket settings
tracker = ProgressTracker(
    upgrade_id="upgrade-123",
    plan_id="plan-456",
    cluster_name="my-cluster",
    enable_websocket=True,
    websocket_port=9000
)

# Start server
await tracker.start_websocket_server()
```

## Error Handling

Each component includes comprehensive error handling:

- **Graceful Degradation**: Components continue working when others fail
- **Logging**: Detailed error logging with context
- **Fallbacks**: Local storage when cloud services unavailable
- **Recovery**: Automatic recovery from transient failures

## Testing

The modular design enables comprehensive testing:

```bash
# Run all progress tracker tests
python -m pytest tests/unit/test_progress_tracker.py -v

# Test individual components
python -m pytest tests/unit/test_progress_storage.py -v
python -m pytest tests/unit/test_eventbridge_notifier.py -v
```

## Migration from Monolithic Design

The modular design maintains full backward compatibility:

```python
# Old import (still works)
from eks_upgrade_agent.common import ProgressTracker

# New import (recommended)
from eks_upgrade_agent.common.progress import ProgressTracker

# All existing APIs remain the same
tracker = ProgressTracker(...)
tracker.start_upgrade()
tracker.add_task(...)
```

## Future Enhancements

The modular design enables easy future enhancements:

1. **New Storage Backends**: Add database or cloud storage
2. **Additional Notifiers**: Add Slack, email, or SMS notifications
3. **Enhanced WebSocket**: Add authentication and channels
4. **Metrics Integration**: Add Prometheus or CloudWatch metrics
5. **Dashboard Integration**: Connect to web-based dashboards
