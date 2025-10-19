# Progress Tracking and Test Artifacts Management

This document describes the progress tracking and test artifacts management system implemented for the EKS Upgrade Agent.

## Overview

The system provides two main components:

1. **ProgressTracker**: Real-time progress monitoring with WebSocket streaming and EventBridge notifications
2. **TestArtifactsManager**: Organized test artifact storage with AWS S3 integration for distributed teams

## Features

### Progress Tracking Features

- **Real-time Progress Updates**: Track upgrade progress with detailed task-level monitoring
- **WebSocket Streaming**: Optional WebSocket server for real-time status updates
- **AWS EventBridge Integration**: Send notifications for key upgrade events
- **Persistent Storage**: Save progress data to local storage for recovery
- **Event Callbacks**: Register callbacks for progress events and status changes
- **Hierarchical Task Management**: Support for parent-child task relationships

### Test Artifacts Features

- **Organized Storage**: Structured artifact organization with sessions and collections
- **AWS S3 Integration**: Upload artifacts to S3 for distributed team access
- **File Management**: Automatic file copying, hashing, and metadata generation
- **Search Capabilities**: Search artifacts by type, tags, task ID, and status
- **Retention Policies**: Automatic cleanup of expired artifacts
- **Multiple Artifact Types**: Support for logs, reports, configurations, and more

## Architecture

### Progress Tracking Architecture

```
ProgressTracker
├── UpgradeProgress (main progress object)
│   ├── TaskProgress (individual tasks)
│   │   └── ProgressEvent (task events)
│   └── Metadata (upgrade context)
├── WebSocket Server (optional)
├── EventBridge Client (AWS notifications)
└── Local Storage (persistence)
```

### Test Artifacts Architecture

```
TestArtifactsManager
├── TestSession (upgrade session)
│   ├── ArtifactCollection (grouped artifacts)
│   │   └── TestArtifact (individual files)
│   └── Session Metadata
├── S3 Client (cloud storage)
└── Local Storage (file management)
```

## Usage Examples

### Basic Progress Tracking

```python
from eks_upgrade_agent.common.progress_tracker import ProgressTracker
from eks_upgrade_agent.common.models.progress import TaskType

# Initialize progress tracker
tracker = ProgressTracker(
    upgrade_id="upgrade-123",
    plan_id="plan-456",
    cluster_name="my-cluster",
    storage_path="./progress",
    eventbridge_bus_name="upgrade-events"
)

# Start upgrade
tracker.start_upgrade("Initialization")

# Add and track tasks
task = tracker.add_task("task-1", "Deploy Infrastructure", TaskType.UPGRADE_STEP)
tracker.start_task("task-1", "Starting infrastructure deployment")
tracker.update_task_progress("task-1", 50.0, "Half way complete")
tracker.complete_task("task-1", "Infrastructure deployed successfully")

# Complete upgrade
tracker.complete_upgrade()
```

### Basic Test Artifacts Management

```python
from eks_upgrade_agent.common.test_artifacts import TestArtifactsManager
from eks_upgrade_agent.common.models.artifacts import ArtifactType

# Initialize artifacts manager
manager = TestArtifactsManager(
    base_directory="./artifacts",
    s3_bucket="my-artifacts-bucket",
    s3_prefix="eks-upgrades",
    auto_upload=True
)

# Create session and collection
session = manager.create_session("upgrade-123", "my-cluster")
collection = manager.create_collection(
    session.session_id,
    "Upgrade Logs",
    task_id="task-1"
)

# Add artifacts
artifact = manager.add_artifact(
    session_id=session.session_id,
    collection_id=collection.collection_id,
    file_path="/path/to/log.txt",
    artifact_type=ArtifactType.LOG_FILE,
    tags=["upgrade", "infrastructure"]
)

# Upload to S3
manager.upload_artifact(session.session_id, artifact.artifact_id)
```

### Event Callbacks

```python
# Add event callback for all progress events
def on_progress_event(event):
    print(f"Progress: {event.message} ({event.percentage}%)")

tracker.add_event_callback(on_progress_event)

# Add status-specific callbacks
def on_task_completed(task):
    print(f"Task completed: {task.task_name}")

tracker.add_status_callback(ProgressStatus.COMPLETED, on_task_completed)
```

### WebSocket Integration

```python
import asyncio

# Enable WebSocket server
tracker = ProgressTracker(
    upgrade_id="upgrade-123",
    plan_id="plan-456",
    cluster_name="my-cluster",
    enable_websocket=True,
    websocket_port=8765
)

# Start WebSocket server
await tracker.start_websocket_server()

# Clients can connect to ws://localhost:8765 for real-time updates
```

### Artifact Search

