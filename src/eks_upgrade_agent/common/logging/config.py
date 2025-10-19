"""
Logging configuration for the EKS Upgrade Agent.
"""

from typing import Optional


class LoggerConfig:
    """Configuration class for logging setup."""
    
    def __init__(
        self,
        log_level: str = "INFO",
        log_format: str = "json",
        log_file: Optional[str] = None,
        cloudwatch_log_group: Optional[str] = None,
        cloudwatch_region: str = "us-east-1",
        enable_console: bool = True,
        enable_cloudwatch: bool = False
    ):
        """
        Initialize logger configuration.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_format: Log format ('json' or 'console')
            log_file: Path to log file (optional)
            cloudwatch_log_group: CloudWatch log group name (optional)
            cloudwatch_region: AWS region for CloudWatch
            enable_console: Whether to enable console logging
            enable_cloudwatch: Whether to enable CloudWatch logging
        """
        self.log_level = log_level.upper()
        self.log_format = log_format
        self.log_file = log_file
        self.cloudwatch_log_group = cloudwatch_log_group
        self.cloudwatch_region = cloudwatch_region
        self.enable_console = enable_console
        self.enable_cloudwatch = enable_cloudwatch and cloudwatch_log_group is not None