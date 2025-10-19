"""
Unit tests for the logging system in the EKS Upgrade Agent.

Tests the structured logging configuration, CloudWatch integration,
and logging utility functions.
"""

import pytest
import logging
import sys
from io import StringIO
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json

from src.eks_upgrade_agent.common.logger import (
    LoggerConfig,
    CloudWatchHandler,
    setup_logging,
    get_logger,
    log_exception,
    log_upgrade_step,
    log_aws_api_call,
    add_context_processor,
    add_exception_processor,
)
from src.eks_upgrade_agent.common.exceptions import (
    EKSUpgradeAgentError,
    PerceptionError,
)


class TestLoggerConfig:
    """Test the LoggerConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = LoggerConfig()
        
        assert config.log_level == "INFO"
        assert config.log_format == "json"
        assert config.log_file is None
        assert config.cloudwatch_log_group is None
        assert config.cloudwatch_region == "us-east-1"
        assert config.enable_console is True
        assert config.enable_cloudwatch is False
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = LoggerConfig(
            log_level="DEBUG",
            log_format="console",
            log_file="/tmp/test.log",
            cloudwatch_log_group="test-group",
            cloudwatch_region="us-west-2",
            enable_console=False,
            enable_cloudwatch=True
        )
        
        assert config.log_level == "DEBUG"
        assert config.log_format == "console"
        assert config.log_file == "/tmp/test.log"
        assert config.cloudwatch_log_group == "test-group"
        assert config.cloudwatch_region == "us-west-2"
        assert config.enable_console is False
        assert config.enable_cloudwatch is True
    
    def test_cloudwatch_enabled_requires_log_group(self):
        """Test that CloudWatch is only enabled when log group is provided."""
        config = LoggerConfig(enable_cloudwatch=True)
        assert config.enable_cloudwatch is False  # No log group provided
        
        config = LoggerConfig(
            enable_cloudwatch=True,
            cloudwatch_log_group="test-group"
        )
        assert config.enable_cloudwatch is True


class TestCloudWatchHandler:
    """Test the CloudWatch logging handler."""
    
    @patch('boto3.client')
    def test_handler_initialization_success(self, mock_boto_client):
        """Test successful CloudWatch handler initialization."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        
        handler = CloudWatchHandler("test-group", "test-stream")
        
        assert handler.log_group == "test-group"
        assert handler.log_stream == "test-stream"
        assert handler._enabled is True
        mock_boto_client.assert_called_once_with('logs', region_name='us-east-1')
    
    @patch('boto3.client')
    def test_handler_initialization_failure(self, mock_boto_client):
        """Test CloudWatch handler initialization with credential failure."""
        from botocore.exceptions import NoCredentialsError
        mock_boto_client.side_effect = NoCredentialsError()
        
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            handler = CloudWatchHandler("test-group")
            
            assert handler._enabled is False
            assert "CloudWatch logging unavailable" in mock_stderr.getvalue()
    
    def test_log_stream_name_generation(self):
        """Test automatic log stream name generation."""
        with patch('boto3.client') as mock_boto_client:
            from botocore.exceptions import NoCredentialsError
            mock_boto_client.side_effect = NoCredentialsError()
            
            with patch('sys.stderr', new_callable=StringIO):
                handler = CloudWatchHandler("test-group")
                
                # Should generate a name with hostname and timestamp
                assert "_" in handler.log_stream
                assert len(handler.log_stream) > 10
    
    @patch('boto3.client')
    def test_emit_log_record(self, mock_boto_client):
        """Test emitting a log record to CloudWatch."""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.put_log_events.return_value = {'nextSequenceToken': 'token123'}
        
        handler = CloudWatchHandler("test-group", "test-stream")
        handler.setFormatter(logging.Formatter('%(message)s'))
        
        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        handler.emit(record)
        
        # Verify CloudWatch API call
        mock_client.put_log_events.assert_called_once()
        call_args = mock_client.put_log_events.call_args[1]
        assert call_args['logGroupName'] == "test-group"
        assert call_args['logStreamName'] == "test-stream"
        assert len(call_args['logEvents']) == 1
        assert call_args['logEvents'][0]['message'] == "Test message"


