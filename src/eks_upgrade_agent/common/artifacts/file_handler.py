"""
File handling utilities for test artifacts.
"""

import hashlib
import shutil
from pathlib import Path
from typing import Optional
import logging

from ..logging.utils import log_exception

logger = logging.getLogger(__name__)


class FileHandler:
    """Handles file operations for test artifacts."""
    
    def __init__(self, base_directory: Path):
        """
        Initialize file handler.
        
        Args:
            base_directory: Base directory for file operations
        """
        self.base_directory = Path(base_directory)
        self.base_directory.mkdir(parents=True, exist_ok=True)
    
    def copy_file_to_session(
        self, 
        source_path: Path, 
        session_dir: Path, 
        collection_id: str
    ) -> Optional[str]:
        """
        Copy file to session directory if not already there.
        
        Args:
            source_path: Source file path
            session_dir: Session directory
            collection_id: Collection ID for organization
            
        Returns:
            Local path of copied file or None if failed
        """
        try:
            if not source_path.exists():
                logger.error(f"Source file not found: {source_path}")
                return None
            
            # Check if file is already in session directory
            if source_path.is_relative_to(session_dir):
                return str(source_path)
            
            # Copy to session directory
            target_path = session_dir / collection_id / source_path.name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)
            
            logger.debug(f"Copied file from {source_path} to {target_path}")
            return str(target_path)
            
        except Exception as e:
            log_exception(logger, e, f"Failed to copy file {source_path}")
            return None
    
    def calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA256 hash of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA256 hash as hex string
        """
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            log_exception(logger, e, f"Failed to calculate hash for {file_path}")
            return ""
    
    def get_file_size(self, file_path: str) -> int:
        """
        Get file size in bytes.
        
        Args:
            file_path: Path to file
            
        Returns:
            File size in bytes
        """
        try:
            return Path(file_path).stat().st_size
        except Exception as e:
            log_exception(logger, e, f"Failed to get file size for {file_path}")
            return 0
    
    def cleanup_session_directory(self, session_dir: Path) -> bool:
        """
        Remove session directory and all contents.
        
        Args:
            session_dir: Session directory to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if session_dir.exists():
                shutil.rmtree(session_dir)
                logger.info(f"Cleaned up session directory: {session_dir}")
                return True
            return True
        except Exception as e:
            log_exception(logger, e, f"Failed to cleanup session directory {session_dir}")
            return False