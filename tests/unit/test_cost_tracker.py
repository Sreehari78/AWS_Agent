"""
Unit tests for cost tracking functionality.
"""

from datetime import datetime, UTC
import pytest

from src.eks_upgrade_agent.common.aws.bedrock.cost_tracker import (
    CostTracker,
    BedrockCostThresholdError,
)


class TestCostTracker:
    """Test cost tracking and thresholds."""

    def test_init(self):
        """Test cost tracker initialization."""
        tracker = CostTracker(cost_threshold_usd=10.0)
        
        assert tracker.cost_threshold_usd == 10.0
        assert tracker._daily_cost == 0.0

    def test_cost_estimation(self):
        """Test cost estimation for token usage."""
        tracker = CostTracker(cost_threshold_usd=10.0)
        
        cost = tracker.estimate_cost(1000, 500)
        
        # Expected: (1000/1000 * 0.003) + (500/1000 * 0.015) = 0.003 + 0.0075 = 0.0105
        expected_cost = 0.0105
        assert abs(cost - expected_cost) < 0.0001

    def test_cost_threshold_check_within_limit(self):
        """Test cost threshold check when within limits."""
        tracker = CostTracker(cost_threshold_usd=10.0)
        tracker._daily_cost = 5.0
        
        # Should not raise exception
        tracker.check_cost_threshold()

    def test_cost_threshold_check_exceeded(self):
        """Test cost threshold check when limit is exceeded."""
        tracker = CostTracker(cost_threshold_usd=10.0)
        tracker._daily_cost = 15.0  # Exceeds threshold of 10.0
        
        with pytest.raises(BedrockCostThresholdError):
            tracker.check_cost_threshold()

    def test_daily_cost_reset(self):
        """Test that daily cost resets on new day."""
        tracker = CostTracker(cost_threshold_usd=10.0)
        
        # Set cost and old reset time
        tracker._daily_cost = 5.0
        tracker._last_cost_reset = datetime(2024, 1, 1, tzinfo=UTC)
        
        # Check threshold (should reset cost)
        tracker.check_cost_threshold()
        
        assert tracker._daily_cost == 0.0

    def test_update_cost_tracking(self):
        """Test cost tracking update with token usage."""
        tracker = CostTracker(cost_threshold_usd=10.0)
        initial_cost = tracker._daily_cost
        
        token_usage = {"input_tokens": 1000, "output_tokens": 500}
        tracker.update_cost_tracking(token_usage)
        
        expected_increase = 0.0105  # From test_cost_estimation
        assert abs(tracker._daily_cost - initial_cost - expected_increase) < 0.0001

    def test_update_cost_tracking_missing_tokens(self):
        """Test cost tracking with missing token information."""
        tracker = CostTracker(cost_threshold_usd=10.0)
        initial_cost = tracker._daily_cost
        
        token_usage = {}  # No token information
        tracker.update_cost_tracking(token_usage)
        
        # Cost should remain the same
        assert tracker._daily_cost == initial_cost

    def test_get_cost_summary(self):
        """Test cost summary generation."""
        tracker = CostTracker(cost_threshold_usd=10.0)
        tracker._daily_cost = 5.5
        
        summary = tracker.get_cost_summary()
        
        assert summary["daily_cost_usd"] == 5.5
        assert summary["cost_threshold_usd"] == 10.0
        assert "last_cost_reset" in summary

    def test_get_cost_summary_with_reset(self):
        """Test cost summary with automatic reset."""
        tracker = CostTracker(cost_threshold_usd=10.0)
        tracker._daily_cost = 5.5
        tracker._last_cost_reset = datetime(2024, 1, 1, tzinfo=UTC)
        
        summary = tracker.get_cost_summary()
        
        # Cost should be reset to 0
        assert summary["daily_cost_usd"] == 0.0