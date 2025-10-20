"""
AWS EventBridge integration for event-driven coordination.

This module provides a client for publishing and handling upgrade events
through Amazon EventBridge for decoupled communication and coordination.
"""

import json
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from pydantic import BaseModel, Field, field_validator

from ...logging import get_logger
from ...handler import AWSServiceError

logger = get_logger(__name__)


class UpgradeEvent(BaseModel):
    """Event model for EKS upgrade notifications."""
    
    event_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique event ID")
    event_type: str = Field(..., description="Event type")
    cluster_name: str = Field(..., description="EKS cluster name")
    source: str = Field(default="eks-upgrade-agent", description="Event source")
    detail_type: str = Field(..., description="Event detail type")
    detail: Dict[str, Any] = Field(default_factory=dict, description="Event details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Event timestamp")
    
    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v):
        valid_types = [
            "upgrade.started",
            "upgrade.completed", 
            "upgrade.failed",
            "phase.started",
            "phase.completed",
            "phase.failed",
            "validation.success",
            "validation.failure",
            "rollback.triggered",
            "rollback.completed",
            "traffic.shifted",
            "cluster.provisioned",
            "cluster.decommissioned"
        ]
        if v not in valid_types:
            raise ValueError(f"Event type must be one of: {valid_types}")
        return v


class EventRule(BaseModel):
    """EventBridge rule configuration."""
    
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    event_pattern: Dict[str, Any] = Field(..., description="Event pattern for matching")
    targets: List[Dict[str, Any]] = Field(default_factory=list, description="Rule targets")
    state: str = Field(default="ENABLED", description="Rule state")
    
    @field_validator("state")
    @classmethod
    def validate_state(cls, v):
        if v not in ["ENABLED", "DISABLED"]:
            raise ValueError("State must be ENABLED or DISABLED")
        return v


