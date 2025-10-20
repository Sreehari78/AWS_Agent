"""
AWS EventBridge integration for progress notifications.
"""

import json
import logging
from datetime import datetime, UTC
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..logging.utils import log_exception

logger = logging.getLogger(__name__)


class EventBridgeNotifier:
    """
    Manages AWS EventBridge notifications for upgrade events.
    
    Features:
    - EventBridge integration
    - Structured event publishing
    - Error handling and fallback
    """
    
    def __init__(
        self,
        bus_name: Optional[str] = None,
        aws_region: str = "us-east-1",
        source: str = "eks-upgrade-agent"
    ):
        """
        Initialize EventBridge notifier.
        
        Args:
            bus_name: EventBridge bus name (None to disable)
            aws_region: AWS region for EventBridge
            source: Event source identifier
        """
        self.bus_name = bus_name
        self.aws_region = aws_region
        self.source = source
        self._client: Optional[boto3.client] = None
        
        logger.debug(f"EventBridgeNotifier initialized for bus: {bus_name}")
    
    @property
    def client(self) -> Optional[boto3.client]:
        """Get or create EventBridge client."""
        if self._client is None and self.bus_name:
            try:
                self._client = boto3.client('events', region_name=self.aws_region)
                logger.debug("EventBridge client created successfully")
            except (NoCredentialsError, ClientError) as e:
                log_exception(logger, e, "Failed to create EventBridge client")
        return self._client
    
    def send_notification(self, event_type: str, detail: Dict[str, Any]) -> bool:
        """
        Send notification to EventBridge.
        
        Args:
            event_type: Type of event (e.g., 'upgrade.started')
            detail: Event detail data
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client or not self.bus_name:
            logger.debug("EventBridge client or bus name not configured, skipping notification")
            return False
        
        try:
            response = self.client.put_events(
                Entries=[
                    {
                        'Source': self.source,
                        'DetailType': event_type,
                        'Detail': json.dumps(detail),
                        'EventBusName': self.bus_name,
                        'Time': datetime.now(UTC)
                    }
                ]
            )
            
            # Check for failures
            if response.get('FailedEntryCount', 0) > 0:
                logger.warning(f"EventBridge notification partially failed: {response}")
                return False
            
            logger.debug(f"Sent EventBridge notification: {event_type}")
            return True
            
        except Exception as e:
            log_exception(logger, e, f"Failed to send EventBridge notification: {event_type}")
            return False
    
    def send_upgrade_started(self, upgrade_id: str, cluster_name: str, phase: str) -> bool:
        """Send upgrade started notification."""
        return self.send_notification("upgrade.started", {
            "upgrade_id": upgrade_id,
            "cluster_name": cluster_name,
            "phase": phase
        })
    
    def send_upgrade_completed(self, upgrade_id: str, cluster_name: str, duration: Optional[str] = None) -> bool:
        """Send upgrade completed notification."""
        return self.send_notification("upgrade.completed", {
            "upgrade_id": upgrade_id,
            "cluster_name": cluster_name,
            "duration": duration
        })
    
    def send_upgrade_failed(self, upgrade_id: str, cluster_name: str, error_message: str) -> bool:
        """Send upgrade failed notification."""
        return self.send_notification("upgrade.failed", {
            "upgrade_id": upgrade_id,
            "cluster_name": cluster_name,
            "error_message": error_message
        })
    
    def send_phase_changed(self, upgrade_id: str, cluster_name: str, phase: str) -> bool:
        """Send phase changed notification."""
        return self.send_notification("upgrade.phase_changed", {
            "upgrade_id": upgrade_id,
            "cluster_name": cluster_name,
            "phase": phase
        })
    
    def send_task_started(self, upgrade_id: str, cluster_name: str, task_id: str, task_name: str) -> bool:
        """Send task started notification."""
        return self.send_notification("task.started", {
            "upgrade_id": upgrade_id,
            "cluster_name": cluster_name,
            "task_id": task_id,
            "task_name": task_name
        })
    
    def send_task_completed(self, upgrade_id: str, cluster_name: str, task_id: str, task_name: str, duration: Optional[str] = None) -> bool:
        """Send task completed notification."""
        return self.send_notification("task.completed", {
            "upgrade_id": upgrade_id,
            "cluster_name": cluster_name,
            "task_id": task_id,
            "task_name": task_name,
            "duration": duration
        })
    
    def send_task_failed(self, upgrade_id: str, cluster_name: str, task_id: str, task_name: str, error_message: str) -> bool:
        """Send task failed notification."""
        return self.send_notification("task.failed", {
            "upgrade_id": upgrade_id,
            "cluster_name": cluster_name,
            "task_id": task_id,
            "task_name": task_name,
            "error_message": error_message
        })
    
    def is_enabled(self) -> bool:
        """Check if EventBridge notifications are enabled."""
        return self.bus_name is not None and self.client is not None