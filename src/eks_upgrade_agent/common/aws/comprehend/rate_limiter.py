"""Rate limiter for Amazon Comprehend API calls."""

import time
from collections import deque
from typing import Optional

from ...logging import get_logger

logger = get_logger(__name__)


class ComprehendRateLimiter:
    """Rate limiter for Amazon Comprehend API calls using sliding window approach."""

    def __init__(self, max_requests_per_minute: int = 100):
        """
        Initialize rate limiter.
        
        Args:
            max_requests_per_minute: Maximum requests allowed per minute
        """
        self.max_requests_per_minute = max_requests_per_minute
        self.requests: deque = deque()
        self._lock = False
        
        logger.info(
            "Initialized Comprehend rate limiter",
            max_requests_per_minute=max_requests_per_minute
        )

    def can_make_request(self) -> bool:
        """
        Check if a request can be made without exceeding rate limits.
        
        Returns:
            True if request can be made, False otherwise
        """
        self._cleanup_old_requests()
        return len(self.requests) < self.max_requests_per_minute

    def wait_if_needed(self) -> Optional[float]:
        """
        Wait if necessary to respect rate limits.
        
        Returns:
            Time waited in seconds, or None if no wait was needed
        """
        if self.can_make_request():
            return None
            
        # Calculate wait time until oldest request expires
        if self.requests:
            oldest_request = self.requests[0]
            wait_time = 60.0 - (time.time() - oldest_request)
            if wait_time > 0:
                logger.info(
                    "Rate limit reached, waiting",
                    wait_time_seconds=wait_time,
                    current_requests=len(self.requests)
                )
                time.sleep(wait_time)
                return wait_time
        
        return None

    def record_request(self) -> None:
        """Record a new request timestamp."""
        current_time = time.time()
        self.requests.append(current_time)
        self._cleanup_old_requests()
        
        logger.debug(
            "Recorded Comprehend API request",
            current_requests=len(self.requests),
            max_requests=self.max_requests_per_minute
        )

    def _cleanup_old_requests(self) -> None:
        """Remove requests older than 60 seconds."""
        current_time = time.time()
        # Filter out requests older than 60 seconds (with small tolerance for floating point precision)
        self.requests = deque([
            req_time for req_time in self.requests 
            if (current_time - req_time) < 60.05  # Small tolerance for floating point precision
        ])

    def get_current_usage(self) -> dict:
        """
        Get current rate limit usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        self._cleanup_old_requests()
        return {
            "current_requests": len(self.requests),
            "max_requests_per_minute": self.max_requests_per_minute,
            "utilization_percentage": (len(self.requests) / self.max_requests_per_minute) * 100,
            "can_make_request": self.can_make_request()
        }

    def reset(self) -> None:
        """Reset the rate limiter by clearing all recorded requests."""
        self.requests.clear()
        logger.info("Reset Comprehend rate limiter")