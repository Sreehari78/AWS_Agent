"""
Low-level model invocation with retry logic for Amazon Bedrock.
"""

import json
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import structlog

from ..models.aws_ai import AWSAIConfig
from ..handler.aws_service import AWSServiceError
from .rate_limiter import RateLimiter
from .cost_tracker import CostTracker

logger = structlog.get_logger(__name__)


class ModelInvoker:
    """
    Low-level Bedrock model invoker with retry logic and error handling.
    """

    def __init__(self, config: AWSAIConfig, rate_limiter: RateLimiter, cost_tracker: CostTracker):
        """
        Initialize model invoker.
        
        Args:
            config: AWS AI configuration
            rate_limiter: Rate limiter instance
            cost_tracker: Cost tracker instance
        """
        self.config = config
        self.rate_limiter = rate_limiter
        self.cost_tracker = cost_tracker
        self.logger = logger.bind(component="model_invoker")
        
        # Initialize boto3 client
        self.client = self._create_bedrock_client()

    def _create_bedrock_client(self):
        """Create and configure Bedrock client."""
        session_kwargs = {}
        if self.config.aws_profile:
            session_kwargs["profile_name"] = self.config.aws_profile
        
        session = boto3.Session(**session_kwargs)
        return session.client(
            "bedrock-runtime",
            region_name=self.config.bedrock_region,
            aws_access_key_id=self.config.aws_access_key_id,
            aws_secret_access_key=self.config.aws_secret_access_key,
            aws_session_token=self.config.aws_session_token,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ClientError, BotoCoreError)),
        before_sleep=before_sleep_log(logger, "warning"),
    )
    def invoke_model(
        self,
        model_id: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Invoke Bedrock model with retry logic.
        
        Args:
            model_id: Bedrock model ID
            body: Request body
            
        Returns:
            Model response
            
        Raises:
            AWSServiceError: If the request fails after retries
        """
        try:
            # Check limits before making request
            self.rate_limiter.check_rate_limit()
            self.cost_tracker.check_cost_threshold()
            
            # Record request for rate limiting
            self.rate_limiter.record_request()
            
            self.logger.info(
                "Invoking Bedrock model",
                model_id=model_id,
                body_size=len(json.dumps(body)),
            )
            
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            
            response_body = json.loads(response["body"].read())
            
            # Update cost tracking if token usage is available
            if "usage" in response_body:
                self.cost_tracker.update_cost_tracking(response_body["usage"])
            
            self.logger.info(
                "Model invocation successful",
                model_id=model_id,
                response_size=len(json.dumps(response_body)),
            )
            
            return response_body
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.logger.error(
                "Bedrock API error",
                error_code=error_code,
                error_message=str(e),
                model_id=model_id,
            )
            raise AWSServiceError(f"Bedrock API error: {error_code} - {str(e)}") from e
            
        except BotoCoreError as e:
            self.logger.error(
                "Boto3 error",
                error_message=str(e),
                model_id=model_id,
            )
            raise AWSServiceError(f"Boto3 error: {str(e)}") from e