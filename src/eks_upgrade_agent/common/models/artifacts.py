"""
Test artifacts models for organizing test outputs and logs.
"""

from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class ArtifactType(str, Enum):
    """Artifact type enumeration."""
    LOG_FILE = "log_file"
    TEST_RESULT = "test_result"
    CONFIGURATION = "configuration"
    SCREENSHOT = "screenshot"
    METRICS_DATA = "metrics_data"
    BACKUP = "backup"
    REPORT = "report"
    DIAGNOSTIC = "diagnostic"


class ArtifactStatus(str, Enum):
    """Artifact status enumeration."""
    CREATED = "created"
    UPLOADED = "uploaded"
    ARCHIVED = "archived"
    DELETED = "deleted"
    FAILED = "failed"


class ArtifactTestData(BaseModel):
    """Individual test artifact."""
    
    model_config = ConfigDict(use_enum_values=True)
    
    artifact_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique artifact ID"
    )
    name: str = Field(..., description="Artifact name")
    description: Optional[str] = Field(None, description="Artifact description")
    artifact_type: ArtifactType = Field(..., description="Type of artifact")
    
    # File information
    local_path: str = Field(..., description="Local file path")
    file_size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    file_hash: Optional[str] = Field(None, description="File hash (SHA256)")
    
    # Storage information
    s3_bucket: Optional[str] = Field(None, description="S3 bucket name")
    s3_key: Optional[str] = Field(None, description="S3 object key")
    s3_url: Optional[str] = Field(None, description="S3 URL")
    
    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    uploaded_at: Optional[datetime] = Field(None, description="Upload timestamp")
    status: ArtifactStatus = Field(
        default=ArtifactStatus.CREATED, description="Artifact status"
    )
    
    # Context information
    task_id: Optional[str] = Field(None, description="Associated task ID")
    step_id: Optional[str] = Field(None, description="Associated step ID")
    upgrade_id: Optional[str] = Field(None, description="Associated upgrade ID")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    tags: List[str] = Field(default_factory=list, description="Artifact tags")
    
    @field_validator("local_path")
    @classmethod
    def validate_local_path(cls, v):
        if not v:
            raise ValueError("Local path cannot be empty")
        return str(Path(v).resolve())
    
    @model_validator(mode="after")
    def validate_s3_consistency(self):
        # Only validate S3 consistency if both bucket and key are provided
        # Allow partial S3 configuration for gradual setup
        if self.s3_bucket and self.s3_key and not self.s3_url:
            # Generate S3 URL if bucket and key are provided but URL is not
            pass  # URL will be set during upload
        
        return self
    
    def mark_uploaded(self, s3_url: str) -> None:
        """Mark artifact as uploaded to S3."""
        self.s3_url = s3_url
        self.uploaded_at = datetime.now(UTC)
        self.status = ArtifactStatus.UPLOADED
    
    def mark_failed(self, error_message: str) -> None:
        """Mark artifact upload as failed."""
        self.status = ArtifactStatus.FAILED
        self.metadata["error_message"] = error_message
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the artifact."""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def get_relative_path(self, base_path: Union[str, Path]) -> str:
        """Get path relative to base directory."""
        try:
            return str(Path(self.local_path).relative_to(Path(base_path)))
        except ValueError:
            return self.local_path


class ArtifactCollection(BaseModel):
    """Collection of related artifacts."""
    
    collection_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique collection ID"
    )
    name: str = Field(..., description="Collection name")
    description: Optional[str] = Field(None, description="Collection description")
    
    # Context information
    upgrade_id: Optional[str] = Field(None, description="Associated upgrade ID")
    task_id: Optional[str] = Field(None, description="Associated task ID")
    
    # Artifacts
    artifacts: List[ArtifactTestData] = Field(
        default_factory=list, description="Artifacts in collection"
    )
    
    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Creation timestamp"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Collection metadata"
    )
    
    def add_artifact(self, artifact: ArtifactTestData) -> None:
        """Add an artifact to the collection."""
        # Set context information if not already set
        if self.upgrade_id and not artifact.upgrade_id:
            artifact.upgrade_id = self.upgrade_id
        if self.task_id and not artifact.task_id:
            artifact.task_id = self.task_id
        
        self.artifacts.append(artifact)
    
    def get_artifacts_by_type(self, artifact_type: ArtifactType) -> List[ArtifactTestData]:
        """Get artifacts by type."""
        return [a for a in self.artifacts if a.artifact_type == artifact_type]
    
    def get_artifacts_by_status(self, status: ArtifactStatus) -> List[ArtifactTestData]:
        """Get artifacts by status."""
        return [a for a in self.artifacts if a.status == status]
    
    def get_total_size(self) -> int:
        """Get total size of all artifacts in bytes."""
        return sum(a.file_size or 0 for a in self.artifacts)
    
    def get_uploaded_count(self) -> int:
        """Get count of uploaded artifacts."""
        return len(self.get_artifacts_by_status(ArtifactStatus.UPLOADED))


class SessionTestData(BaseModel):
    """Test session containing multiple artifact collections."""
    
    session_id: str = Field(
        default_factory=lambda: str(uuid4()), description="Unique session ID"
    )
    name: str = Field(..., description="Session name")
    description: Optional[str] = Field(None, description="Session description")
    
    # Context information
    upgrade_id: str = Field(..., description="Associated upgrade ID")
    cluster_name: str = Field(..., description="Target cluster name")
    
    # Collections
    collections: Dict[str, ArtifactCollection] = Field(
        default_factory=dict, description="Artifact collections"
    )
    
    # Session metadata
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Session start time"
    )
    completed_at: Optional[datetime] = Field(None, description="Session completion time")
    
    # Storage configuration
    base_directory: str = Field(..., description="Base directory for artifacts")
    s3_bucket: Optional[str] = Field(None, description="S3 bucket for storage")
    s3_prefix: Optional[str] = Field(None, description="S3 key prefix")
    
    # Retention policy
    retention_days: int = Field(default=30, ge=1, description="Retention period in days")
    
    def add_collection(self, collection: ArtifactCollection) -> None:
        """Add an artifact collection to the session."""
        # Set context information
        collection.upgrade_id = self.upgrade_id
        self.collections[collection.collection_id] = collection
    
    def create_collection(self, name: str, description: Optional[str] = None, 
                         task_id: Optional[str] = None) -> ArtifactCollection:
        """Create a new artifact collection."""
        collection = ArtifactCollection(
            name=name,
            description=description,
            upgrade_id=self.upgrade_id,
            task_id=task_id
        )
        self.add_collection(collection)
        return collection
    
    def get_collection(self, collection_id: str) -> Optional[ArtifactCollection]:
        """Get a collection by ID."""
        return self.collections.get(collection_id)
    
    def get_all_artifacts(self) -> List[ArtifactTestData]:
        """Get all artifacts from all collections."""
        artifacts = []
        for collection in self.collections.values():
            artifacts.extend(collection.artifacts)
        return artifacts
    
    def get_total_size(self) -> int:
        """Get total size of all artifacts in the session."""
        return sum(collection.get_total_size() for collection in self.collections.values())
    
    def complete_session(self) -> None:
        """Mark the session as completed."""
        self.completed_at = datetime.now(UTC)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the session."""
        all_artifacts = self.get_all_artifacts()
        
        return {
            "session_id": self.session_id,
            "name": self.name,
            "upgrade_id": self.upgrade_id,
            "cluster_name": self.cluster_name,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "collections_count": len(self.collections),
            "total_artifacts": len(all_artifacts),
            "total_size_bytes": self.get_total_size(),
            "uploaded_artifacts": len([a for a in all_artifacts if a.status == ArtifactStatus.UPLOADED]),
            "artifact_types": {
                artifact_type.value: len([a for a in all_artifacts if a.artifact_type == artifact_type])
                for artifact_type in ArtifactType
            }
        }