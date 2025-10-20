"""Amazon Comprehend integration for EKS Upgrade Agent."""

from .comprehend_client import ComprehendClient
from .entity_extractor import EntityExtractor
from .custom_classifier import CustomClassifier
from .rate_limiter import ComprehendRateLimiter
from .analysis_engine import AnalysisEngine
from .aws_client import AWSComprehendClient
from .result_processor import ResultProcessor
from .patterns import ClassificationCategory, SeverityLevel

__all__ = [
    "ComprehendClient",
    "EntityExtractor", 
    "CustomClassifier",
    "ComprehendRateLimiter",
    "AnalysisEngine",
    "AWSComprehendClient",
    "ResultProcessor",
    "ClassificationCategory",
    "SeverityLevel",
]