class TestLoggingSetup:
    """Test the logging setup functionality."""
    
    def test_setup_logging_default_config(self):
        """Test setting up logging with default configuration."""
        logger = setup_logging()
        
        assert logger is not None
        assert logger.name == "eks_upgrade_agent"
    
    def test_setup_logging_custom_config(self):
        """Test setting up logging with custom configuration."""
        config = LoggerConfig(
            log_level="DEBUG",
            log_format="console",
            enable_console=True
        )
        
        logger = setup_logging(config)
        
        assert logger is not None
        # The logger itself should be configured properly
        assert logger.name == "eks_upgrade_agent"
    
    def test_setup_logging_with_file_output(self):
        """Test setting up logging with file output."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            config = LoggerConfig(
                log_file=tmp_file.name,
                enable_console=False
            )
            
            logger = setup_logging(config)
            
            # Test that we can log to the file
            logger.info("Test message")
            
            # Verify file was created and contains log
            log_path = Path(tmp_file.name)
            assert log_path.exists()
    
    @patch('src.eks_upgrade_agent.common.logger.CloudWatchHandler')
    def test_setup_logging_with_cloudwatch(self, mock_cloudwatch_handler):
        """Test setting up logging with CloudWatch integration."""
        mock_handler = Mock()
        mock_cloudwatch_handler.return_value = mock_handler
        
        config = LoggerConfig(
            cloudwatch_log_group="test-group",
            enable_cloudwatch=True
        )
        
        logger = setup_logging(config)
        
        mock_cloudwatch_handler.assert_called_once_with(
            log_group="test-group",
            region="us-east-1"
        )
        assert logger is not None


class TestLoggingProcessors:
    """Test the custom logging processors."""
    
    def test_add_context_processor(self):
        """Test the context processor adds common fields."""
        logger = Mock()
        event_dict = {"message": "test"}
        
        result = add_context_processor(logger, "info", event_dict)
        
        assert "timestamp" in result
        assert result["level"] == "INFO"
        assert "process_id" in result
        assert "thread_name" in result
    
    def test_add_exception_processor_with_custom_exception(self):
        """Test exception processor with custom EKS exception."""
        logger = Mock()
        custom_exception = PerceptionError("Test error", source="test")
        event_dict = {"exc_info": (None, custom_exception, None)}
        
        result = add_exception_processor(logger, "error", event_dict)
        
        assert "exception" in result
        assert result["exception"]["error_type"] == "PerceptionError"
        assert result["exception"]["message"] == "Test error"
        assert "exc_info" not in result  # Should be removed
    
    def test_add_exception_processor_with_standard_exception(self):
        """Test exception processor with standard Python exception."""
        logger = Mock()
        standard_exception = ValueError("Standard error")
        event_dict = {"exc_info": (None, standard_exception, None)}
        
        with patch('structlog.processors.format_exc_info') as mock_format_exc:
            mock_format_exc.return_value = "Formatted traceback"
            
            result = add_exception_processor(logger, "error", event_dict)
            
            assert "exception" in result
            assert result["exception"]["type"] == "ValueError"
            assert result["exception"]["message"] == "Standard error"
            assert result["exception"]["traceback"] == "Formatted traceback"


class TestLoggingUtilities:
    """Test the logging utility functions."""
    
    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger("test_logger")
        
        assert logger is not None
        assert logger.name == "test_logger"
    
    def test_get_logger_default_name(self):
        """Test getting a logger with default name."""
        logger = get_logger()
        
        assert logger is not None
        assert logger.name == "eks_upgrade_agent"
    
    def test_log_exception_with_custom_exception(self):
        """Test logging a custom exception."""
        logger = Mock()
        custom_exception = PerceptionError("Test error", source="test")
        
        log_exception(logger, custom_exception, "Custom error occurred", cluster="test")
        
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert call_args[0][0] == "Custom error occurred"
        assert "exception_data" in call_args[1]
        assert call_args[1]["cluster"] == "test"
    
    def test_log_exception_with_standard_exception(self):
        """Test logging a standard exception."""
        logger = Mock()
        standard_exception = ValueError("Standard error")
        
        log_exception(logger, standard_exception, "Standard error occurred")
        
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert call_args[0][0] == "Standard error occurred"
        assert call_args[1]["exc_info"] == standard_exception
    
    def test_log_upgrade_step(self):
        """Test logging upgrade step progress."""
        logger = Mock()
        
        log_upgrade_step(
            logger,
            "Deploy Applications",
            "step_123",
            "started",
            cluster="test-cluster"
        )
        
        logger.info.assert_called_once()
        call_args = logger.info.call_args
        assert call_args[0][0] == "Upgrade step started"
        assert call_args[1]["step_name"] == "Deploy Applications"
        assert call_args[1]["step_id"] == "step_123"
        assert call_args[1]["status"] == "started"
        assert call_args[1]["cluster"] == "test-cluster"
    
    def test_log_aws_api_call_success(self):
        """Test logging successful AWS API call."""
        logger = Mock()
        
        log_aws_api_call(
            logger,
            "bedrock",
            "invoke_model",
            True,
            duration_ms=150.5,
            model_id="claude-3"
        )
        
        logger.info.assert_called_once()
        call_args = logger.info.call_args
        assert call_args[0][0] == "AWS API call succeeded"
        assert call_args[1]["aws_service"] == "bedrock"
        assert call_args[1]["aws_operation"] == "invoke_model"
        assert call_args[1]["success"] is True
        assert call_args[1]["duration_ms"] == 150.5
        assert call_args[1]["model_id"] == "claude-3"
    
    def test_log_aws_api_call_failure(self):
        """Test logging failed AWS API call."""
        logger = Mock()
        
        log_aws_api_call(
            logger,
            "comprehend",
            "detect_entities",
            False,
            error_code="ThrottlingException"
        )
        
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert call_args[0][0] == "AWS API call failed"
        assert call_args[1]["aws_service"] == "comprehend"
        assert call_args[1]["aws_operation"] == "detect_entities"
        assert call_args[1]["success"] is False
        assert call_args[1]["error_code"] == "ThrottlingException"