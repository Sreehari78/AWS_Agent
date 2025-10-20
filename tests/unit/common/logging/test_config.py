"""Tests for logging configuration."""

import pytest
from src.eks_upgrade_agent.common.logging import LoggerConfig


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
            log_format="text",
            log_file="/tmp/test.log",
            cloudwatch_log_group="test-group",
            cloudwatch_region="us-west-2",
            enable_console=False,
            enable_cloudwatch=True
        )
        
        assert config.log_level == "DEBUG"
        assert config.log_format == "text"
        assert config.log_file == "/tmp/test.log"
        assert config.cloudwatch_log_group == "test-group"
        assert config.cloudwatch_region == "us-west-2"
        assert config.enable_console is False
        assert config.enable_cloudwatch is True

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid log levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = LoggerConfig(log_level=level)
            assert config.log_level == level
        
        # Valid log formats
        for fmt in ["json", "text"]:
            config = LoggerConfig(log_format=fmt)
            assert config.log_format == fmt

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "log_level": "WARNING",
            "log_format": "text",
            "enable_console": False,
            "enable_cloudwatch": True,
            "cloudwatch_log_group": "my-log-group"
        }
        
        config = LoggerConfig(**config_dict)
        
        assert config.log_level == "WARNING"
        assert config.log_format == "text"
        assert config.enable_console is False
        assert config.enable_cloudwatch is True
        assert config.cloudwatch_log_group == "my-log-group"

    def test_config_serialization(self):
        """Test config can be serialized."""
        config = LoggerConfig(
            log_level="DEBUG",
            cloudwatch_log_group="test-group"
        )
        
        # Should be able to convert to dict
        config_dict = {
            "log_level": config.log_level,
            "log_format": config.log_format,
            "enable_console": config.enable_console,
            "enable_cloudwatch": config.enable_cloudwatch,
            "cloudwatch_log_group": config.cloudwatch_log_group,
            "cloudwatch_region": config.cloudwatch_region
        }
        
        assert config_dict["log_level"] == "DEBUG"
        assert config_dict["cloudwatch_log_group"] == "test-group"