```python
# Search by artifact type
log_files = manager.search_artifacts(
    artifact_type=ArtifactType.LOG_FILE
)

# Search by tags
test_artifacts = manager.search_artifacts(
    tags=["test", "validation"]
)

# Search by task ID
task_artifacts = manager.search_artifacts(
    task_id="task-1"
)

# Combined search
specific_artifacts = manager.search_artifacts(
    session_id=session.session_id,
    artifact_type=ArtifactType.REPORT,
    tags=["performance"],
    status=ArtifactStatus.UPLOADED
)
```

## Data Models

### Progress Models

- **ProgressStatus**: Enumeration of progress states (not_started, in_progress, completed, failed, etc.)
- **TaskType**: Enumeration of task types (upgrade_plan, upgrade_step, validation, rollback, cleanup)
- **ProgressEvent**: Individual progress event with timestamp, message, and details
- **TaskProgress**: Progress tracking for individual tasks with events and metrics
- **UpgradeProgress**: Overall upgrade progress with task collection and summary

### Artifact Models

- **ArtifactType**: Enumeration of artifact types (log_file, test_result, configuration, etc.)
- **ArtifactStatus**: Enumeration of artifact states (created, uploaded, archived, deleted, failed)
- **TestArtifact**: Individual artifact with metadata, file information, and S3 details
- **ArtifactCollection**: Collection of related artifacts with grouping metadata
- **TestSession**: Session containing multiple collections for an upgrade

## AWS Integration

### EventBridge Notifications

The ProgressTracker sends notifications to EventBridge for key events:

- `upgrade.started`: When upgrade tracking begins
- `upgrade.completed`: When upgrade completes successfully
- `upgrade.failed`: When upgrade fails
- `upgrade.phase_changed`: When upgrade phase changes

Event structure:

```json
{
  "Source": "eks-upgrade-agent",
  "DetailType": "upgrade.started",
  "Detail": {
    "upgrade_id": "upgrade-123",
    "cluster_name": "my-cluster",
    "phase": "Initialization"
  }
}
```

### S3 Storage

The TestArtifactsManager integrates with S3 for distributed artifact storage:

- Automatic file uploads with metadata
- Organized S3 key structure: `{prefix}/{session_id}/{collection_id}/{filename}`
- File metadata stored as S3 object metadata
- Support for pre-signed URLs and access control

## Configuration

### Progress Tracker Configuration

```python
tracker = ProgressTracker(
    upgrade_id="unique-upgrade-id",
    plan_id="associated-plan-id",
    cluster_name="target-cluster",
    storage_path="./progress",           # Local storage path
    eventbridge_bus_name="event-bus",   # EventBridge bus name
    aws_region="us-east-1",             # AWS region
    enable_websocket=True,              # Enable WebSocket server
    websocket_port=8765                 # WebSocket port
)
```

### Test Artifacts Manager Configuration

```python
manager = TestArtifactsManager(
    base_directory="./artifacts",       # Local storage directory
    s3_bucket="artifacts-bucket",       # S3 bucket name
    s3_prefix="eks-upgrades",          # S3 key prefix
    aws_region="us-east-1",            # AWS region
    retention_days=30,                 # Retention period
    auto_upload=False                  # Auto-upload to S3
)
```

## Error Handling

Both components include comprehensive error handling:

- **Graceful Degradation**: Continue operation when optional features fail
- **Retry Logic**: Automatic retries for transient failures
- **Error Logging**: Detailed error logging with context
- **Fallback Mechanisms**: Local storage when cloud services are unavailable

## Performance Considerations

- **Efficient Storage**: Minimal memory footprint with streaming for large files
- **Batch Operations**: Batch uploads and operations for better performance
- **Connection Pooling**: Reuse AWS client connections
- **Async Support**: Async/await support for non-blocking operations

## Security

- **Credential Management**: Secure AWS credential handling
- **Access Control**: S3 bucket policies and IAM integration
- **Data Encryption**: Encryption in transit and at rest
- **Audit Logging**: Comprehensive audit trails for all operations

## Testing

The implementation includes comprehensive unit tests:

- **Progress Tracker Tests**: 19 test cases covering all functionality
- **Test Artifacts Tests**: 21 test cases covering all functionality
- **Mock Integration**: Proper mocking of AWS services
- **Edge Cases**: Testing of error conditions and edge cases

Run tests with:

```bash
python -m pytest tests/unit/test_progress_tracker.py -v
python -m pytest tests/unit/test_test_artifacts.py -v
```

## Example Application

See `examples/progress_tracking_example.py` for a complete working example that demonstrates:

- Progress tracking setup and usage
- Test artifacts management
- Event callbacks
- Search functionality
- Integration between components

## Future Enhancements

Potential future improvements:

1. **Real-time Dashboard**: Web-based dashboard for progress monitoring
2. **Advanced Analytics**: Progress analytics and reporting
3. **Multi-cluster Support**: Track progress across multiple clusters
4. **Integration APIs**: REST APIs for external system integration
5. **Advanced Search**: Full-text search capabilities for artifacts
6. **Compression**: Automatic artifact compression for storage efficiency
