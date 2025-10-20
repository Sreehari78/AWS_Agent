"""Unit tests for ComprehendRateLimiter."""

import pytest
import time
from unittest.mock import patch
from src.eks_upgrade_agent.common.aws.comprehend.rate_limiter import ComprehendRateLimiter


class TestComprehendRateLimiter:
    """Test cases for ComprehendRateLimiter."""

    def test_initialization(self):
        """Test rate limiter initialization."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=100)
        
        assert limiter.max_requests_per_minute == 100
        assert len(limiter.requests) == 0
        assert limiter._lock is False

    def test_can_make_request_empty(self):
        """Test can_make_request with no previous requests."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=100)
        
        assert limiter.can_make_request() is True

    def test_can_make_request_under_limit(self):
        """Test can_make_request when under the limit."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=100)
        
        # Add some requests
        current_time = time.time()
        for i in range(50):
            limiter.requests.append(current_time - i)
        
        assert limiter.can_make_request() is True

    def test_can_make_request_at_limit(self):
        """Test can_make_request when at the limit."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=10)
        
        # Add requests up to the limit
        current_time = time.time()
        for i in range(10):
            limiter.requests.append(current_time - i)
        
        assert limiter.can_make_request() is False

    def test_record_request(self):
        """Test recording a request."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=100)
        
        initial_count = len(limiter.requests)
        limiter.record_request()
        
        assert len(limiter.requests) == initial_count + 1
        assert limiter.requests[-1] <= time.time()

    def test_cleanup_old_requests(self):
        """Test cleanup of old requests."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=100)
        
        current_time = time.time()
        # Add old requests (older than 60 seconds)
        limiter.requests.append(current_time - 70)
        limiter.requests.append(current_time - 65)
        # Add recent requests
        limiter.requests.append(current_time - 30)
        limiter.requests.append(current_time - 10)
        
        limiter._cleanup_old_requests()
        
        # Only recent requests should remain
        assert len(limiter.requests) == 2
        for request_time in limiter.requests:
            assert (current_time - request_time) <= 60

    @patch('time.sleep')
    def test_wait_if_needed_no_wait(self, mock_sleep):
        """Test wait_if_needed when no wait is required."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=100)
        
        wait_time = limiter.wait_if_needed()
        
        assert wait_time is None
        mock_sleep.assert_not_called()

    @patch('time.sleep')
    @patch('time.time')
    def test_wait_if_needed_with_wait(self, mock_time, mock_sleep):
        """Test wait_if_needed when wait is required."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=2)
        
        # Mock time progression
        base_time = 1000.0
        mock_time.side_effect = [
            base_time,      # Initial cleanup
            base_time,      # can_make_request check
            base_time,      # Wait calculation
            base_time + 30  # After sleep
        ]
        
        # Fill up the rate limiter
        limiter.requests.append(base_time - 10)
        limiter.requests.append(base_time - 5)
        
        wait_time = limiter.wait_if_needed()
        
        assert wait_time > 0
        mock_sleep.assert_called_once()

    def test_get_current_usage(self):
        """Test getting current usage statistics."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=100)
        
        # Add some requests
        current_time = time.time()
        for i in range(25):
            limiter.requests.append(current_time - i)
        
        usage = limiter.get_current_usage()
        
        assert usage["current_requests"] == 25
        assert usage["max_requests_per_minute"] == 100
        assert usage["utilization_percentage"] == 25.0
        assert usage["can_make_request"] is True

    def test_get_current_usage_at_limit(self):
        """Test usage statistics when at limit."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=10)
        
        # Fill to capacity
        current_time = time.time()
        for i in range(10):
            limiter.requests.append(current_time - i)
        
        usage = limiter.get_current_usage()
        
        assert usage["current_requests"] == 10
        assert usage["utilization_percentage"] == 100.0
        assert usage["can_make_request"] is False

    def test_reset(self):
        """Test resetting the rate limiter."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=100)
        
        # Add some requests
        current_time = time.time()
        for i in range(50):
            limiter.requests.append(current_time - i)
        
        assert len(limiter.requests) == 50
        
        limiter.reset()
        
        assert len(limiter.requests) == 0
        assert limiter.can_make_request() is True

    def test_integration_record_and_cleanup(self):
        """Test integration of record_request and cleanup."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=5)
        
        # Record several requests
        for _ in range(3):
            limiter.record_request()
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        assert len(limiter.requests) == 3
        assert limiter.can_make_request() is True
        
        # Add more to reach limit
        limiter.record_request()
        limiter.record_request()
        
        assert len(limiter.requests) == 5
        assert limiter.can_make_request() is False

    @patch('time.time')
    def test_cleanup_with_mixed_timestamps(self, mock_time):
        """Test cleanup with mixed old and new timestamps."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=100)
        
        base_time = 1000.0
        mock_time.return_value = base_time
        
        # Add requests with various ages
        limiter.requests.append(base_time - 70)  # Too old
        limiter.requests.append(base_time - 50)  # Recent enough
        limiter.requests.append(base_time - 80)  # Too old
        limiter.requests.append(base_time - 30)  # Recent enough
        limiter.requests.append(base_time - 90)  # Too old
        
        limiter._cleanup_old_requests()
        
        # Should keep only the 2 recent requests
        assert len(limiter.requests) == 2
        
        # Verify remaining requests are within 60 seconds
        for request_time in limiter.requests:
            assert (base_time - request_time) <= 60

    def test_edge_case_exactly_60_seconds(self):
        """Test edge case where request is exactly 60 seconds old."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=100)
        
        current_time = time.time()
        # Add request exactly 60 seconds ago (should be kept)
        limiter.requests.append(current_time - 60.0)
        # Add request slightly more than 60 seconds ago (should be removed)
        limiter.requests.append(current_time - 60.1)
        # Add recent request (should be kept)
        limiter.requests.append(current_time - 30)
        
        limiter._cleanup_old_requests()
        
        # The 60.1 second old request should be removed, others kept
        remaining_times = list(limiter.requests)
        assert len(remaining_times) == 2
        
        # Verify the correct requests remain
        assert (current_time - 60.0) in remaining_times  # Exactly 60 seconds should be kept
        assert (current_time - 30) in remaining_times    # Recent request should be kept
        assert (current_time - 60.1) not in remaining_times  # Too old should be removed

    def test_multiple_cleanup_calls(self):
        """Test multiple cleanup calls don't cause issues."""
        limiter = ComprehendRateLimiter(max_requests_per_minute=100)
        
        current_time = time.time()
        limiter.requests.append(current_time - 30)
        limiter.requests.append(current_time - 20)
        
        # Multiple cleanups should be safe
        limiter._cleanup_old_requests()
        limiter._cleanup_old_requests()
        limiter._cleanup_old_requests()
        
        assert len(limiter.requests) == 2