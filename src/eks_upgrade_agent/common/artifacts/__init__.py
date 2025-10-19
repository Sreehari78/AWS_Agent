"""
Test artifacts management system for organizing test outputs and logs.

This package provides modular components for managing test artifacts
with AWS S3 integration for distributed teams.
"""

from .manager import TestArtifactsManager
from .s3_client import S3ArtifactClient
from .file_handler import FileHandler
from .session_manager import SessionManager
from .search_engine import ArtifactSearchEngine

__all__ = [
    "TestArtifactsManager",
    "S3ArtifactClient", 
    "FileHandler",
    "SessionManager",
    "ArtifactSearchEngine",
]