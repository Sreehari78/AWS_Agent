"""AWS Comprehend client initialization and management."""

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from typing import Optional

from ...models.aws_ai import AWSAIConfig
from ...logging import get_logger
from ...handler import AWSServiceError

logger = get_logger(__name__)


class AWSComprehendClient:
    """Manages AWS Comprehend boto3 client initialization."""

    def __init__(self, config: AWSAIConfig):
        """
        Initialize AWS client manager.
        
        Args:
            config: AWS AI configuration
        """
        self.config = config
        self._client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the boto3 Comprehend client."""
        try:
            if self.config.aws_profile:
                session = boto3.Session(profile_name=self.config.aws_profile)
            else:
                session = boto3.Session(
                    aws_access_key_id=self.config.aws_access_key_id,
                    aws_secret_access_key=self.config.aws_secret_access_key,
                    aws_session_token=self.config.aws_session_token
                )
            
            self._client = session.client(
                'comprehend',
                region_name=self.config.comprehend_region
            )
            
            logger.info("Successfully initialized Comprehend client")
            
        except Exception as e:
            logger.error("Failed to initialize Comprehend client", error=str(e))
            raise AWSServiceError(f"Failed to initialize Comprehend client: {e}")

    @property
    def client(self):
        """Get the boto3 Comprehend client."""
        if not self._client:
            raise AWSServiceError("Comprehend client not initialized")
        return self._client

    def is_initialized(self) -> bool:
        """Check if client is initialized."""
        return self._client is not None