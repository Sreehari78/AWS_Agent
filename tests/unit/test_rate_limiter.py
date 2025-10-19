"""
Unit tests for rate limiter functionality.
"""

import time
import pytest

from src.eks_upgrade_agent.common.aws.bedrock.rate_limiter import (
    RateLimiter,
    BedrockRateLimitError,
)


class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_init(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(max_requests_per_minute=10)
        
        assert limiter.max_requests_per_minute == 10
        assert len(limiter._request_times) == 0

    def test_check_rate_limit_within_limit(self):
        """Test rate limit check when within limits."""
        limiter = RateLimiter(max_requests_per_minute=5)
        
        # Should not raise exception
        limiter.check_rate_limit()

    def test_check_rate_limit_exceeded(self):
        """Test rate limit check when limit is exceeded."""
        limiter = RateLimiter(max_requests_per_minute=5)
        
        # Fill up request times to exceed limit
        current_time = time.time()
        limiter._request_times = [current_time - 30] * 6  # Exceed limit of 5
        
        with pytest.raises(BedrockRateLimitError):
            limiter.check_rate_limit()

    def test_cleanup_old_requests(self):
        """Test that old requests are cleaned up."""
        limiter = RateLimiter(max_requests_per_minute=5)
        
        current_time = time.time()
        # Add old requests (older than 1 minute)
        limiter._request_times = [current_time - 120, current_time - 90]
        # Add recent requests
        limiter._request_times.extend([current_time - 30] * 3)
        
        limiter.check_rate_limit()
        
        # Old requests should be removed
        assert len(limiter._request_times) == 3

    def test_record_request(self):
        """Test recording a request."""
        limiter = RateLimiter(max_requests_per_minute=5)
        
        initial_count = len(limiter._request_times)
        limiter.record_request()
        
        assert len(limiter._request_times) == initial_count + 1

    def test_get_current_usage(self):
        """Test getting current usage."""
        limiter = RateLimiter(max_requests_per_minute=5)
        
        # Add some recent requests
        current_time = time.time()
        limiter._request_times = [current_time - 30] * 3
        
        usage = limiter.get_current_usage()
        assert usage == 3

    def test_get_current_usage_with_cleanup(self):
        """Test getting current usage with old request cleanup."""
        limiter = RateLimiter(max_requests_per_minute=5)
        
        current_time = time.time()
        # Add old and new requests
        limiter._request_times = [
            current_time - 120,  # Old request
            current_time - 30,   # Recent request
            current_time - 10,   # Recent request
        ]
        
        usage = limiter.get_current_usage()
        assert usage == 2  # Only recent requests counted