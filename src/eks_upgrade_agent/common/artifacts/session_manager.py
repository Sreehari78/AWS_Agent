"""
Session management for test artifacts.
"""

import json
import logging
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from ..models.artifacts import TestSession, ArtifactCollection
from ..logging.utils import log_exception

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages test artifact sessions and collections."""
    
    def __init__(self, base_directory: Path, retention_days: int = 30):
        """
        Initialize session manager.
        
        Args:
            base_directory: Base directory for session storage
            retention_days: Default retention period in days
        """
        self.base_directory = Path(base_directory)
        self.retention_days = retention_days
        self._sessions: Dict[str, TestSession] = {}
        
        # Ensure base directory exists
        self.base_directory.mkdir(parents=True, exist_ok=True)
        
        # Load existing sessions
        self._load_sessions()
    
    def create_session(
        self,
        upgrade_id: str,
        cluster_name: str,
        session_name: Optional[str] = None,
        description: Optional[str] = None,
        s3_bucket: Optional[str] = None,
        s3_prefix: Optional[str] = None
    ) -> TestSession:
        """
        Create a new test session.
        
        Args:
            upgrade_id: Associated upgrade ID
            cluster_name: Target cluster name
            session_name: Optional session name
            description: Optional session description
            s3_bucket: Optional S3 bucket for storage
            s3_prefix: Optional S3 key prefix
            
        Returns:
            TestSession instance
        """
        session_id = str(uuid4())
        session_name = session_name or f"upgrade-{upgrade_id}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
        
        # Create session directory
        session_dir = self.base_directory / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Create session
        session = TestSession(
            session_id=session_id,
            name=session_name,
            description=description,
            upgrade_id=upgrade_id,
            cluster_name=cluster_name,
            base_directory=str(session_dir),
            s3_bucket=s3_bucket,
            s3_prefix=f"{s3_prefix}/{session_id}" if s3_prefix else session_id,
            retention_days=self.retention_days
        )
        
        self._sessions[session_id] = session
        self._save_session(session)
        
        logger.info(f"Created test session {session_id}: {session_name}")
        return session
    
    def get_session(self, session_id: str) -> Optional[TestSession]:
        """Get a test session by ID."""
        return self._sessions.get(session_id)
    
    def create_collection(
        self,
        session_id: str,
        collection_name: str,
        description: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Optional[ArtifactCollection]:
        """
        Create a new artifact collection within a session.
        
        Args:
            session_id: Target session ID
            collection_name: Collection name
            description: Optional description
            task_id: Optional associated task ID
            
        Returns:
            ArtifactCollection instance or None if session not found
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None
        
        collection = session.create_collection(collection_name, description, task_id)
        self._save_session(session)
        
        logger.info(f"Created collection {collection.collection_id}: {collection_name}")
        return collection
    
    def complete_session(self, session_id: str) -> bool:
        """
        Complete a test session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return False
        
        session.complete_session()
        self._save_session(session)
        
        logger.info(f"Completed test session {session_id}")
        return True
    
    def cleanup_expired_sessions(self, file_handler) -> List[str]:
        """
        Clean up expired sessions based on retention policy.
        
        Args:
            file_handler: FileHandler instance for cleanup operations
            
        Returns:
            List of cleaned up session IDs
        """
        cleaned_sessions = []
        cutoff_date = datetime.now(UTC) - timedelta(days=self.retention_days)
        
        for session_id, session in list(self._sessions.items()):
            if session.completed_at and session.completed_at < cutoff_date:
                try:
                    # Remove local files
                    session_dir = Path(session.base_directory)
                    if file_handler.cleanup_session_directory(session_dir):
                        # Remove session metadata
                        session_file = self.base_directory / f"session_{session_id}.json"
                        if session_file.exists():
                            session_file.unlink()
                        
                        # Remove from memory
                        del self._sessions[session_id]
                        
                        cleaned_sessions.append(session_id)
                        logger.info(f"Cleaned up expired session {session_id}")
                    
                except Exception as e:
                    log_exception(logger, e, f"Failed to cleanup session {session_id}")
        
        return cleaned_sessions
    
    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get a summary of a test session."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return session.get_session_summary()
    
    def list_sessions(self) -> List[TestSession]:
        """Get list of all sessions."""
        return list(self._sessions.values())
    
    def _save_session(self, session: TestSession) -> None:
        """Save session metadata to disk."""
        try:
            session_file = self.base_directory / f"session_{session.session_id}.json"
            with open(session_file, 'w') as f:
                json.dump(session.model_dump(), f, indent=2, default=str)
        except Exception as e:
            log_exception(logger, e, f"Failed to save session {session.session_id}")
    
    def _load_sessions(self) -> None:
        """Load existing sessions from disk."""
        try:
            for session_file in self.base_directory.glob("session_*.json"):
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    
                    session = TestSession(**data)
                    self._sessions[session.session_id] = session
                    
                except Exception as e:
                    log_exception(logger, e, f"Failed to load session from {session_file}")
            
            logger.info(f"Loaded {len(self._sessions)} existing sessions")
            
        except Exception as e:
            log_exception(logger, e, "Failed to load sessions")
    
    def save_all_sessions(self) -> None:
        """Save all sessions to disk."""
        for session in self._sessions.values():
            self._save_session(session)