"""Shared fixtures for logging tests."""

import pytest
import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from io import StringIO

from src.eks_upgrade_agent.common.logging import LoggerConfig


@pytest.fixture
def temp_log_file():
    """Create a temporary log file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        temp_path = Path(f.name)
    yield temp_path
    # Cleanup - handle Windows file locking issues
    try:
        if temp_path.exists():
            # Force close any open handles and delete
            import gc
            gc.collect()
            temp_path.unlink(missing_ok=True)
    except (PermissionError, OSError):
        # On Windows, files might still be locked - ignore cleanup errors
        pass


@pytest.fixture
def logger_config():
    """Create a basic logger configuration."""
    return LoggerConfig(
        log_level="DEBUG",
        log_format="json",
        enable_console=True,
        enable_cloudwatch=False
    )


@pytest.fixture
def logger_config_with_file(temp_log_file):
    """Create logger configuration with file output."""
    return LoggerConfig(
        log_level="INFO",
        log_format="json",
        log_file=str(temp_log_file),
        enable_console=False,
        enable_cloudwatch=False
    )


@pytest.fixture
def mock_cloudwatch_client():
    """Mock CloudWatch Logs client."""
    with patch('boto3.client') as mock_client:
        mock_cw = Mock()
        mock_client.return_value = mock_cw
        yield mock_cw


@pytest.fixture
def captured_logs():
    """Capture log output for testing."""
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    # Cleanup
    root_logger.removeHandler(handler)


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    mock_log = Mock(spec=logging.Logger)
    mock_log.level = logging.INFO
    mock_log.debug = Mock()
    mock_log.info = Mock()
    mock_log.warning = Mock()
    mock_log.error = Mock()
    mock_log.critical = Mock()
    return mock_log


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration after each test."""
    yield
    # Clear all handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Reset level
    root_logger.setLevel(logging.WARNING)