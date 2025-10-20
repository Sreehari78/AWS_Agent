"""Custom classification models for Kubernetes terminology."""

from typing import Dict, List, Optional
import re

from ...models.aws_ai import ComprehendEntity
from ...logging import get_logger
from .patterns import ClassificationPatterns, KubernetesComponents

logger = get_logger(__name__)


class CustomClassifier:
    """Custom classifier for Kubernetes and EKS terminology."""

    def __init__(self, confidence_threshold: float = 0.7):
        """
        Initialize custom classifier.
        
        Args:
            confidence_threshold: Minimum confidence for classification results
        """
        self.confidence_threshold = confidence_threshold
        self.classification_patterns = ClassificationPatterns()
        self.k8s_components = KubernetesComponents()
        logger.info("Initialized CustomClassifier", confidence_threshold=confidence_threshold)

    def classify_text(self, text: str) -> List[Dict[str, any]]:
        """
        Classify text into Kubernetes-specific categories.
        
        Args:
            text: Text to classify
            
        Returns:
            List of classification results
        """
        results = []
        text_lower = text.lower()
        
        for category, config in self.classification_patterns.PATTERNS.items():
            matches = []
            confidence_scores = []
            
            # Pattern matching
            for pattern in config["patterns"]:
                pattern_matches = list(re.finditer(pattern, text, re.IGNORECASE))
                matches.extend(pattern_matches)
            
            # Keyword scoring
            keyword_score = 0
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    keyword_score += 1
            
            if matches or keyword_score > 0:
                # Calculate confidence based on matches and keyword presence
                pattern_confidence = min(len(matches) * 0.4, 1.0)
                keyword_confidence = min(keyword_score * 0.3, 0.7)
                total_confidence = min(pattern_confidence + keyword_confidence, 1.0)
                
                if total_confidence >= self.confidence_threshold:
                    result = {
                        "category": category.value,
                        "severity": config["severity"].value,
                        "confidence": total_confidence,
                        "matches": [m.group() for m in matches],
                        "match_positions": [(m.start(), m.end()) for m in matches],
                        "keyword_matches": [kw for kw in config["keywords"] if kw in text_lower]
                    }
                    results.append(result)
        
        logger.debug(
            "Classified text",
            text_length=len(text),
            classification_count=len(results)
        )
        
        return results

    def analyze_kubernetes_context(self, text: str) -> Dict[str, any]:
        """
        Analyze text for Kubernetes-specific context and components.
        
        Args:
            text: Text to analyze
            
        Returns:
            Analysis results with component detection
        """
        context = {
            "api_objects": [],
            "api_groups": [],
            "eks_addons": [],
            "version_references": [],
            "kubernetes_score": 0.0
        }
        
        text_lower = text.lower()
        
        # Detect API objects
        for obj in self.k8s_components.COMPONENTS["API_OBJECTS"]:
            if obj.lower() in text_lower:
                context["api_objects"].append(obj)
        
        # Detect API groups
        for group in self.k8s_components.COMPONENTS["API_GROUPS"]:
            if group in text_lower:
                context["api_groups"].append(group)
        
        # Detect EKS addons
        for addon in self.k8s_components.COMPONENTS["EKS_ADDONS"]:
            if addon in text_lower:
                context["eks_addons"].append(addon)
        
        # Detect version references
        version_pattern = r"\bv?\d+\.\d+(?:\.\d+)?(?:-\w+(?:\.\d+)?)?\b"
        versions = re.findall(version_pattern, text)
        context["version_references"] = list(set(versions))
        
        # Calculate Kubernetes relevance score
        total_components = (
            len(context["api_objects"]) +
            len(context["api_groups"]) +
            len(context["eks_addons"]) +
            len(context["version_references"])
        )
        
        # Additional scoring for Kubernetes keywords
        k8s_keywords = ["kubernetes", "k8s", "kubectl", "helm", "eks", "cluster"]
        keyword_matches = sum(1 for kw in k8s_keywords if kw in text_lower)
        
        context["kubernetes_score"] = min((total_components + keyword_matches) * 0.1, 1.0)
        
        logger.debug(
            "Analyzed Kubernetes context",
            kubernetes_score=context["kubernetes_score"],
            total_components=total_components
        )
        
        return context

    def extract_action_items(self, classifications: List[Dict[str, any]], text: str) -> List[Dict[str, any]]:
        """
        Extract actionable items from classification results.
        
        Args:
            classifications: Classification results
            text: Original text
            
        Returns:
            List of action items with priorities
        """
        action_items = []
        
        for classification in classifications:
            category = classification["category"]
            severity = classification["severity"]
            
            # Determine action based on category and severity
            action = self._determine_action(category, severity)
            
            if action:
                # Extract context around matches
                contexts = []
                for start, end in classification["match_positions"]:
                    context_start = max(0, start - 50)
                    context_end = min(len(text), end + 50)
                    context = text[context_start:context_end].strip()
                    contexts.append(context)
                
                action_item = {
                    "action": action,
                    "category": category,
                    "severity": severity,
                    "confidence": classification["confidence"],
                    "contexts": contexts,
                    "priority": self._calculate_priority(severity, classification["confidence"])
                }
                action_items.append(action_item)
        
        # Sort by priority (highest first)
        action_items.sort(key=lambda x: x["priority"], reverse=True)
        
        logger.info(
            "Extracted action items",
            action_item_count=len(action_items)
        )
        
        return action_items

    def _determine_action(self, category: str, severity: str) -> Optional[str]:
        """Determine appropriate action based on category and severity."""
        action_map = {
            ("BREAKING_CHANGE", "CRITICAL"): "Immediate review and testing required before upgrade",
            ("BREAKING_CHANGE", "HIGH"): "Review breaking changes and plan migration",
            ("DEPRECATION", "HIGH"): "Plan migration from deprecated APIs",
            ("DEPRECATION", "MEDIUM"): "Schedule migration from deprecated APIs",
            ("MIGRATION_REQUIRED", "HIGH"): "Execute required migration steps",
            ("MIGRATION_REQUIRED", "MEDIUM"): "Plan and schedule migration",
            ("SECURITY_UPDATE", "CRITICAL"): "Apply security updates immediately",
            ("SECURITY_UPDATE", "HIGH"): "Schedule security updates",
            ("CONFIGURATION_CHANGE", "MEDIUM"): "Review and update configuration",
            ("CONFIGURATION_CHANGE", "LOW"): "Consider configuration updates"
        }
        
        return action_map.get((category, severity))

    def _calculate_priority(self, severity: str, confidence: float) -> float:
        """Calculate priority score based on severity and confidence."""
        severity_weights = {
            "CRITICAL": 1.0,
            "HIGH": 0.8,
            "MEDIUM": 0.6,
            "LOW": 0.4,
            "INFO": 0.2
        }
        
        severity_weight = severity_weights.get(severity, 0.5)
        return severity_weight * confidence

    def validate_classification_results(self, results: List[Dict[str, any]]) -> Dict[str, any]:
        """
        Validate classification results and provide quality metrics.
        
        Args:
            results: Classification results to validate
            
        Returns:
            Validation results and quality metrics
        """
        if not results:
            return {
                "valid": True,
                "result_count": 0,
                "avg_confidence": 0.0,
                "severity_distribution": {},
                "category_distribution": {},
                "issues": []
            }
        
        issues = []
        confidences = [r["confidence"] for r in results]
        avg_confidence = sum(confidences) / len(confidences)
        
        # Check for low confidence results
        low_confidence_count = len([c for c in confidences if c < self.confidence_threshold])
        if low_confidence_count > 0:
            issues.append(f"{low_confidence_count} results below confidence threshold")
        
        # Distribution analysis
        severity_dist = {}
        category_dist = {}
        
        for result in results:
            severity = result["severity"]
            category = result["category"]
            
            severity_dist[severity] = severity_dist.get(severity, 0) + 1
            category_dist[category] = category_dist.get(category, 0) + 1
        
        validation_result = {
            "valid": len(issues) == 0,
            "result_count": len(results),
            "avg_confidence": avg_confidence,
            "severity_distribution": severity_dist,
            "category_distribution": category_dist,
            "issues": issues
        }
        
        logger.debug("Validated classification results", **validation_result)
        
        return validation_result