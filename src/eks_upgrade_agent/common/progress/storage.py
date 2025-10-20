"""
Progress storage management for persistent progress tracking.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Union

from ..models.progress import UpgradeProgress
from ..logging.utils import log_exception

logger = logging.getLogger(__name__)


class ProgressStorage:
    """
    Manages persistent storage of progress data.
    
    Features:
    - JSON-based local storage
    - Automatic file management
    - Error handling and recovery
    """
    
    def __init__(self, storage_path: Union[str, Path], upgrade_id: str):
        """
        Initialize progress storage.
        
        Args:
            storage_path: Directory for storing progress files
            upgrade_id: Unique upgrade identifier
        """
        self.storage_path = Path(storage_path) / "progress"
        self.upgrade_id = upgrade_id
        self.progress_file = self.storage_path / f"upgrade_{upgrade_id}.json"
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"ProgressStorage initialized for upgrade {upgrade_id}")
    
    def save_progress(self, progress: UpgradeProgress) -> bool:
        """
        Save progress data to storage.
        
        Args:
            progress: Progress data to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress.model_dump(), f, indent=2, default=str)
            
            logger.debug(f"Saved progress for upgrade {self.upgrade_id}")
            return True
            
        except Exception as e:
            log_exception(logger, e, f"Failed to save progress to {self.progress_file}")
            return False
    
    def load_progress(self) -> Optional[UpgradeProgress]:
        """
        Load progress data from storage.
        
        Returns:
            UpgradeProgress instance or None if not found/failed
        """
        if not self.progress_file.exists():
            logger.debug(f"No existing progress file found for upgrade {self.upgrade_id}")
            return None
        
        try:
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
            
            progress = UpgradeProgress(**data)
            logger.info(f"Loaded existing progress for upgrade {self.upgrade_id}")
            return progress
            
        except Exception as e:
            log_exception(logger, e, f"Failed to load progress from {self.progress_file}")
            return None
    
    def delete_progress(self) -> bool:
        """
        Delete progress file from storage.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.progress_file.exists():
                self.progress_file.unlink()
                logger.info(f"Deleted progress file for upgrade {self.upgrade_id}")
            return True
            
        except Exception as e:
            log_exception(logger, e, f"Failed to delete progress file {self.progress_file}")
            return False
    
    def get_storage_info(self) -> dict:
        """
        Get information about the storage.
        
        Returns:
            Dictionary with storage information
        """
        return {
            "storage_path": str(self.storage_path),
            "progress_file": str(self.progress_file),
            "file_exists": self.progress_file.exists(),
            "file_size": self.progress_file.stat().st_size if self.progress_file.exists() else 0
        }