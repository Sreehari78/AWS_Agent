"""Result processing and validation for Comprehend analysis."""

from typing import Dict, List, Any
from datetime import datetime, UTC

from ...models.aws_ai import ComprehendEntity
from ...logging import get_logger

logger = get_logger(__name__)


class ResultProcessor:
    """Processes and validates Comprehend analysis results."""

    def __init__(self):
        """Initialize result processor."""
        logger.debug("Initialized ResultProcessor")

    def create_analysis_result(
        self,
        analysis_id: str,
        input_text: str,
        processing_time: float,
        comprehend_entities: List[ComprehendEntity],
        k8s_entities: List[ComprehendEntity],
        filtered_entities: List[ComprehendEntity],
        classifications: List[Dict[str, Any]],
        k8s_context: Dict[str, Any],
        breaking_changes: List[Dict[str, Any]],
        deprecations: List[Dict[str, Any]],
        action_items: List[Dict[str, Any]],
        entity_validation: Dict[str, Any],
        classification_validation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create comprehensive analysis result.
        
        Args:
            analysis_id: Unique analysis identifier
            input_text: Original input text
            processing_time: Time taken for analysis
            comprehend_entities: Entities from Comprehend
            k8s_entities: Kubernetes-specific entities
            filtered_entities: Filtered entities by confidence
            classifications: Classification results
            k8s_context: Kubernetes context analysis
            breaking_changes: Breaking change information
            deprecations: API deprecation information
            action_items: Extracted action items
            entity_validation: Entity validation results
            classification_validation: Classification validation results
            
        Returns:
            Comprehensive analysis result dictionary
        """
        return {
            "analysis_id": analysis_id,
            "input_text_length": len(input_text),
            "processing_time": processing_time,
            "entities": {
                "comprehend_entities": [e.model_dump() for e in comprehend_entities],
                "kubernetes_entities": [e.model_dump() for e in k8s_entities],
                "filtered_entities": [e.model_dump() for e in filtered_entities],
                "entity_count": len(filtered_entities)
            },
            "classifications": classifications,
            "kubernetes_context": k8s_context,
            "breaking_changes": breaking_changes,
            "api_deprecations": deprecations,
            "action_items": action_items,
            "validation": {
                "entities": entity_validation,
                "classifications": classification_validation
            },
            "summary": self._create_summary(
                k8s_context, breaking_changes, deprecations, action_items
            )
        }

    def create_breaking_change_result(
        self,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create breaking change specific result.
        
        Args:
            analysis: Full analysis result
            
        Returns:
            Breaking change analysis result
        """
        return {
            "analysis_id": analysis["analysis_id"],
            "breaking_changes": analysis["breaking_changes"],
            "api_deprecations": analysis["api_deprecations"],
            "critical_actions": [
                action for action in analysis["action_items"]
                if action["severity"] in ["CRITICAL", "HIGH"]
            ],
            "kubernetes_components": {
                "api_objects": analysis["kubernetes_context"]["api_objects"],
                "api_groups": analysis["kubernetes_context"]["api_groups"],
                "eks_addons": analysis["kubernetes_context"]["eks_addons"]
            },
            "severity_assessment": {
                "overall_score": self._calculate_severity_score(analysis),
                "requires_immediate_action": len([
                    a for a in analysis["action_items"] 
                    if a["severity"] == "CRITICAL"
                ]) > 0,
                "migration_required": len([
                    c for c in analysis["classifications"]
                    if c["category"] == "MIGRATION_REQUIRED"
                ]) > 0
            },
            "processing_time": analysis["processing_time"]
        }

    def _create_summary(
        self,
        k8s_context: Dict[str, Any],
        breaking_changes: List[Dict[str, Any]],
        deprecations: List[Dict[str, Any]],
        action_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create analysis summary."""
        return {
            "kubernetes_relevance_score": k8s_context["kubernetes_score"],
            "breaking_change_count": len(breaking_changes),
            "deprecation_count": len(deprecations),
            "action_item_count": len(action_items),
            "high_priority_actions": len([a for a in action_items if a["priority"] > 0.7])
        }

    def _calculate_severity_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate overall severity score from analysis results."""
        score = 0.0
        
        # Breaking changes contribute heavily to severity
        score += len(analysis["breaking_changes"]) * 3.0
        
        # API deprecations contribute moderately
        score += len(analysis["api_deprecations"]) * 2.0
        
        # Critical and high priority actions
        for action in analysis["action_items"]:
            if action["severity"] == "CRITICAL":
                score += 2.0
            elif action["severity"] == "HIGH":
                score += 1.0
        
        # Normalize to 0-10 scale
        return min(score, 10.0)

    def validate_analysis_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate analysis result completeness and quality.
        
        Args:
            result: Analysis result to validate
            
        Returns:
            Validation report
        """
        issues = []
        
        # Check required fields
        required_fields = [
            "analysis_id", "entities", "classifications", 
            "kubernetes_context", "summary"
        ]
        
        for field in required_fields:
            if field not in result:
                issues.append(f"Missing required field: {field}")
        
        # Check entity quality
        if "entities" in result:
            entity_count = result["entities"].get("entity_count", 0)
            if entity_count == 0:
                issues.append("No entities detected")
        
        # Check classification quality
        if "classifications" in result:
            if len(result["classifications"]) == 0:
                issues.append("No classifications found")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "quality_score": self._calculate_quality_score(result)
        }

    def _calculate_quality_score(self, result: Dict[str, Any]) -> float:
        """Calculate quality score for analysis result."""
        score = 0.0
        
        # Entity quality
        if "entities" in result:
            entity_count = result["entities"].get("entity_count", 0)
            score += min(entity_count * 0.1, 3.0)
        
        # Classification quality
        if "classifications" in result:
            classification_count = len(result["classifications"])
            score += min(classification_count * 0.2, 2.0)
        
        # Kubernetes relevance
        if "summary" in result:
            k8s_score = result["summary"].get("kubernetes_relevance_score", 0)
            score += k8s_score * 3.0
        
        # Action items
        if "action_items" in result:
            action_count = len(result["action_items"])
            score += min(action_count * 0.15, 2.0)
        
        return min(score, 10.0)