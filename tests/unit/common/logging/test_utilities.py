"""Tests for logging utility functions."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from src.eks_upgrade_agent.common.logging import (
    log_exception,
    log_upgrade_step,
    log_aws_api_call
)
from src.eks_upgrade_agent.common.handler import EKSUpgradeAgentError


class TestLoggingUtilities:
    """Test logging utility functions."""

    def test_log_exception_with_exception_object(self, mock_logger):
        """Test logging exception with exception object."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            log_exception(mock_logger, e, "Test context")
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Test context" in call_args[0][0]

    def test_log_exception_with_string(self, mock_logger):
        """Test logging exception with string message."""
        log_exception(mock_logger, "String error message", "Test context")
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Test context" in call_args[0][0]
        assert "String error message" in call_args[0][0]

    def test_log_exception_with_custom_error(self, mock_logger):
        """Test logging custom EKS error."""
        error = EKSUpgradeAgentError("Custom error", error_code="TEST_001")
        log_exception(mock_logger, error, "Custom error context")
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Custom error context" in call_args[0][0]

    def test_log_upgrade_step_start(self, mock_logger):
        """Test logging upgrade step start."""
        log_upgrade_step(
            mock_logger,
            step_name="Test Step",
            action="start",
            cluster_name="test-cluster",
            upgrade_id="upgrade-123"
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Test Step" in call_args[0][0]
        assert "start" in call_args[0][0].lower()

    def test_log_upgrade_step_complete(self, mock_logger):
        """Test logging upgrade step completion."""
        log_upgrade_step(
            mock_logger,
            step_name="Test Step",
            action="complete",
            cluster_name="test-cluster",
            upgrade_id="upgrade-123",
            duration=120.5
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Test Step" in call_args[0][0]
        assert "complete" in call_args[0][0].lower()

    def test_log_upgrade_step_fail(self, mock_logger):
        """Test logging upgrade step failure."""
        log_upgrade_step(
            mock_logger,
            step_name="Test Step",
            action="fail",
            cluster_name="test-cluster",
            upgrade_id="upgrade-123",
            error="Test error occurred"
        )
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Test Step" in call_args[0][0]
        assert "fail" in call_args[0][0].lower()

    def test_log_aws_api_call_success(self, mock_logger):
        """Test logging successful AWS API call."""
        log_aws_api_call(
            mock_logger,
            service="eks",
            operation="describe_cluster",
            cluster_name="test-cluster",
            duration=1.5,
            success=True
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "eks" in call_args[0][0]
        assert "describe_cluster" in call_args[0][0]

    def test_log_aws_api_call_failure(self, mock_logger):
        """Test logging failed AWS API call."""
        log_aws_api_call(
            mock_logger,
            service="eks",
            operation="update_cluster_version",
            cluster_name="test-cluster",
            duration=2.3,
            success=False,
            error="Access denied"
        )
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "eks" in call_args[0][0]
        assert "update_cluster_version" in call_args[0][0]
        assert "Access denied" in call_args[0][0]

    def test_log_aws_api_call_with_request_id(self, mock_logger):
        """Test logging AWS API call with request ID."""
        log_aws_api_call(
            mock_logger,
            service="eks",
            operation="describe_cluster",
            cluster_name="test-cluster",
            duration=1.0,
            success=True,
            request_id="req-12345"
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "req-12345" in call_args[0][0]

    def test_log_upgrade_step_with_extra_context(self, mock_logger):
        """Test logging upgrade step with extra context."""
        log_upgrade_step(
            mock_logger,
            step_name="Test Step",
            action="start",
            cluster_name="test-cluster",
            upgrade_id="upgrade-123",
            extra_context={"node_count": 5, "version": "1.28"}
        )
        
        mock_logger.info.assert_called_once()
        # Verify extra context is included
        call_kwargs = mock_logger.info.call_args[1]
        assert "extra" in call_kwargs
        assert call_kwargs["extra"]["node_count"] == 5
        assert call_kwargs["extra"]["version"] == "1.28"

    def test_logging_utilities_with_none_values(self, mock_logger):
        """Test logging utilities handle None values gracefully."""
        # Should not raise errors
        log_exception(mock_logger, None, "Test context")
        log_upgrade_step(mock_logger, None, "start", None, None)
        log_aws_api_call(mock_logger, None, None, None, None, True)
        
        # Should have made some log calls
        assert mock_logger.error.call_count >= 1
        assert mock_logger.info.call_count >= 2