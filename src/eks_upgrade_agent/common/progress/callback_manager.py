"""
Callback management system for progress events.
"""

import logging
from typing import Callable, Dict, List

from ..models.progress import ProgressEvent, ProgressStatus, TaskProgress
from ..logging.utils import log_exception

logger = logging.getLogger(__name__)


class CallbackManager:
    """
    Manages event callbacks and status change notifications.
    
    Features:
    - Event callback registration
    - Status-specific callbacks
    - Error handling for callback execution
    """
    
    def __init__(self):
        """Initialize callback manager."""
        self._event_callbacks: List[Callable[[ProgressEvent], None]] = []
        self._status_callbacks: Dict[ProgressStatus, List[Callable[[TaskProgress], None]]] = {
            status: [] for status in ProgressStatus
        }
        
        logger.debug("CallbackManager initialized")
    
    def add_event_callback(self, callback: Callable[[ProgressEvent], None]) -> None:
        """
        Add a callback for all progress events.
        
        Args:
            callback: Function to call on progress events
        """
        self._event_callbacks.append(callback)
        logger.debug(f"Added event callback: {callback.__name__}")
    
    def remove_event_callback(self, callback: Callable[[ProgressEvent], None]) -> bool:
        """
        Remove an event callback.
        
        Args:
            callback: Function to remove
            
        Returns:
            True if removed, False if not found
        """
        try:
            self._event_callbacks.remove(callback)
            logger.debug(f"Removed event callback: {callback.__name__}")
            return True
        except ValueError:
            logger.warning(f"Event callback not found: {callback.__name__}")
            return False
    
    def add_status_callback(
        self, 
        status: ProgressStatus, 
        callback: Callable[[TaskProgress], None]
    ) -> None:
        """
        Add a callback for specific status changes.
        
        Args:
            status: Status to listen for
            callback: Function to call on status change
        """
        self._status_callbacks[status].append(callback)
        logger.debug(f"Added status callback for {status}: {callback.__name__}")
    
    def remove_status_callback(
        self, 
        status: ProgressStatus, 
        callback: Callable[[TaskProgress], None]
    ) -> bool:
        """
        Remove a status callback.
        
        Args:
            status: Status the callback was registered for
            callback: Function to remove
            
        Returns:
            True if removed, False if not found
        """
        try:
            self._status_callbacks[status].remove(callback)
            logger.debug(f"Removed status callback for {status}: {callback.__name__}")
            return True
        except ValueError:
            logger.warning(f"Status callback not found for {status}: {callback.__name__}")
            return False
    
    def notify_event(self, event: ProgressEvent) -> None:
        """
        Notify all event callbacks.
        
        Args:
            event: Progress event to notify about
        """
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                log_exception(logger, e, f"Event callback error for {event.event_id}")
    
    def notify_status_change(self, task: TaskProgress) -> None:
        """
        Notify status-specific callbacks.
        
        Args:
            task: Task with status change
        """
        callbacks = self._status_callbacks.get(task.status, [])
        for callback in callbacks:
            try:
                callback(task)
            except Exception as e:
                log_exception(logger, e, f"Status callback error for task {task.task_id}")
    
    def clear_all_callbacks(self) -> None:
        """Clear all registered callbacks."""
        self._event_callbacks.clear()
        for callbacks in self._status_callbacks.values():
            callbacks.clear()
        
        logger.debug("Cleared all callbacks")
    
    def get_callback_counts(self) -> Dict[str, int]:
        """
        Get counts of registered callbacks.
        
        Returns:
            Dictionary with callback counts
        """
        return {
            "event_callbacks": len(self._event_callbacks),
            "status_callbacks": {
                status.value: len(callbacks) 
                for status, callbacks in self._status_callbacks.items()
                if callbacks
            }
        }