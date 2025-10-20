"""AWS integration modules for EKS Upgrade Agent."""

from .bedrock import BedrockClient
from .comprehend import ComprehendClient

__all__ = [
    "BedrockClient",
    "ComprehendClient",
]