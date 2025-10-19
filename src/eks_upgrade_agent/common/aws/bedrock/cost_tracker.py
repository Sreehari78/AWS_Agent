"""
Cost tracking and threshold management for AWS AI services.
"""

from datetime import datetime, UTC
from typing import Dict, Any

import structlog

logger = structlog.get_logger(__name__)


class BedrockCostThresholdError(Exception):
    """Raised when cost thresholds are exceeded."""
    pass


class CostTracker:
    """
    Cost tracking and threshold management for Bedrock usage.
    """

    def __init__(self, cost_threshold_usd: float):
        """
        Initialize cost tracker.
        
        Args:
            cost_threshold_usd: Daily cost threshold in USD
        """
        self.cost_threshold_usd = cost_threshold_usd
        self._daily_cost: float = 0.0
        self._last_cost_reset: datetime = datetime.now(UTC)
        self.logger = logger.bind(component="cost_tracker")

    def check_cost_threshold(self) -> None:
        """
        Check if we're within cost thresholds.
        
        Raises:
            BedrockCostThresholdError: If cost threshold is exceeded
        """
        self._reset_daily_cost_if_needed()
        
        if self._daily_cost >= self.cost_threshold_usd:
            self.logger.warning(
                "Cost threshold exceeded",
                daily_cost=self._daily_cost,
                threshold=self.cost_threshold_usd,
            )
            raise BedrockCostThresholdError(
                f"Daily cost threshold exceeded: ${self._daily_cost:.2f}"
            )

    def _reset_daily_cost_if_needed(self) -> None:
        """Reset daily cost if it's a new day."""
        current_date = datetime.now(UTC).date()
        last_reset_date = self._last_cost_reset.date()
        
        if current_date > last_reset_date:
            self.logger.info(
                "Resetting daily cost for new day",
                previous_cost=self._daily_cost,
                reset_date=current_date,
            )
            self._daily_cost = 0.0
            self._last_cost_reset = datetime.now(UTC)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for Claude 3 Sonnet usage.
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Estimated cost in USD
        """
        # Claude 3 Sonnet pricing (as of 2024)
        input_cost_per_1k = 0.003  # $0.003 per 1K input tokens
        output_cost_per_1k = 0.015  # $0.015 per 1K output tokens
        
        input_cost = (input_tokens / 1000) * input_cost_per_1k
        output_cost = (output_tokens / 1000) * output_cost_per_1k
        
        return input_cost + output_cost

    def update_cost_tracking(self, token_usage: Dict[str, int]) -> None:
        """
        Update cost tracking with token usage.
        
        Args:
            token_usage: Dictionary containing input_tokens and output_tokens
        """
        input_tokens = token_usage.get("input_tokens", 0)
        output_tokens = token_usage.get("output_tokens", 0)
        
        cost = self.estimate_cost(input_tokens, output_tokens)
        self._daily_cost += cost
        
        self.logger.info(
            "Cost tracking updated",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            request_cost=cost,
            daily_cost=self._daily_cost,
        )

    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get cost summary.
        
        Returns:
            Cost summary dictionary
        """
        self._reset_daily_cost_if_needed()
        
        return {
            "daily_cost_usd": self._daily_cost,
            "cost_threshold_usd": self.cost_threshold_usd,
            "last_cost_reset": self._last_cost_reset.isoformat(),
        }