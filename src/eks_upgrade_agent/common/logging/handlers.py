"""
Custom logging handlers for the EKS Upgrade Agent.
"""

import logging
import sys
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class CloudWatchHandler(logging.Handler):
    """
    Custom logging handler for AWS CloudWatch Logs integration.
    
    Sends log messages to CloudWatch Logs with proper error handling
    and fallback to local logging when CloudWatch is unavailable.
    """
    
    def __init__(
        self,
        log_group: str,
        log_stream: Optional[str] = None,
        region: str = "us-east-1",
        create_log_group: bool = True
    ):
        """
        Initialize CloudWatch handler.
        
        Args:
            log_group: CloudWatch log group name
            log_stream: CloudWatch log stream name (defaults to hostname-timestamp)
            region: AWS region for CloudWatch
            create_log_group: Whether to create log group if it doesn't exist
        """
        super().__init__()
        self.log_group = log_group
        self.log_stream = log_stream or self._generate_log_stream_name()
        self.region = region
        self.create_log_group = create_log_group
        
        self._client = None
        self._sequence_token = None
        self._enabled = False
        
        # Try to initialize CloudWatch client
        self._initialize_client()
    
    def _generate_log_stream_name(self) -> str:
        """Generate a unique log stream name."""
        import socket
        hostname = socket.gethostname()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{hostname}_{timestamp}"
    
    def _initialize_client(self) -> None:
        """Initialize CloudWatch Logs client with error handling."""
        try:
            self._client = boto3.client('logs', region_name=self.region)
            
            # Test credentials and create log group/stream if needed
            if self.create_log_group:
                self._ensure_log_group_exists()
            self._ensure_log_stream_exists()
            
            self._enabled = True
            
        except (NoCredentialsError, ClientError) as e:
            # Log to stderr that CloudWatch is unavailable
            print(f"CloudWatch logging unavailable: {e}", file=sys.stderr)
            self._enabled = False
    
    def _ensure_log_group_exists(self) -> None:
        """Create log group if it doesn't exist."""
        try:
            self._client.create_log_group(logGroupName=self.log_group)
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
    
    def _ensure_log_stream_exists(self) -> None:
        """Create log stream if it doesn't exist."""
        try:
            self._client.create_log_stream(
                logGroupName=self.log_group,
                logStreamName=self.log_stream
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to CloudWatch.
        
        Args:
            record: Log record to emit
        """
        if not self._enabled or not self._client:
            return
        
        try:
            # Format the log message
            message = self.format(record)
            
            # Prepare log event
            log_event = {
                'timestamp': int(record.created * 1000),  # CloudWatch expects milliseconds
                'message': message
            }
            
            # Send to CloudWatch
            kwargs = {
                'logGroupName': self.log_group,
                'logStreamName': self.log_stream,
                'logEvents': [log_event]
            }
            
            if self._sequence_token:
                kwargs['sequenceToken'] = self._sequence_token
            
            response = self._client.put_log_events(**kwargs)
            self._sequence_token = response.get('nextSequenceToken')
            
        except Exception as e:
            # Fallback to stderr if CloudWatch fails
            print(f"CloudWatch logging failed: {e}", file=sys.stderr)
            print(f"Log message: {self.format(record)}", file=sys.stderr)