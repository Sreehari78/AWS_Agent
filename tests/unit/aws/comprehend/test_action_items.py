"""Unit tests for action item extraction functionality."""

import pytest
from src.eks_upgrade_agent.common.aws.comprehend.custom_classifier import CustomClassifier


@pytest.fixture
def classifier():
    """Create CustomClassifier instance."""
    return CustomClassifier(confidence_threshold=0.7)


class TestActionItems:
    """Test cases for action item extraction methods."""

    def test_extract_action_items(self, classifier):
        """Test extraction of action items from classifications."""
        classifications = [
            {
                "category": "BREAKING_CHANGE",
                "severity": "CRITICAL",
                "confidence": 0.9,
                "match_positions": [(0, 15)]
            },
            {
                "category": "DEPRECATION",
                "severity": "HIGH",
                "confidence": 0.8,
                "match_positions": [(20, 30)]
            }
        ]
        
        text = "Breaking change in deprecated API"
        action_items = classifier.extract_action_items(classifications, text)
        
        assert len(action_items) == 2
        
        # Should be sorted by priority (highest first)
        assert action_items[0]["priority"] >= action_items[1]["priority"]
        
        # Check action content
        critical_action = action_items[0]
        assert critical_action["category"] == "BREAKING_CHANGE"
        assert critical_action["severity"] == "CRITICAL"
        assert "Immediate review" in critical_action["action"]

    def test_determine_action_mapping(self, classifier):
        """Test action determination based on category and severity."""
        # Test various combinations
        assert classifier._determine_action("BREAKING_CHANGE", "CRITICAL") is not None
        assert classifier._determine_action("DEPRECATION", "HIGH") is not None
        assert classifier._determine_action("MIGRATION_REQUIRED", "HIGH") is not None
        assert classifier._determine_action("SECURITY_UPDATE", "CRITICAL") is not None
        assert classifier._determine_action("CONFIGURATION_CHANGE", "MEDIUM") is not None
        
        # Test unknown combination
        assert classifier._determine_action("UNKNOWN", "UNKNOWN") is None

    def test_calculate_priority(self, classifier):
        """Test priority calculation."""
        # Critical severity should have highest priority
        critical_priority = classifier._calculate_priority("CRITICAL", 0.9)
        high_priority = classifier._calculate_priority("HIGH", 0.9)
        medium_priority = classifier._calculate_priority("MEDIUM", 0.9)
        
        assert critical_priority > high_priority > medium_priority
        
        # Higher confidence should increase priority
        high_conf_priority = classifier._calculate_priority("HIGH", 0.9)
        low_conf_priority = classifier._calculate_priority("HIGH", 0.5)
        
        assert high_conf_priority > low_conf_priority

    def test_extract_action_items_with_context(self, classifier):
        """Test action item extraction with context information."""
        classifications = [
            {
                "category": "SECURITY_UPDATE",
                "severity": "CRITICAL",
                "confidence": 0.95,
                "match_positions": [(10, 25), (50, 65)]
            }
        ]
        
        text = "Important security vulnerability CVE-2023-1234 found in security module"
        action_items = classifier.extract_action_items(classifications, text)
        
        assert len(action_items) == 1
        action = action_items[0]
        
        assert action["category"] == "SECURITY_UPDATE"
        assert action["severity"] == "CRITICAL"
        assert len(action["contexts"]) == 2  # Two match positions
        assert action["priority"] > 0.9  # High priority for critical security

    def test_extract_action_items_empty_classifications(self, classifier):
        """Test action item extraction with empty classifications."""
        action_items = classifier.extract_action_items([], "some text")
        
        assert action_items == []

    def test_extract_action_items_no_actions(self, classifier):
        """Test extraction when no actions are determined."""
        classifications = [
            {
                "category": "FEATURE_ADDITION",
                "severity": "INFO",
                "confidence": 0.8,
                "match_positions": [(0, 10)]
            }
        ]
        
        text = "New feature added"
        action_items = classifier.extract_action_items(classifications, text)
        
        # INFO level features typically don't generate actions
        assert len(action_items) == 0

    def test_action_item_priority_sorting(self, classifier):
        """Test that action items are sorted by priority."""
        classifications = [
            {
                "category": "CONFIGURATION_CHANGE",
                "severity": "MEDIUM",
                "confidence": 0.7,
                "match_positions": [(0, 10)]
            },
            {
                "category": "BREAKING_CHANGE",
                "severity": "CRITICAL",
                "confidence": 0.9,
                "match_positions": [(20, 35)]
            },
            {
                "category": "DEPRECATION",
                "severity": "HIGH",
                "confidence": 0.8,
                "match_positions": [(40, 50)]
            }
        ]
        
        text = "Config change, breaking change, and deprecation"
        action_items = classifier.extract_action_items(classifications, text)
        
        # Should be sorted by priority (highest first)
        priorities = [item["priority"] for item in action_items]
        assert priorities == sorted(priorities, reverse=True)
        
        # Critical breaking change should be first
        assert action_items[0]["category"] == "BREAKING_CHANGE"