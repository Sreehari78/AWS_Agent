"""
Search engine for test artifacts.
"""

import logging
from typing import Dict, List, Optional

from ..models.artifacts import (
    ArtifactStatus,
    ArtifactType,
    ArtifactTestData,
    SessionTestData,
)

logger = logging.getLogger(__name__)


class ArtifactSearchEngine:
    """Search engine for finding artifacts based on various criteria."""
    
    def __init__(self, sessions: Dict[str, SessionTestData]):
        """
        Initialize search engine.
        
        Args:
            sessions: Dictionary of sessions to search in
        """
        self.sessions = sessions
    
    def search_artifacts(
        self,
        session_id: Optional[str] = None,
        artifact_type: Optional[ArtifactType] = None,
        tags: Optional[List[str]] = None,
        task_id: Optional[str] = None,
        status: Optional[ArtifactStatus] = None,
        collection_id: Optional[str] = None,
        upgrade_id: Optional[str] = None
    ) -> List[ArtifactTestData]:
        """
        Search for artifacts based on criteria.
        
        Args:
            session_id: Optional session ID filter
            artifact_type: Optional artifact type filter
            tags: Optional tags filter (artifacts must have all tags)
            task_id: Optional task ID filter
            status: Optional status filter
            collection_id: Optional collection ID filter
            upgrade_id: Optional upgrade ID filter
            
        Returns:
            List of matching artifacts
        """
        results = []
        
        # Determine sessions to search
        sessions_to_search = self._get_sessions_to_search(session_id, upgrade_id)
        
        for session in sessions_to_search:
            for collection in session.collections.values():
                # Filter by collection ID if specified
                if collection_id and collection.collection_id != collection_id:
                    continue
                
                for artifact in collection.artifacts:
                    if self._matches_criteria(artifact, artifact_type, tags, task_id, status):
                        results.append(artifact)
        
        logger.debug(f"Found {len(results)} artifacts matching search criteria")
        return results
    
    def search_by_name(self, name_pattern: str, session_id: Optional[str] = None) -> List[ArtifactTestData]:
        """
        Search artifacts by name pattern.
        
        Args:
            name_pattern: Pattern to match in artifact names (case-insensitive)
            session_id: Optional session ID filter
            
        Returns:
            List of matching artifacts
        """
        results = []
        pattern_lower = name_pattern.lower()
        
        sessions_to_search = self._get_sessions_to_search(session_id)
        
        for session in sessions_to_search:
            for collection in session.collections.values():
                for artifact in collection.artifacts:
                    if pattern_lower in artifact.name.lower():
                        results.append(artifact)
        
        logger.debug(f"Found {len(results)} artifacts matching name pattern '{name_pattern}'")
        return results
    
    def get_artifacts_by_size_range(
        self,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> List[ArtifactTestData]:
        """
        Get artifacts within a size range.
        
        Args:
            min_size: Minimum file size in bytes
            max_size: Maximum file size in bytes
            session_id: Optional session ID filter
            
        Returns:
            List of matching artifacts
        """
        results = []
        
        sessions_to_search = self._get_sessions_to_search(session_id)
        
        for session in sessions_to_search:
            for collection in session.collections.values():
                for artifact in collection.artifacts:
                    if artifact.file_size is None:
                        continue
                    
                    if min_size is not None and artifact.file_size < min_size:
                        continue
                    
                    if max_size is not None and artifact.file_size > max_size:
                        continue
                    
                    results.append(artifact)
        
        logger.debug(f"Found {len(results)} artifacts in size range {min_size}-{max_size}")
        return results
    
    def get_recent_artifacts(
        self,
        hours: int = 24,
        session_id: Optional[str] = None
    ) -> List[ArtifactTestData]:
        """
        Get artifacts created within the last N hours.
        
        Args:
            hours: Number of hours to look back
            session_id: Optional session ID filter
            
        Returns:
            List of recent artifacts
        """
        from datetime import datetime, timedelta, UTC
        
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        results = []
        
        sessions_to_search = self._get_sessions_to_search(session_id)
        
        for session in sessions_to_search:
            for collection in session.collections.values():
                for artifact in collection.artifacts:
                    if artifact.created_at >= cutoff_time:
                        results.append(artifact)
        
        # Sort by creation time (newest first)
        results.sort(key=lambda x: x.created_at, reverse=True)
        
        logger.debug(f"Found {len(results)} artifacts created in last {hours} hours")
        return results
    
    def get_artifacts_by_collection(self, collection_id: str) -> List[ArtifactTestData]:
        """
        Get all artifacts in a specific collection.
        
        Args:
            collection_id: Collection ID
            
        Returns:
            List of artifacts in the collection
        """
        for session in self.sessions.values():
            collection = session.get_collection(collection_id)
            if collection:
                return collection.artifacts
        
        return []
    
    def get_artifact_statistics(self, session_id: Optional[str] = None) -> Dict:
        """
        Get statistics about artifacts.
        
        Args:
            session_id: Optional session ID filter
            
        Returns:
            Dictionary with statistics
        """
        sessions_to_search = self._get_sessions_to_search(session_id)
        
        total_artifacts = 0
        total_size = 0
        type_counts = {}
        status_counts = {}
        
        for session in sessions_to_search:
            for collection in session.collections.values():
                for artifact in collection.artifacts:
                    total_artifacts += 1
                    total_size += artifact.file_size or 0
                    
                    # Count by type
                    artifact_type = str(artifact.artifact_type)
                    type_counts[artifact_type] = type_counts.get(artifact_type, 0) + 1
                    
                    # Count by status
                    status = str(artifact.status)
                    status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_artifacts": total_artifacts,
            "total_size_bytes": total_size,
            "average_size_bytes": total_size / total_artifacts if total_artifacts > 0 else 0,
            "type_distribution": type_counts,
            "status_distribution": status_counts,
            "sessions_searched": len(sessions_to_search)
        }
    
    def _get_sessions_to_search(
        self, 
        session_id: Optional[str] = None, 
        upgrade_id: Optional[str] = None
    ) -> List[SessionTestData]:
        """Get list of sessions to search based on filters."""
        if session_id:
            session = self.sessions.get(session_id)
            return [session] if session else []
        
        if upgrade_id:
            return [s for s in self.sessions.values() if s.upgrade_id == upgrade_id]
        
        return list(self.sessions.values())
    
    def _matches_criteria(
        self,
        artifact: ArtifactTestData,
        artifact_type: Optional[ArtifactType],
        tags: Optional[List[str]],
        task_id: Optional[str],
        status: Optional[ArtifactStatus]
    ) -> bool:
        """Check if artifact matches search criteria."""
        # Check artifact type
        if artifact_type and artifact.artifact_type != artifact_type:
            return False
        
        # Check task ID
        if task_id and artifact.task_id != task_id:
            return False
        
        # Check status
        if status and artifact.status != status:
            return False
        
        # Check tags (artifact must have all specified tags)
        if tags and not all(tag in artifact.tags for tag in tags):
            return False
        
        return True