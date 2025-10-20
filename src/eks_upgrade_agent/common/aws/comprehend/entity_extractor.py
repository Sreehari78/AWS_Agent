"""Entity extraction functionality for Amazon Comprehend."""

from typing import Dict, List, Optional
import re

from ...models.aws_ai import ComprehendEntity
from ...logging import get_logger
from .patterns import KubernetesPatterns

logger = get_logger(__name__)


class EntityExtractor:
    """Extracts and processes entities from Comprehend NER results."""

    def __init__(self, min_confidence: float = 0.5):
        """
        Initialize entity extractor.
        
        Args:
            min_confidence: Minimum confidence threshold for entities
        """
        self.min_confidence = min_confidence
        self.patterns = KubernetesPatterns()
        logger.info("Initialized EntityExtractor", min_confidence=min_confidence)

    def extract_kubernetes_entities(self, text: str) -> List[ComprehendEntity]:
        """
        Extract Kubernetes-specific entities using pattern matching.
        
        Args:
            text: Input text to analyze
            
        Returns:
            List of extracted Kubernetes entities
        """
        entities = []
        
        for entity_type, patterns in self.patterns.ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entity = ComprehendEntity(
                        text=match.group(),
                        type=entity_type,
                        confidence=self.patterns.CONFIDENCE_THRESHOLDS.get(entity_type, 0.8),
                        begin_offset=match.start(),
                        end_offset=match.end(),
                        category="KUBERNETES",
                        subcategory=entity_type
                    )
                    entities.append(entity)
        
        logger.debug(
            "Extracted Kubernetes entities",
            entity_count=len(entities),
            text_length=len(text)
        )
        
        return entities

    def filter_entities_by_confidence(
        self, 
        entities: List[ComprehendEntity],
        min_confidence: Optional[float] = None
    ) -> List[ComprehendEntity]:
        """
        Filter entities by confidence threshold.
        
        Args:
            entities: List of entities to filter
            min_confidence: Minimum confidence threshold (uses instance default if None)
            
        Returns:
            Filtered list of entities
        """
        threshold = min_confidence or self.min_confidence
        filtered = [e for e in entities if e.confidence >= threshold]
        
        logger.debug(
            "Filtered entities by confidence",
            original_count=len(entities),
            filtered_count=len(filtered),
            threshold=threshold
        )
        
        return filtered

    def group_entities_by_type(
        self, 
        entities: List[ComprehendEntity]
    ) -> Dict[str, List[ComprehendEntity]]:
        """
        Group entities by their type.
        
        Args:
            entities: List of entities to group
            
        Returns:
            Dictionary mapping entity types to lists of entities
        """
        grouped = {}
        for entity in entities:
            if entity.type not in grouped:
                grouped[entity.type] = []
            grouped[entity.type].append(entity)
        
        logger.debug(
            "Grouped entities by type",
            total_entities=len(entities),
            unique_types=len(grouped)
        )
        
        return grouped

    def extract_breaking_changes(
        self, 
        entities: List[ComprehendEntity],
        text: str
    ) -> List[Dict[str, any]]:
        """
        Extract breaking change information from entities and text.
        
        Args:
            entities: List of entities
            text: Original text
            
        Returns:
            List of breaking change information
        """
        breaking_changes = []
        
        # Find breaking change indicators
        breaking_entities = [
            e for e in entities 
            if e.type == "BREAKING_CHANGE_INDICATORS" or 
               "deprecat" in e.text.lower() or 
               "remov" in e.text.lower() or
               "breaking" in e.text.lower()
        ]
        
        for entity in breaking_entities:
            # Extract surrounding context
            start = max(0, entity.begin_offset - 100)
            end = min(len(text), entity.end_offset + 100)
            context = text[start:end].strip()
            
            breaking_change = {
                "indicator": entity.text,
                "confidence": entity.confidence,
                "context": context,
                "position": {
                    "start": entity.begin_offset,
                    "end": entity.end_offset
                }
            }
            breaking_changes.append(breaking_change)
        
        logger.info(
            "Extracted breaking changes",
            breaking_change_count=len(breaking_changes)
        )
        
        return breaking_changes

    def extract_api_deprecations(
        self, 
        entities: List[ComprehendEntity],
        text: str
    ) -> List[Dict[str, any]]:
        """
        Extract API deprecation information.
        
        Args:
            entities: List of entities
            text: Original text
            
        Returns:
            List of API deprecation information
        """
        deprecations = []
        
        # Find API versions and resource kinds near deprecation indicators
        api_versions = [e for e in entities if e.type == "API_VERSION"]
        resource_kinds = [e for e in entities if e.type == "RESOURCE_KIND"]
        breaking_indicators = [
            e for e in entities 
            if e.type == "BREAKING_CHANGE_INDICATORS" or "deprecat" in e.text.lower()
        ]
        
        for indicator in breaking_indicators:
            # Find nearby API versions and resource kinds (within 200 characters)
            nearby_apis = [
                api for api in api_versions 
                if abs(api.begin_offset - indicator.begin_offset) <= 200
            ]
            nearby_resources = [
                res for res in resource_kinds 
                if abs(res.begin_offset - indicator.begin_offset) <= 200
            ]
            
            if nearby_apis or nearby_resources:
                deprecation = {
                    "indicator": indicator.text,
                    "confidence": indicator.confidence,
                    "api_versions": [api.text for api in nearby_apis],
                    "resource_kinds": [res.text for res in nearby_resources],
                    "context_start": max(0, indicator.begin_offset - 150),
                    "context_end": min(len(text), indicator.end_offset + 150)
                }
                deprecations.append(deprecation)
        
        logger.info(
            "Extracted API deprecations",
            deprecation_count=len(deprecations)
        )
        
        return deprecations

    def validate_entities(self, entities: List[ComprehendEntity]) -> Dict[str, any]:
        """
        Validate extracted entities and provide quality metrics.
        
        Args:
            entities: List of entities to validate
            
        Returns:
            Validation results and quality metrics
        """
        if not entities:
            return {
                "valid": True,
                "entity_count": 0,
                "avg_confidence": 0.0,
                "confidence_distribution": {},
                "issues": []
            }
        
        issues = []
        confidence_scores = [e.confidence for e in entities]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        # Check for overlapping entities
        sorted_entities = sorted(entities, key=lambda e: e.begin_offset)
        for i in range(len(sorted_entities) - 1):
            current = sorted_entities[i]
            next_entity = sorted_entities[i + 1]
            if current.end_offset > next_entity.begin_offset:
                issues.append(f"Overlapping entities: '{current.text}' and '{next_entity.text}'")
        
        # Check confidence distribution
        confidence_ranges = {
            "high (>0.8)": len([c for c in confidence_scores if c > 0.8]),
            "medium (0.5-0.8)": len([c for c in confidence_scores if 0.5 <= c <= 0.8]),
            "low (<0.5)": len([c for c in confidence_scores if c < 0.5])
        }
        
        validation_result = {
            "valid": len(issues) == 0,
            "entity_count": len(entities),
            "avg_confidence": avg_confidence,
            "confidence_distribution": confidence_ranges,
            "issues": issues
        }
        
        logger.debug("Validated entities", **validation_result)
        
        return validation_result