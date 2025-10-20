"""Main Amazon Comprehend client for EKS Upgrade Agent."""

from botocore.exceptions import ClientError, BotoCoreError
from typing import Dict, List, Optional, Any
import time

from ...models.aws_ai import ComprehendEntity, AWSAIConfig
from ...logging import get_logger
from ...handler import AWSServiceError
from .aws_client import AWSComprehendClient
from .rate_limiter import ComprehendRateLimiter
from .analysis_engine import AnalysisEngine

logger = get_logger(__name__)


class ComprehendClient:
    """Main client for Amazon Comprehend integration."""

    def __init__(self, config: AWSAIConfig):
        """
        Initialize Comprehend client.
        
        Args:
            config: AWS AI configuration
        """
        self.config = config
        self.aws_client = AWSComprehendClient(config)
        self.rate_limiter = ComprehendRateLimiter(
            max_requests_per_minute=config.max_comprehend_requests_per_minute
        )
        self.analysis_engine = AnalysisEngine()
        
        logger.info(
            "Initialized ComprehendClient",
            region=config.comprehend_region,
            language_code=config.comprehend_language_code
        )

    def detect_entities(
        self, 
        text: str, 
        language_code: Optional[str] = None
    ) -> List[ComprehendEntity]:
        """
        Detect named entities in text using Amazon Comprehend.
        
        Args:
            text: Text to analyze
            language_code: Language code (defaults to config value)
            
        Returns:
            List of detected entities
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for entity detection")
            return []
        
        language = language_code or self.config.comprehend_language_code
        
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        try:
            start_time = time.time()
            
            logger.debug(
                "Calling Comprehend detect_entities",
                text_length=len(text),
                language_code=language
            )
            
            response = self.aws_client.client.detect_entities(
                Text=text,
                LanguageCode=language
            )
            
            processing_time = time.time() - start_time
            self.rate_limiter.record_request()
            
            # Convert response to ComprehendEntity objects
            entities = []
            for entity_data in response.get('Entities', []):
                entity = ComprehendEntity(
                    text=entity_data['Text'],
                    type=entity_data['Type'],
                    confidence=entity_data['Score'],
                    begin_offset=entity_data['BeginOffset'],
                    end_offset=entity_data['EndOffset']
                )
                entities.append(entity)
            
            logger.info(
                "Successfully detected entities",
                entity_count=len(entities),
                processing_time=processing_time,
                text_length=len(text)
            )
            
            return entities
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.error(
                "Comprehend API error",
                error_code=error_code,
                error_message=error_message,
                text_length=len(text)
            )
            
            raise AWSServiceError(f"Comprehend API error: {error_code} - {error_message}")
            
        except BotoCoreError as e:
            logger.error("Boto3 error during entity detection", error=str(e))
            raise AWSServiceError(f"Boto3 error: {e}")
            
        except Exception as e:
            logger.error("Unexpected error during entity detection", error=str(e))
            raise AWSServiceError(f"Unexpected error: {e}")

    def analyze_kubernetes_text(self, text: str) -> Dict[str, Any]:
        """
        Comprehensive analysis of Kubernetes-related text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Comprehensive analysis results
        """
        start_time = time.time()
        
        logger.info(
            "Starting Kubernetes text analysis",
            text_length=len(text)
        )
        
        try:
            # Detect standard entities using Comprehend
            comprehend_entities = self.detect_entities(text)
            
            # Use analysis engine for comprehensive analysis
            return self.analysis_engine.analyze_kubernetes_text(text, comprehend_entities)
            
        except Exception as e:
            logger.error("Failed to analyze Kubernetes text", error=str(e))
            raise AWSServiceError(f"Failed to analyze Kubernetes text: {e}")

    def detect_breaking_changes(self, release_notes: str) -> Dict[str, Any]:
        """
        Specialized method to detect breaking changes in release notes.
        
        Args:
            release_notes: Release notes text to analyze
            
        Returns:
            Breaking change analysis results
        """
        logger.info("Analyzing release notes for breaking changes")
        
        try:
            # Detect entities first
            comprehend_entities = self.detect_entities(release_notes)
            
            # Use analysis engine for breaking change detection
            return self.analysis_engine.detect_breaking_changes(release_notes, comprehend_entities)
            
        except Exception as e:
            logger.error("Failed to detect breaking changes", error=str(e))
            raise AWSServiceError(f"Failed to detect breaking changes: {e}")



    def get_usage_statistics(self) -> Dict[str, Any]:
        """
        Get usage statistics for the Comprehend client.
        
        Returns:
            Usage statistics
        """
        rate_limit_stats = self.rate_limiter.get_current_usage()
        
        return {
            "rate_limiting": rate_limit_stats,
            "configuration": {
                "region": self.config.comprehend_region,
                "language_code": self.config.comprehend_language_code,
                "max_requests_per_minute": self.config.max_comprehend_requests_per_minute
            },
            "client_status": "active" if self.aws_client.is_initialized() else "not_initialized"
        }