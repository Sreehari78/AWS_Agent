"""Tests for EventBridge integration."""

import json
import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError, BotoCoreError

from src.eks_upgrade_agent.common.aws.orchestration.eventbridge import (
    EventBridgeClient,
    UpgradeEvent,
    EventRule,
    create_upgrade_monitoring_rule,
    create_rollback_trigger_rule
)
from src.eks_upgrade_agent.common.handler import AWSServiceError


class TestUpgradeEvent:
    """Test UpgradeEvent model."""
    
    def test_valid_event(self):
        """Test valid upgrade event."""
        event = UpgradeEvent(
            event_type="upgrade.started",
            cluster_name="test-cluster",
            detail_type="EKS Upgrade Started",
            detail={"target_version": "1.29"}
        )
        
        assert event.event_type == "upgrade.started"
        assert event.cluster_name == "test-cluster"
        assert event.source == "eks-upgrade-agent"
        assert isinstance(event.timestamp, datetime)
    
    def test_invalid_event_type(self):
        """Test invalid event type validation."""
        with pytest.raises(ValueError, match="Event type must be one of"):
            UpgradeEvent(
                event_type="invalid.type",
                cluster_name="test-cluster",
                detail_type="Test Event"
            )
    
    def test_valid_event_types(self):
        """Test all valid event types."""
        valid_types = [
            "upgrade.started", "upgrade.completed", "upgrade.failed",
            "phase.started", "phase.completed", "phase.failed",
            "validation.success", "validation.failure",
            "rollback.triggered", "rollback.completed",
            "traffic.shifted", "cluster.provisioned", "cluster.decommissioned"
        ]
        
        for event_type in valid_types:
            event = UpgradeEvent(
                event_type=event_type,
                cluster_name="test-cluster",
                detail_type="Test Event"
            )
            assert event.event_type == event_type


class TestEventRule:
    """Test EventRule model."""
    
    def test_valid_rule(self):
        """Test valid event rule."""
        rule = EventRule(
            name="test-rule",
            description="Test rule",
            event_pattern={"source": ["eks-upgrade-agent"]},
            targets=[{"Id": "1", "Arn": "arn:aws:lambda:us-east-1:123456789012:function:test"}]
        )
        
        assert rule.name == "test-rule"
        assert rule.state == "ENABLED"
        assert len(rule.targets) == 1
    
    def test_invalid_state(self):
        """Test invalid state validation."""
        with pytest.raises(ValueError, match="State must be ENABLED or DISABLED"):
            EventRule(
                name="test-rule",
                description="Test rule",
                event_pattern={},
                state="INVALID"
            )


