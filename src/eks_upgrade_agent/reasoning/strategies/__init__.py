"""
Upgrade strategy implementations for the EKS Upgrade Agent.

This module contains different upgrade strategies including Blue/Green
and in-place upgrade approaches.
"""

from .base_strategy import UpgradeStrategy
from .blue_green import BlueGreenStrategy
from .in_place import InPlaceStrategy

__all__ = [
    "UpgradeStrategy",
    "BlueGreenStrategy", 
    "InPlaceStrategy",
]