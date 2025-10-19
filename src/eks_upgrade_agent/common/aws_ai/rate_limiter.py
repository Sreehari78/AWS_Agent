"""
Rate limiting functionality for AWS AI services.
"""

import time
from typing import List

import structlog

logger = structlog.get_logger(__name__)


class BedrockRateLimitError(Exception):
    """Raised when Bedrock rate limits are exceeded."""
    pass


class RateLimiter:
    """
    Rate limiter for API requests with sliding window approach.
    """

    def __init__(self, max_requests_per_minute: int):
        """
        Initialize rate limiter.
        
        Args:
            max_requests_per_minute: Maximum requests allowed per minute
        """
        self.max_requests_per_minute = max_requests_per_minute
        self._request_times: List[float] = []
        self.logger = logger.bind(component="rate_limiter")

    def check_rate_limit(self) -> None:
        """
        Check if we're within rate limits.
        
        Raises:
            BedrockRateLimitError: If rate limit is exceeded
        """
        current_time = time.time()
        
        # Remove requests older than 1 minute
        self._request_times = [
            t for t in self._request_times if current_time - t < 60
        ]
        
        if len(self._request_times) >= self.max_requests_per_minute:
            self.logger.warning(
                "Rate limit exceeded",
                current_requests=len(self._request_times),
                limit=self.max_requests_per_minute,
            )
            raise BedrockRateLimitError(
                f"Rate limit exceeded: {len(self._request_times)} requests in last minute"
            )

    def record_request(self) -> None:
        """Record a new request for rate limiting."""
        self._request_times.append(time.time())
        
        self.logger.debug(
            "Request recorded",
            current_requests=len(self._request_times),
            limit=self.max_requests_per_minute,
        )

    def get_current_usage(self) -> int:
        """
        Get current number of requests in the last minute.
        
        Returns:
            Number of requests in the last minute
        """
        current_time = time.time()
        self._request_times = [
            t for t in self._request_times if current_time - t < 60
        ]
        return len(self._request_times)