class TestEventBridgeClient:
    """Test EventBridgeClient."""
    
    @pytest.fixture
    def mock_client(self):
        """Mock boto3 EventBridge client."""
        with patch('boto3.Session') as mock_session:
            mock_eb_client = Mock()
            mock_session.return_value.client.return_value = mock_eb_client
            
            client = EventBridgeClient(bus_name="test-bus", region="us-east-1")
            client.client = mock_eb_client
            
            yield client, mock_eb_client
    
    def test_initialization(self):
        """Test client initialization."""
        with patch('boto3.Session') as mock_session:
            mock_eb_client = Mock()
            mock_session.return_value.client.return_value = mock_eb_client
            
            client = EventBridgeClient(
                bus_name="custom-bus",
                region="us-west-2",
                aws_access_key_id="test-key"
            )
            
            assert client.bus_name == "custom-bus"
            assert client.region == "us-west-2"
    
    def test_publish_event_success(self, mock_client):
        """Test successful event publishing."""
        client, mock_eb_client = mock_client
        
        event = UpgradeEvent(
            event_type="upgrade.started",
            cluster_name="test-cluster",
            detail_type="EKS Upgrade Started"
        )
        
        mock_eb_client.put_events.return_value = {
            "FailedEntryCount": 0,
            "Entries": [{"EventId": "test-event-id"}]
        }
        
        result = client.publish_event(event)
        
        assert result == "test-event-id"
        mock_eb_client.put_events.assert_called_once()
        
        # Verify event entry structure
        call_args = mock_eb_client.put_events.call_args[1]
        entries = call_args["Entries"]
        assert len(entries) == 1
        
        entry = entries[0]
        assert entry["Source"] == "eks-upgrade-agent"
        assert entry["DetailType"] == "EKS Upgrade Started"
        assert entry["EventBusName"] == "test-bus"
        
        detail = json.loads(entry["Detail"])
        assert detail["event_type"] == "upgrade.started"
        assert detail["cluster_name"] == "test-cluster"
    
    def test_publish_event_failure(self, mock_client):
        """Test event publishing failure."""
        client, mock_eb_client = mock_client
        
        event = UpgradeEvent(
            event_type="upgrade.started",
            cluster_name="test-cluster",
            detail_type="EKS Upgrade Started"
        )
        
        mock_eb_client.put_events.return_value = {
            "FailedEntryCount": 1,
            "Entries": [{"ErrorCode": "InvalidArgument", "ErrorMessage": "Invalid event"}]
        }
        
        with pytest.raises(AWSServiceError, match="Failed to publish event"):
            client.publish_event(event)
    
    def test_publish_upgrade_started(self, mock_client):
        """Test publishing upgrade started event."""
        client, mock_eb_client = mock_client
        
        mock_eb_client.put_events.return_value = {
            "FailedEntryCount": 0,
            "Entries": [{"EventId": "test-event-id"}]
        }
        
        result = client.publish_upgrade_started("test-cluster", "1.29", "blue_green")
        
        assert result == "test-event-id"
        
        # Verify event details
        call_args = mock_eb_client.put_events.call_args[1]
        detail = json.loads(call_args["Entries"][0]["Detail"])
        assert detail["event_type"] == "upgrade.started"
        assert detail["cluster_name"] == "test-cluster"
        assert detail["target_version"] == "1.29"
        assert detail["strategy"] == "blue_green"
    
    def test_publish_upgrade_completed(self, mock_client):
        """Test publishing upgrade completed event."""
        client, mock_eb_client = mock_client
        
        mock_eb_client.put_events.return_value = {
            "FailedEntryCount": 0,
            "Entries": [{"EventId": "test-event-id"}]
        }
        
        result = client.publish_upgrade_completed("test-cluster", "1.29", 1800.5)
        
        assert result == "test-event-id"
        
        # Verify event details
        call_args = mock_eb_client.put_events.call_args[1]
        detail = json.loads(call_args["Entries"][0]["Detail"])
        assert detail["event_type"] == "upgrade.completed"
        assert detail["duration_seconds"] == 1800.5
        assert detail["status"] == "success"
    
    def test_publish_upgrade_failed(self, mock_client):
        """Test publishing upgrade failed event."""
        client, mock_eb_client = mock_client
        
        mock_eb_client.put_events.return_value = {
            "FailedEntryCount": 0,
            "Entries": [{"EventId": "test-event-id"}]
        }
        
        result = client.publish_upgrade_failed("test-cluster", "1.29", "Validation failed", "validation")
        
        assert result == "test-event-id"
        
        # Verify event details
        call_args = mock_eb_client.put_events.call_args[1]
        detail = json.loads(call_args["Entries"][0]["Detail"])
        assert detail["event_type"] == "upgrade.failed"
        assert detail["error"] == "Validation failed"
        assert detail["phase"] == "validation"
        assert detail["status"] == "failed"
    
    def test_publish_validation_result_success(self, mock_client):
        """Test publishing validation success result."""
        client, mock_eb_client = mock_client
        
        mock_eb_client.put_events.return_value = {
            "FailedEntryCount": 0,
            "Entries": [{"EventId": "test-event-id"}]
        }
        
        metrics = {"error_rate": 0.01, "latency_p99": 150}
        result = client.publish_validation_result("test-cluster", True, metrics)
        
        assert result == "test-event-id"
        
        # Verify event details
        call_args = mock_eb_client.put_events.call_args[1]
        detail = json.loads(call_args["Entries"][0]["Detail"])
        assert detail["event_type"] == "validation.success"
        assert detail["success"] is True
        assert detail["metrics"] == metrics
    
    def test_publish_validation_result_failure(self, mock_client):
        """Test publishing validation failure result."""
        client, mock_eb_client = mock_client
        
        mock_eb_client.put_events.return_value = {
            "FailedEntryCount": 0,
            "Entries": [{"EventId": "test-event-id"}]
        }
        
        result = client.publish_validation_result("test-cluster", False)
        
        # Verify event details
        call_args = mock_eb_client.put_events.call_args[1]
        detail = json.loads(call_args["Entries"][0]["Detail"])
        assert detail["event_type"] == "validation.failure"
        assert detail["success"] is False
    
    def test_publish_traffic_shifted(self, mock_client):
        """Test publishing traffic shifted event."""
        client, mock_eb_client = mock_client
        
        mock_eb_client.put_events.return_value = {
            "FailedEntryCount": 0,
            "Entries": [{"EventId": "test-event-id"}]
        }
        
        result = client.publish_traffic_shifted("test-cluster", 25, "green-cluster")
        
        # Verify event details
        call_args = mock_eb_client.put_events.call_args[1]
        detail = json.loads(call_args["Entries"][0]["Detail"])
        assert detail["event_type"] == "traffic.shifted"
        assert detail["percentage"] == 25
        assert detail["target_cluster"] == "green-cluster"
    
    def test_create_rule_success(self, mock_client):
        """Test successful rule creation."""
        client, mock_eb_client = mock_client
        
        rule = EventRule(
            name="test-rule",
            description="Test rule",
            event_pattern={"source": ["eks-upgrade-agent"]},
            targets=[{"Id": "1", "Arn": "arn:aws:lambda:us-east-1:123456789012:function:test"}]
        )
        
        mock_eb_client.put_rule.return_value = {
            "RuleArn": "arn:aws:events:us-east-1:123456789012:rule/test-rule"
        }
        
        result = client.create_rule(rule)
        
        assert result == "arn:aws:events:us-east-1:123456789012:rule/test-rule"
        
        # Verify rule creation
        mock_eb_client.put_rule.assert_called_once()
        mock_eb_client.put_targets.assert_called_once()
    
    def test_delete_rule_success(self, mock_client):
        """Test successful rule deletion."""
        client, mock_eb_client = mock_client
        
        mock_eb_client.list_targets_by_rule.return_value = {
            "Targets": [{"Id": "1", "Arn": "arn:aws:lambda:us-east-1:123456789012:function:test"}]
        }
        
        client.delete_rule("test-rule")
        
        # Verify targets removed and rule deleted
        mock_eb_client.remove_targets.assert_called_once()
        mock_eb_client.delete_rule.assert_called_once()
    
    def test_list_rules_success(self, mock_client):
        """Test successful rule listing."""
        client, mock_eb_client = mock_client
        
        mock_eb_client.list_rules.return_value = {
            "Rules": [
                {"Name": "test-rule-1", "State": "ENABLED"},
                {"Name": "test-rule-2", "State": "DISABLED"}
            ]
        }
        
        result = client.list_rules("test-rule")
        
        assert len(result) == 2
        assert result[0]["Name"] == "test-rule-1"
        assert result[1]["Name"] == "test-rule-2"


class TestEventRuleCreators:
    """Test event rule creator functions."""
    
    def test_create_upgrade_monitoring_rule(self):
        """Test creating upgrade monitoring rule."""
        rule = create_upgrade_monitoring_rule("test-cluster")
        
        assert rule.name == "eks-upgrade-monitor-test-cluster"
        assert "Monitor upgrade events" in rule.description
        assert rule.event_pattern["source"] == ["eks-upgrade-agent"]
        assert rule.event_pattern["detail"]["cluster_name"] == ["test-cluster"]
        assert len(rule.targets) == 1
    
    def test_create_rollback_trigger_rule(self):
        """Test creating rollback trigger rule."""
        rule = create_rollback_trigger_rule()
        
        assert rule.name == "eks-upgrade-rollback-trigger"
        assert "Trigger rollback" in rule.description
        assert rule.event_pattern["source"] == ["eks-upgrade-agent"]
        assert rule.event_pattern["detail-type"] == ["EKS Upgrade Validation Result"]
        assert rule.event_pattern["detail"]["success"] == [False]
        assert len(rule.targets) == 1