class EventBridgeClient:
    """
    Client for AWS EventBridge integration.
    
    Manages event publishing and rule configuration for upgrade coordination
    with proper error handling and monitoring.
    """
    
    def __init__(
        self,
        bus_name: str = "default",
        region: str = "us-east-1",
        aws_profile: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None
    ):
        """
        Initialize EventBridge client.
        
        Args:
            bus_name: EventBridge bus name
            region: AWS region
            aws_profile: AWS profile name
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            aws_session_token: AWS session token
        """
        self.bus_name = bus_name
        self.region = region
        
        # Create boto3 session
        session_kwargs = {}
        if aws_profile:
            session_kwargs["profile_name"] = aws_profile
        else:
            if aws_access_key_id:
                session_kwargs["aws_access_key_id"] = aws_access_key_id
            if aws_secret_access_key:
                session_kwargs["aws_secret_access_key"] = aws_secret_access_key
            if aws_session_token:
                session_kwargs["aws_session_token"] = aws_session_token
        
        self.session = boto3.Session(**session_kwargs)
        self.client = self.session.client("events", region_name=region)
        
        logger.info(f"Initialized EventBridge client for bus: {bus_name}, region: {region}")
    
    def publish_event(self, event: UpgradeEvent) -> str:
        """
        Publish an upgrade event to EventBridge.
        
        Args:
            event: Upgrade event to publish
            
        Returns:
            Event ID from EventBridge response
            
        Raises:
            AWSServiceError: If event publishing fails
        """
        try:
            logger.info(f"Publishing event: {event.event_type} for cluster: {event.cluster_name}")
            
            # Prepare event entry
            event_entry = {
                "Source": event.source,
                "DetailType": event.detail_type,
                "Detail": json.dumps({
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "cluster_name": event.cluster_name,
                    "timestamp": event.timestamp.isoformat(),
                    **event.detail
                }),
                "EventBusName": self.bus_name
            }
            
            response = self.client.put_events(Entries=[event_entry])
            
            # Check for failures
            if response.get("FailedEntryCount", 0) > 0:
                failed_entries = response.get("Entries", [])
                error_msg = f"Failed to publish event: {failed_entries}"
                logger.error(error_msg)
                raise AWSServiceError(error_msg)
            
            event_id = response["Entries"][0]["EventId"]
            logger.info(f"Published event successfully: {event_id}")
            
            return event_id
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to publish event {event.event_type}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def publish_upgrade_started(self, cluster_name: str, target_version: str, strategy: str) -> str:
        """
        Publish upgrade started event.
        
        Args:
            cluster_name: EKS cluster name
            target_version: Target Kubernetes version
            strategy: Upgrade strategy
            
        Returns:
            Event ID
        """
        event = UpgradeEvent(
            event_type="upgrade.started",
            cluster_name=cluster_name,
            detail_type="EKS Upgrade Started",
            detail={
                "target_version": target_version,
                "strategy": strategy,
                "phase": "initialization"
            }
        )
        return self.publish_event(event)
    
    def publish_upgrade_completed(self, cluster_name: str, target_version: str, duration_seconds: float) -> str:
        """
        Publish upgrade completed event.
        
        Args:
            cluster_name: EKS cluster name
            target_version: Target Kubernetes version
            duration_seconds: Upgrade duration
            
        Returns:
            Event ID
        """
        event = UpgradeEvent(
            event_type="upgrade.completed",
            cluster_name=cluster_name,
            detail_type="EKS Upgrade Completed",
            detail={
                "target_version": target_version,
                "duration_seconds": duration_seconds,
                "status": "success"
            }
        )
        return self.publish_event(event)
    
    def publish_upgrade_failed(self, cluster_name: str, target_version: str, error: str, phase: str) -> str:
        """
        Publish upgrade failed event.
        
        Args:
            cluster_name: EKS cluster name
            target_version: Target Kubernetes version
            error: Error message
            phase: Phase where failure occurred
            
        Returns:
            Event ID
        """
        event = UpgradeEvent(
            event_type="upgrade.failed",
            cluster_name=cluster_name,
            detail_type="EKS Upgrade Failed",
            detail={
                "target_version": target_version,
                "error": error,
                "phase": phase,
                "status": "failed"
            }
        )
        return self.publish_event(event)
    
    def publish_phase_started(self, cluster_name: str, phase: str, details: Dict[str, Any] = None) -> str:
        """
        Publish phase started event.
        
        Args:
            cluster_name: EKS cluster name
            phase: Upgrade phase name
            details: Additional phase details
            
        Returns:
            Event ID
        """
        event = UpgradeEvent(
            event_type="phase.started",
            cluster_name=cluster_name,
            detail_type="EKS Upgrade Phase Started",
            detail={
                "phase": phase,
                "status": "started",
                **(details or {})
            }
        )
        return self.publish_event(event)
    
    def publish_phase_completed(self, cluster_name: str, phase: str, details: Dict[str, Any] = None) -> str:
        """
        Publish phase completed event.
        
        Args:
            cluster_name: EKS cluster name
            phase: Upgrade phase name
            details: Additional phase details
            
        Returns:
            Event ID
        """
        event = UpgradeEvent(
            event_type="phase.completed",
            cluster_name=cluster_name,
            detail_type="EKS Upgrade Phase Completed",
            detail={
                "phase": phase,
                "status": "completed",
                **(details or {})
            }
        )
        return self.publish_event(event)
    
    def publish_validation_result(self, cluster_name: str, success: bool, metrics: Dict[str, Any] = None) -> str:
        """
        Publish validation result event.
        
        Args:
            cluster_name: EKS cluster name
            success: Validation success status
            metrics: Validation metrics
            
        Returns:
            Event ID
        """
        event_type = "validation.success" if success else "validation.failure"
        event = UpgradeEvent(
            event_type=event_type,
            cluster_name=cluster_name,
            detail_type="EKS Upgrade Validation Result",
            detail={
                "success": success,
                "metrics": metrics or {},
                "phase": "validation"
            }
        )
        return self.publish_event(event)
    
    def publish_rollback_triggered(self, cluster_name: str, reason: str, phase: str) -> str:
        """
        Publish rollback triggered event.
        
        Args:
            cluster_name: EKS cluster name
            reason: Rollback reason
            phase: Phase where rollback was triggered
            
        Returns:
            Event ID
        """
        event = UpgradeEvent(
            event_type="rollback.triggered",
            cluster_name=cluster_name,
            detail_type="EKS Upgrade Rollback Triggered",
            detail={
                "reason": reason,
                "phase": phase,
                "status": "rollback_initiated"
            }
        )
        return self.publish_event(event)
    
    def publish_traffic_shifted(self, cluster_name: str, percentage: int, target_cluster: str) -> str:
        """
        Publish traffic shifted event.
        
        Args:
            cluster_name: EKS cluster name
            percentage: Traffic percentage shifted
            target_cluster: Target cluster receiving traffic
            
        Returns:
            Event ID
        """
        event = UpgradeEvent(
            event_type="traffic.shifted",
            cluster_name=cluster_name,
            detail_type="EKS Upgrade Traffic Shifted",
            detail={
                "percentage": percentage,
                "target_cluster": target_cluster,
                "phase": "traffic_management"
            }
        )
        return self.publish_event(event)
    
    def create_rule(self, rule: EventRule) -> str:
        """
        Create an EventBridge rule.
        
        Args:
            rule: Rule configuration
            
        Returns:
            Rule ARN
            
        Raises:
            AWSServiceError: If rule creation fails
        """
        try:
            logger.info(f"Creating EventBridge rule: {rule.name}")
            
            response = self.client.put_rule(
                Name=rule.name,
                EventPattern=json.dumps(rule.event_pattern),
                State=rule.state,
                Description=rule.description,
                EventBusName=self.bus_name
            )
            
            rule_arn = response["RuleArn"]
            
            # Add targets if specified
            if rule.targets:
                self.client.put_targets(
                    Rule=rule.name,
                    EventBusName=self.bus_name,
                    Targets=rule.targets
                )
                logger.info(f"Added {len(rule.targets)} targets to rule: {rule.name}")
            
            logger.info(f"Created EventBridge rule: {rule_arn}")
            return rule_arn
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to create rule {rule.name}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def delete_rule(self, rule_name: str) -> None:
        """
        Delete an EventBridge rule.
        
        Args:
            rule_name: Rule name to delete
            
        Raises:
            AWSServiceError: If rule deletion fails
        """
        try:
            logger.info(f"Deleting EventBridge rule: {rule_name}")
            
            # Remove all targets first
            targets_response = self.client.list_targets_by_rule(
                Rule=rule_name,
                EventBusName=self.bus_name
            )
            
            if targets_response.get("Targets"):
                target_ids = [target["Id"] for target in targets_response["Targets"]]
                self.client.remove_targets(
                    Rule=rule_name,
                    EventBusName=self.bus_name,
                    Ids=target_ids
                )
                logger.info(f"Removed {len(target_ids)} targets from rule: {rule_name}")
            
            # Delete the rule
            self.client.delete_rule(
                Name=rule_name,
                EventBusName=self.bus_name
            )
            
            logger.info(f"Deleted EventBridge rule: {rule_name}")
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to delete rule {rule_name}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def list_rules(self, name_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List EventBridge rules.
        
        Args:
            name_prefix: Optional name prefix filter
            
        Returns:
            List of rule information
            
        Raises:
            AWSServiceError: If listing fails
        """
        try:
            logger.debug(f"Listing EventBridge rules with prefix: {name_prefix}")
            
            kwargs = {"EventBusName": self.bus_name}
            if name_prefix:
                kwargs["NamePrefix"] = name_prefix
            
            response = self.client.list_rules(**kwargs)
            
            rules = response.get("Rules", [])
            logger.debug(f"Found {len(rules)} rules")
            
            return rules
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to list rules: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e


def create_upgrade_monitoring_rule(cluster_name: str) -> EventRule:
    """
    Create a rule for monitoring upgrade events for a specific cluster.
    
    Args:
        cluster_name: EKS cluster name
        
    Returns:
        EventRule configuration
    """
    return EventRule(
        name=f"eks-upgrade-monitor-{cluster_name}",
        description=f"Monitor upgrade events for cluster {cluster_name}",
        event_pattern={
            "source": ["eks-upgrade-agent"],
            "detail": {
                "cluster_name": [cluster_name]
            }
        },
        targets=[
            {
                "Id": "1",
                "Arn": f"arn:aws:logs:us-east-1:123456789012:log-group:/aws/events/eks-upgrade-{cluster_name}",
                "InputTransformer": {
                    "InputPathsMap": {
                        "timestamp": "$.detail.timestamp",
                        "event_type": "$.detail.event_type",
                        "cluster": "$.detail.cluster_name"
                    },
                    "InputTemplate": '{"timestamp": "<timestamp>", "event": "<event_type>", "cluster": "<cluster>"}'
                }
            }
        ]
    )


def create_rollback_trigger_rule() -> EventRule:
    """
    Create a rule for triggering rollback on validation failures.
    
    Returns:
        EventRule configuration
    """
    return EventRule(
        name="eks-upgrade-rollback-trigger",
        description="Trigger rollback on validation failures",
        event_pattern={
            "source": ["eks-upgrade-agent"],
            "detail-type": ["EKS Upgrade Validation Result"],
            "detail": {
                "success": [False]
            }
        },
        targets=[
            {
                "Id": "1",
                "Arn": "arn:aws:lambda:us-east-1:123456789012:function:eks-upgrade-agent-rollback",
                "InputTransformer": {
                    "InputPathsMap": {
                        "cluster": "$.detail.cluster_name",
                        "reason": "$.detail.metrics.error"
                    },
                    "InputTemplate": '{"cluster_name": "<cluster>", "rollback_reason": "<reason>"}'
                }
            }
        ]
    )