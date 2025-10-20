"""Analysis engine that coordinates different Comprehend analysis components."""

import time
from typing import Dict, List, Any
from datetime import datetime, UTC

from ...models.aws_ai import ComprehendEntity
from ...logging import get_logger
from .entity_extractor import EntityExtractor
from .custom_classifier import CustomClassifier
from .result_processor import ResultProcessor

logger = get_logger(__name__)


class AnalysisEngine:
    """Coordinates different analysis components for comprehensive text analysis."""

    def __init__(self):
        """Initialize analysis engine."""
        self.entity_extractor = EntityExtractor()
        self.custom_classifier = CustomClassifier()
        self.result_processor = ResultProcessor()
        logger.info("Initialized AnalysisEngine")

    def analyze_kubernetes_text(
        self, 
        text: str, 
        comprehend_entities: List[ComprehendEntity]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive Kubernetes text analysis.
        
        Args:
            text: Text to analyze
            comprehend_entities: Entities detected by Comprehend
            
        Returns:
            Comprehensive analysis results
        """
        start_time = time.time()
        analysis_id = f"comprehend_{int(datetime.now(UTC).timestamp())}"
        
        logger.info("Starting Kubernetes text analysis", text_length=len(text))
        
        try:
            # Extract Kubernetes-specific entities
            k8s_entities = self.entity_extractor.extract_kubernetes_entities(text)
            
            # Combine and filter entities
            all_entities = comprehend_entities + k8s_entities
            filtered_entities = self.entity_extractor.filter_entities_by_confidence(all_entities)
            
            # Custom classification
            classifications = self.custom_classifier.classify_text(text)
            
            # Kubernetes context analysis
            k8s_context = self.custom_classifier.analyze_kubernetes_context(text)
            
            # Extract breaking changes and deprecations
            breaking_changes = self.entity_extractor.extract_breaking_changes(filtered_entities, text)
            deprecations = self.entity_extractor.extract_api_deprecations(filtered_entities, text)
            
            # Extract action items
            action_items = self.custom_classifier.extract_action_items(classifications, text)
            
            # Validate results
            entity_validation = self.entity_extractor.validate_entities(filtered_entities)
            classification_validation = self.custom_classifier.validate_classification_results(classifications)
            
            processing_time = time.time() - start_time
            
            # Create comprehensive result
            result = self.result_processor.create_analysis_result(
                analysis_id=analysis_id,
                input_text=text,
                processing_time=processing_time,
                comprehend_entities=comprehend_entities,
                k8s_entities=k8s_entities,
                filtered_entities=filtered_entities,
                classifications=classifications,
                k8s_context=k8s_context,
                breaking_changes=breaking_changes,
                deprecations=deprecations,
                action_items=action_items,
                entity_validation=entity_validation,
                classification_validation=classification_validation
            )
            
            logger.info(
                "Completed Kubernetes text analysis",
                processing_time=processing_time,
                entity_count=len(filtered_entities),
                classification_count=len(classifications),
                breaking_change_count=len(breaking_changes),
                action_item_count=len(action_items)
            )
            
            return result
            
        except Exception as e:
            logger.error("Failed to analyze Kubernetes text", error=str(e))
            raise

    def detect_breaking_changes(self, release_notes: str, comprehend_entities: List[ComprehendEntity]) -> Dict[str, Any]:
        """
        Specialized method to detect breaking changes in release notes.
        
        Args:
            release_notes: Release notes text to analyze
            comprehend_entities: Entities detected by Comprehend
            
        Returns:
            Breaking change analysis results
        """
        logger.info("Analyzing release notes for breaking changes")
        
        try:
            # Perform full analysis
            analysis = self.analyze_kubernetes_text(release_notes, comprehend_entities)
            
            # Create breaking change specific result
            result = self.result_processor.create_breaking_change_result(analysis)
            
            logger.info(
                "Completed breaking change analysis",
                breaking_change_count=len(result["breaking_changes"]),
                critical_action_count=len(result["critical_actions"]),
                overall_severity=result["severity_assessment"]["overall_score"]
            )
            
            return result
            
        except Exception as e:
            logger.error("Failed to detect breaking changes", error=str(e))
            raise