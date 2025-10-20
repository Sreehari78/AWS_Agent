"""Unit tests for text classification functionality."""

import pytest
from src.eks_upgrade_agent.common.aws.comprehend.custom_classifier import CustomClassifier
from src.eks_upgrade_agent.common.aws.comprehend.patterns import ClassificationCategory, SeverityLevel


@pytest.fixture
def classifier():
    """Create CustomClassifier instance."""
    return CustomClassifier(confidence_threshold=0.7)


class TestTextClassification:
    """Test cases for text classification methods."""

    def test_classify_breaking_change(self, classifier):
        """Test classification of breaking changes."""
        text = "This is a breaking change that will affect your applications"
        results = classifier.classify_text(text)
        
        breaking_results = [r for r in results if r["category"] == "BREAKING_CHANGE"]
        assert len(breaking_results) > 0
        
        result = breaking_results[0]
        assert result["severity"] == "CRITICAL"
        assert result["confidence"] >= 0.7
        assert "breaking change" in result["matches"]

    def test_classify_deprecation(self, classifier):
        """Test classification of deprecations."""
        text = "The v1beta1 API is deprecated and will be removed in the next version"
        results = classifier.classify_text(text)
        
        deprecation_results = [r for r in results if r["category"] == "DEPRECATION"]
        assert len(deprecation_results) > 0
        
        result = deprecation_results[0]
        assert result["severity"] == "HIGH"
        assert result["confidence"] >= 0.7
        assert "deprecated" in result["keyword_matches"]

    def test_classify_migration_required(self, classifier):
        """Test classification of migration requirements."""
        text = "Migration required: update your manifests to use the new API version"
        results = classifier.classify_text(text)
        
        migration_results = [r for r in results if r["category"] == "MIGRATION_REQUIRED"]
        assert len(migration_results) > 0
        
        result = migration_results[0]
        assert result["severity"] == "HIGH"
        assert result["confidence"] >= 0.7

    def test_classify_security_update(self, classifier):
        """Test classification of security updates."""
        text = "Security vulnerability CVE-2023-1234 fixed in this release"
        results = classifier.classify_text(text)
        
        security_results = [r for r in results if r["category"] == "SECURITY_UPDATE"]
        assert len(security_results) > 0
        
        result = security_results[0]
        assert result["severity"] == "CRITICAL"
        assert result["confidence"] >= 0.7

    def test_classify_configuration_change(self, classifier):
        """Test classification of configuration changes."""
        text = "Default configuration values have changed for the cluster autoscaler"
        results = classifier.classify_text(text)
        
        config_results = [r for r in results if r["category"] == "CONFIGURATION_CHANGE"]
        assert len(config_results) > 0
        
        result = config_results[0]
        assert result["severity"] == "MEDIUM"
        assert "configuration" in result["keyword_matches"]

    def test_classify_feature_addition(self, classifier):
        """Test classification of feature additions."""
        text = "New feature added: support for custom resource definitions"
        results = classifier.classify_text(text)
        
        feature_results = [r for r in results if r["category"] == "FEATURE_ADDITION"]
        assert len(feature_results) > 0
        
        result = feature_results[0]
        assert result["severity"] == "INFO"

    def test_classify_multiple_categories(self, classifier):
        """Test classification with multiple categories in one text."""
        text = """
        Breaking change: The v1beta1 API is deprecated and removed.
        Security fix for CVE-2023-1234.
        New feature: enhanced monitoring capabilities.
        """
        results = classifier.classify_text(text)
        
        categories = [r["category"] for r in results]
        assert "BREAKING_CHANGE" in categories
        assert "DEPRECATION" in categories
        assert "SECURITY_UPDATE" in categories
        assert "FEATURE_ADDITION" in categories

    def test_confidence_threshold_filtering(self, classifier):
        """Test that results below confidence threshold are filtered out."""
        text = "minor change in configuration"  # Should have low confidence
        results = classifier.classify_text(text)
        
        # All results should meet the confidence threshold
        for result in results:
            assert result["confidence"] >= classifier.confidence_threshold

    def test_case_insensitive_matching(self, classifier):
        """Test case-insensitive pattern matching."""
        text1 = "BREAKING CHANGE in the API"
        text2 = "breaking change in the API"
        
        results1 = classifier.classify_text(text1)
        results2 = classifier.classify_text(text2)
        
        # Both should detect breaking changes
        breaking1 = [r for r in results1 if r["category"] == "BREAKING_CHANGE"]
        breaking2 = [r for r in results2 if r["category"] == "BREAKING_CHANGE"]
        
        assert len(breaking1) > 0
        assert len(breaking2) > 0