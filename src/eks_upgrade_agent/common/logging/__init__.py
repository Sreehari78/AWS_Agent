"""
Logging module for the EKS Upgrade Agent.

This module provides structured logging with JSON output, AWS CloudWatch integration,
and proper error context preservation.
"""

from .config import LoggerConfig
from .setup import setup_logging, get_logger, get_default_logger, init_default_logger
from .utils import log_exception, log_upgrade_step, log_aws_api_call

__all__ = [
    "LoggerConfig",
    "setup_logging",
    "get_logger",
    "get_default_logger", 
    "init_default_logger",
    "log_exception",
    "log_upgrade_step",
    "log_aws_api_call"
]