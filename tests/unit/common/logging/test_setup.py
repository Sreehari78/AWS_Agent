"""Tests for logging setup functionality."""

import pytest
import logging
import json
from unittest.mock import patch, Mock

from src.eks_upgrade_agent.common.logging import setup_logging, get_logger


class TestLoggingSetup:
    """Test logging setup functionality."""

    def test_setup_logging_console_only(self, logger_config, captured_logs):
        """Test setting up logging with console output only."""
        setup_logging(logger_config)
        
        # Get a logger and test it
        logger = get_logger("test_logger")
        logger.info("Test message")
        
        # Should have output
        log_output = captured_logs.getvalue()
        assert "Test message" in log_output

    def test_setup_logging_file_output(self, logger_config_with_file, temp_log_file):
        """Test setting up logging with file output."""
        setup_logging(logger_config_with_file)
        
        # Get a logger and test it
        logger = get_logger("test_logger")
        logger.info("Test file message")
        
        # Check file was written
        assert temp_log_file.exists()
        content = temp_log_file.read_text()
        assert "Test file message" in content

    def test_setup_logging_json_format(self, logger_config_with_file, temp_log_file):
        """Test JSON format logging."""
        logger_config_with_file.log_format = "json"
        setup_logging(logger_config_with_file)
        
        logger = get_logger("test_logger")
        logger.info("JSON test message", extra={"key": "value"})
        
        # Check JSON format
        content = temp_log_file.read_text().strip()
        log_entry = json.loads(content)
        
        assert log_entry["message"] == "JSON test message"
        assert log_entry["key"] == "value"

    def test_setup_logging_text_format(self, logger_config_with_file, temp_log_file):
        """Test text format logging."""
        logger_config_with_file.log_format = "text"
        setup_logging(logger_config_with_file)
        
        logger = get_logger("test_logger")
        logger.info("Text test message")
        
        # Check text format
        content = temp_log_file.read_text()
        assert "Text test message" in content
        assert "INFO" in content

    @patch('src.eks_upgrade_agent.common.logging.handlers.CloudWatchHandler')
    def test_setup_logging_cloudwatch(self, mock_cloudwatch_handler, logger_config):
        """Test setting up CloudWatch logging."""
        logger_config.enable_cloudwatch = True
        logger_config.cloudwatch_log_group = "test-group"
        
        # Mock the handler
        mock_handler = Mock()
        mock_cloudwatch_handler.return_value = mock_handler
        
        setup_logging(logger_config)
        
        # Verify CloudWatch handler was created
        mock_cloudwatch_handler.assert_called_once_with(
            log_group="test-group",
            region="us-east-1"
        )

    def test_setup_logging_log_levels(self, logger_config_with_file, temp_log_file):
        """Test different log levels."""
        logger_config_with_file.log_level = "WARNING"
        setup_logging(logger_config_with_file)
        
        logger = get_logger("test_logger")
        
        # These should not appear
        logger.debug("Debug message")
        logger.info("Info message")
        
        # These should appear
        logger.warning("Warning message")
        logger.error("Error message")
        
        content = temp_log_file.read_text()
        assert "Debug message" not in content
        assert "Info message" not in content
        assert "Warning message" in content
        assert "Error message" in content

    def test_get_logger_returns_same_instance(self):
        """Test that get_logger returns the same instance for same name."""
        logger1 = get_logger("test_logger")
        logger2 = get_logger("test_logger")
        
        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """Test that get_logger returns different instances for different names."""
        logger1 = get_logger("logger1")
        logger2 = get_logger("logger2")
        
        assert logger1 is not logger2
        assert logger1.name == "logger1"
        assert logger2.name == "logger2"

    def test_setup_logging_multiple_calls(self, logger_config):
        """Test that multiple setup_logging calls don't cause issues."""
        setup_logging(logger_config)
        setup_logging(logger_config)  # Should not raise error
        
        logger = get_logger("test_logger")
        assert logger is not None