# Test Artifacts Management System

This module provides a modular test artifacts management system for organizing test outputs, logs, and other files generated during EKS upgrade operations.

## Architecture

The system is broken down into focused, single-responsibility modules:

```
artifacts/
├── __init__.py           # Package exports
├── manager.py            # Main TestArtifactsManager (simplified)
├── session_manager.py    # Session and collection management
├── file_handler.py       # File operations and utilities
├── s3_client.py         # AWS S3 integration
├── search_engine.py     # Artifact search capabilities
└── README.md            # This file
```

## Components

### 1. TestArtifactsManager (`manager.py`)

- **Purpose**: Main coordinator class that orchestrates all other components
- **Responsibilities**:
  - Initialize and coordinate sub-components
  - Provide simplified public API
  - Handle auto-upload logic
- **Size**: ~200 lines (down from 500+)

### 2. SessionManager (`session_manager.py`)

- **Purpose**: Manage test sessions and artifact collections
- **Responsibilities**:
  - Create and manage test sessions
  - Handle artifact collections within sessions
  - Session persistence and loading
  - Retention policy enforcement

### 3. FileHandler (`file_handler.py`)

- **Purpose**: Handle all file system operations
- **Responsibilities**:
  - File copying and organization
  - Hash calculation and file metadata
  - Directory cleanup operations
  - File size and integrity checks

### 4. S3ArtifactClient (`s3_client.py`)

- **Purpose**: AWS S3 integration for cloud storage
- **Responsibilities**:
  - Upload/download artifacts to/from S3
  - S3 metadata management
  - S3 object existence checks
  - Error handling for S3 operations

### 5. ArtifactSearchEngine (`search_engine.py`)

- **Purpose**: Advanced search and filtering capabilities
- **Responsibilities**:
  - Multi-criteria artifact search
  - Name pattern matching
  - Size-based filtering
  - Statistics and analytics

## Benefits of Modularization

### ✅ **Improved Readability**

- Each file has a single, clear purpose
- Functions are focused and easier to understand
- Reduced cognitive load when working with specific functionality

### ✅ **Better Maintainability**

- Changes to S3 logic don't affect file handling
- Search improvements don't impact session management
- Easier to add new features without touching unrelated code

### ✅ **Enhanced Testability**

- Each component can be tested in isolation
- Mock dependencies more easily
- Focused unit tests for specific functionality

### ✅ **Reusability**

- Components can be used independently
- S3Client could be reused for other storage needs
- FileHandler useful for other file operations

### ✅ **Parallel Development**

- Different team members can work on different components
- Reduced merge conflicts
- Clear interfaces between components

## Usage Examples

### Basic Usage (Same API)

```python
from eks_upgrade_agent.common.artifacts import TestArtifactsManager

# Usage remains exactly the same
manager = TestArtifactsManager(
    base_directory="./artifacts",
    s3_bucket="my-bucket",
    auto_upload=True
)

session = manager.create_session("upgrade-123", "my-cluster")
collection = manager.create_collection(session.session_id, "Logs")
artifact = manager.add_artifact(
    session.session_id,
    collection.collection_id,
    "/path/to/log.txt"
)
```

### Advanced Usage (Access to Components)

```python
# Direct access to components for advanced use cases
file_handler = manager.file_handler
s3_client = manager.s3_client
search_engine = manager.search_engine

# Advanced search
recent_logs = search_engine.get_recent_artifacts(hours=6)
large_files = search_engine.get_artifacts_by_size_range(min_size=1024*1024)  # > 1MB
stats = search_engine.get_artifact_statistics()

# Direct S3 operations
success = s3_client.upload_artifact(artifact)
exists = s3_client.check_artifact_exists(artifact)

# File operations
hash_value = file_handler.calculate_file_hash("/path/to/file")
```

## Migration from Monolithic Version

The public API remains **100% compatible**. Existing code will work without changes:

```python
# This still works exactly the same
manager = TestArtifactsManager(base_directory="./artifacts")
session = manager.create_session("upgrade-123", "cluster")
# ... rest of the code unchanged
```

## Testing Strategy

Each component has focused unit tests:

```bash
# Test individual components
pytest tests/unit/test_file_handler.py
pytest tests/unit/test_s3_client.py
pytest tests/unit/test_session_manager.py
pytest tests/unit/test_search_engine.py

# Test integration
pytest tests/unit/test_test_artifacts.py  # Tests the main manager
```

## Performance Benefits

- **Reduced Memory Usage**: Only load components when needed
- **Faster Imports**: Smaller modules load faster
- **Better Caching**: Component-level caching opportunities
- **Parallel Operations**: Components can work independently

## Future Enhancements

The modular structure makes it easy to add new features:

- **New Storage Backends**: Add Azure Blob or GCS clients
- **Advanced Search**: Add full-text search capabilities
- **Compression**: Add artifact compression in FileHandler
- **Encryption**: Add encryption in S3Client
- **Monitoring**: Add metrics collection in each component

## Component Dependencies

```
TestArtifactsManager
├── SessionManager
├── FileHandler
├── S3ArtifactClient
└── ArtifactSearchEngine
    └── SessionManager._sessions (read-only)
```

Each component has minimal dependencies and clear interfaces, making the system maintainable and extensible.
