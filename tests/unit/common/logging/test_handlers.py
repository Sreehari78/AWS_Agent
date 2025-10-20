"""Tests for custom logging handlers."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging

from src.eks_upgrade_agent.common.logging.handlers import CloudWatchHandler


class TestCloudWatchHandler:
    """Test CloudWatch logging handler."""

    @patch('boto3.client')
    def test_cloudwatch_handler_initialization(self, mock_boto_client):
        """Test CloudWatch handler initialization."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        handler = CloudWatchHandler(
            log_group="test-group",
            log_stream="test-stream",
            region="us-east-1"
        )
        
        assert handler.log_group == "test-group"
        assert handler.log_stream == "test-stream"
        assert handler.region == "us-east-1"
        
        # Verify boto3 client was created
        mock_boto_client.assert_called_once_with(
            'logs',
            region_name="us-east-1"
        )

    @patch('boto3.client')
    def test_cloudwatch_handler_emit(self, mock_boto_client):
        """Test CloudWatch handler emit functionality."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        handler = CloudWatchHandler("test-group", "test-stream")
        
        # Create a log record
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test",
            level=logging.INFO,
            fn="test.py",
            lno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Emit the record
        handler.emit(record)
        
        # Verify CloudWatch API was called
        mock_client.put_log_events.assert_called_once()

    @patch('boto3.client')
    def test_cloudwatch_handler_with_auto_stream_name(self, mock_boto_client):
        """Test CloudWatch handler with automatic stream name generation."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        handler = CloudWatchHandler("test-group")  # No stream name provided
        
        # Should generate a stream name
        assert handler.log_stream is not None
        assert len(handler.log_stream) > 0

    @patch('boto3.client')
    def test_cloudwatch_handler_error_handling(self, mock_boto_client):
        """Test CloudWatch handler error handling."""
        mock_client = Mock()
        mock_client.put_log_events.side_effect = Exception("CloudWatch error")
        mock_boto_client.return_value = mock_client
        
        handler = CloudWatchHandler("test-group", "test-stream")
        
        # Create a log record
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test",
            level=logging.ERROR,
            fn="test.py",
            lno=1,
            msg="Test error message",
            args=(),
            exc_info=None
        )
        
        # Should not raise exception even if CloudWatch fails
        try:
            handler.emit(record)
        except Exception:
            pytest.fail("CloudWatch handler should handle errors gracefully")

    @patch('boto3.client')
    def test_cloudwatch_handler_formatting(self, mock_boto_client):
        """Test CloudWatch handler message formatting."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        handler = CloudWatchHandler("test-group", "test-stream")
        
        # Set a custom formatter
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Create a log record
        logger = logging.getLogger("test")
        record = logger.makeRecord(
            name="test",
            level=logging.WARNING,
            fn="test.py",
            lno=1,
            msg="Test warning",
            args=(),
            exc_info=None
        )
        
        # Emit the record
        handler.emit(record)
        
        # Verify the formatted message was sent
        mock_client.put_log_events.assert_called_once()
        call_args = mock_client.put_log_events.call_args
        log_events = call_args[1]['logEvents']
        assert len(log_events) == 1
        assert "WARNING - Test warning" in log_events[0]['message']

    @patch('boto3.client')
    def test_cloudwatch_handler_batch_logging(self, mock_boto_client):
        """Test CloudWatch handler with multiple log messages."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        handler = CloudWatchHandler("test-group", "test-stream")
        
        logger = logging.getLogger("test")
        
        # Emit multiple records
        for i in range(3):
            record = logger.makeRecord(
                name="test",
                level=logging.INFO,
                fn="test.py",
                lno=1,
                msg=f"Test message {i}",
                args=(),
                exc_info=None
            )
            handler.emit(record)
        
        # Should have made multiple calls to CloudWatch
        assert mock_client.put_log_events.call_count == 3