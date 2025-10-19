"""
Main test artifacts manager - simplified and focused.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..models.artifacts import (
    ArtifactCollection,
    ArtifactStatus,
    ArtifactType,
    TestArtifact,
    TestSession,
)
from .file_handler import FileHandler
from .s3_client import S3ArtifactClient
from .session_manager import SessionManager
from .search_engine import ArtifactSearchEngine

logger = logging.getLogger(__name__)


class TestArtifactsManager:
    """
    Main test artifacts management system with S3 integration for distributed teams.
    
    This is a simplified, focused manager that coordinates the modular components.
    """
    
    def __init__(
        self,
        base_directory: Union[str, Path],
        s3_bucket: Optional[str] = None,
        s3_prefix: Optional[str] = None,
        aws_region: str = "us-east-1",
        retention_days: int = 30,
        auto_upload: bool = False
    ):
        """
        Initialize the test artifacts manager.
        
        Args:
            base_directory: Base directory for local artifact storage
            s3_bucket: S3 bucket name for distributed storage
            s3_prefix: S3 key prefix for organization
            aws_region: AWS region for S3
            retention_days: Default retention period in days
            auto_upload: Automatically upload artifacts to S3
        """
        self.base_directory = Path(base_directory)
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix or "eks-upgrade-agent/artifacts"
        self.auto_upload = auto_upload
        
        # Initialize components
        self.file_handler = FileHandler(self.base_directory)
        self.s3_client = S3ArtifactClient(aws_region)
        self.session_manager = SessionManager(self.base_directory, retention_days)
        self.search_engine = ArtifactSearchEngine(self.session_manager._sessions)
        
        logger.info(f"TestArtifactsManager initialized with base directory: {self.base_directory}")
    
    # Session Management
    def create_session(
        self,
        upgrade_id: str,
        cluster_name: str,
        session_name: Optional[str] = None,
        description: Optional[str] = None
    ) -> TestSession:
        """Create a new test session."""
        return self.session_manager.create_session(
            upgrade_id=upgrade_id,
            cluster_name=cluster_name,
            session_name=session_name,
            description=description,
            s3_bucket=self.s3_bucket,
            s3_prefix=self.s3_prefix
        )
    
    def get_session(self, session_id: str) -> Optional[TestSession]:
        """Get a test session by ID."""
        return self.session_manager.get_session(session_id)
    
    def complete_session(self, session_id: str) -> bool:
        """Complete a test session."""
        success = self.session_manager.complete_session(session_id)
        
        # Upload all artifacts if auto-upload is enabled
        if success and self.auto_upload:
            self.upload_session_artifacts(session_id)
        
        return success
    
    # Collection Management
    def create_collection(
        self,
        session_id: str,
        collection_name: str,
        description: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Optional[ArtifactCollection]:
        """Create a new artifact collection within a session."""
        return self.session_manager.create_collection(
            session_id=session_id,
            collection_name=collection_name,
            description=description,
            task_id=task_id
        )
    
    # Artifact Management
    def add_artifact(
        self,
        session_id: str,
        collection_id: str,
        file_path: Union[str, Path],
        artifact_name: Optional[str] = None,
        artifact_type: ArtifactType = ArtifactType.LOG_FILE,
        description: Optional[str] = None,
        task_id: Optional[str] = None,
        step_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **metadata
    ) -> Optional[TestArtifact]:
        """Add an artifact to a collection."""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None
        
        collection = session.get_collection(collection_id)
        if not collection:
            logger.warning(f"Collection {collection_id} not found in session {session_id}")
            return None
        
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f"Artifact file not found: {file_path}")
            return None
        
        # Generate artifact name if not provided
        if not artifact_name:
            artifact_name = file_path.name
        
        # Copy file to session directory
        session_dir = Path(session.base_directory)
        local_path = self.file_handler.copy_file_to_session(file_path, session_dir, collection_id)
        if not local_path:
            return None
        
        # Calculate file metadata
        file_hash = self.file_handler.calculate_file_hash(local_path)
        file_size = self.file_handler.get_file_size(local_path)
        
        # Create S3 configuration
        s3_key = None
        if session.s3_bucket and session.s3_prefix:
            relative_path = Path(local_path).relative_to(session_dir)
            s3_key = f"{session.s3_prefix}/{relative_path}"
        
        # Create artifact
        artifact = TestArtifact(
            name=artifact_name,
            description=description,
            artifact_type=artifact_type,
            local_path=local_path,
            file_size=file_size,
            file_hash=file_hash,
            s3_bucket=session.s3_bucket,
            s3_key=s3_key,
            task_id=task_id,
            step_id=step_id,
            upgrade_id=session.upgrade_id,
            metadata=metadata,
            tags=tags or []
        )
        
        collection.add_artifact(artifact)
        self.session_manager._save_session(session)
        
        # Auto-upload if enabled
        if self.auto_upload and self.s3_client.s3_client:
            self.upload_artifact(session_id, artifact.artifact_id)
        
        logger.info(f"Added artifact {artifact.artifact_id}: {artifact_name}")
        return artifact
    
    # S3 Operations
    def upload_artifact(self, session_id: str, artifact_id: str) -> bool:
        """Upload an artifact to S3."""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return False
        
        # Find artifact
        artifact = self._find_artifact_in_session(session, artifact_id)
        if not artifact:
            logger.warning(f"Artifact {artifact_id} not found in session {session_id}")
            return False
        
        success = self.s3_client.upload_artifact(artifact)
        if success:
            self.session_manager._save_session(session)
        
        return success
    
    def upload_session_artifacts(self, session_id: str) -> Dict[str, bool]:
        """Upload all artifacts in a session to S3."""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return {}
        
        results = {}
        for collection in session.collections.values():
            for artifact in collection.artifacts:
                if artifact.status == ArtifactStatus.CREATED:
                    results[artifact.artifact_id] = self.s3_client.upload_artifact(artifact)
        
        # Save session after all uploads
        self.session_manager._save_session(session)
        
        logger.info(f"Uploaded {sum(results.values())} of {len(results)} artifacts for session {session_id}")
        return results
    
    # Search Operations
    def search_artifacts(self, **criteria) -> List[TestArtifact]:
        """Search for artifacts based on criteria."""
        return self.search_engine.search_artifacts(**criteria)
    
    def search_by_name(self, name_pattern: str, session_id: Optional[str] = None) -> List[TestArtifact]:
        """Search artifacts by name pattern."""
        return self.search_engine.search_by_name(name_pattern, session_id)
    
    def get_recent_artifacts(self, hours: int = 24, session_id: Optional[str] = None) -> List[TestArtifact]:
        """Get artifacts created within the last N hours."""
        return self.search_engine.get_recent_artifacts(hours, session_id)
    
    # Utility Operations
    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get a summary of a test session."""
        return self.session_manager.get_session_summary(session_id)
    
    def cleanup_expired_sessions(self) -> List[str]:
        """Clean up expired sessions based on retention policy."""
        return self.session_manager.cleanup_expired_sessions(self.file_handler)
    
    def get_artifact_statistics(self, session_id: Optional[str] = None) -> Dict:
        """Get statistics about artifacts."""
        return self.search_engine.get_artifact_statistics(session_id)
    
    def cleanup(self) -> None:
        """Cleanup resources and save state."""
        self.session_manager.save_all_sessions()
        logger.info("TestArtifactsManager cleanup completed")
    
    def _find_artifact_in_session(self, session: TestSession, artifact_id: str) -> Optional[TestArtifact]:
        """Find an artifact by ID within a session."""
        for collection in session.collections.values():
            for artifact in collection.artifacts:
                if artifact.artifact_id == artifact_id:
                    return artifact
        return None