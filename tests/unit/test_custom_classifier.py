"""Unit tests for CustomClassifier."""

import pytest
from src.eks_upgrade_agent.common.aws.comprehend.custom_classifier import CustomClassifier
from src.eks_upgrade_agent.common.aws.comprehend.patterns import ClassificationCategory, SeverityLevel


class TestCustomClassifier:
    """Test cases for CustomClassifier."""

    @pytest.fixture
    def classifier(self):
        """Create CustomClassifier instance."""
        return CustomClassifier(confidence_threshold=0.7)

    def test_initialization(self, classifier):
        """Test CustomClassifier initialization."""
        assert classifier.confidence_threshold == 0.7
        assert hasattr(classifier, 'classification_patterns')
        assert hasattr(classifier, 'k8s_components')
        assert hasattr(classifier.classification_patterns, 'PATTERNS')
        assert hasattr(classifier.k8s_components, 'COMPONENTS')

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

    def test_analyze_kubernetes_context_api_objects(self, classifier):
        """Test Kubernetes context analysis for API objects."""
        text = "Update your Deployment, Service, and ConfigMap resources"
        context = classifier.analyze_kubernetes_context(text)
        
        assert "Deployment" in context["api_objects"]
        assert "Service" in context["api_objects"]
        assert "ConfigMap" in context["api_objects"]
        assert context["kubernetes_score"] > 0

    def test_analyze_kubernetes_context_api_groups(self, classifier):
        """Test Kubernetes context analysis for API groups."""
        text = "The apps/v1 and networking.k8s.io APIs are affected"
        context = classifier.analyze_kubernetes_context(text)
        
        assert "apps" in context["api_groups"]
        assert "networking.k8s.io" in context["api_groups"]

    def test_analyze_kubernetes_context_eks_addons(self, classifier):
        """Test Kubernetes context analysis for EKS addons."""
        text = "Update vpc-cni, coredns, and kube-proxy to the latest versions"
        context = classifier.analyze_kubernetes_context(text)
        
        assert "vpc-cni" in context["eks_addons"]
        assert "coredns" in context["eks_addons"]
        assert "kube-proxy" in context["eks_addons"]

    def test_analyze_kubernetes_context_versions(self, classifier):
        """Test Kubernetes context analysis for version references."""
        text = "Upgrade from v1.27.0 to 1.28.5 or use 1.29.0-alpha.1"
        context = classifier.analyze_kubernetes_context(text)
        
        versions = context["version_references"]
        assert any("1.27.0" in v for v in versions)
        assert any("1.28.5" in v for v in versions)
        assert any("1.29.0-alpha.1" in v for v in versions)

    def test_analyze_kubernetes_context_score_calculation(self, classifier):
        """Test Kubernetes relevance score calculation."""
        # High relevance text
        high_relevance_text = "Kubernetes cluster with Deployment, Service, and vpc-cni addon"
        high_context = classifier.analyze_kubernetes_context(high_relevance_text)
        
        # Low relevance text
        low_relevance_text = "This is just regular text without any special terms"
        low_context = classifier.analyze_kubernetes_context(low_relevance_text)
        
        assert high_context["kubernetes_score"] > low_context["kubernetes_score"]
        assert high_context["kubernetes_score"] > 0.3
        assert low_context["kubernetes_score"] < 0.1

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

    def test_validate_classification_results_success(self, classifier):
        """Test successful validation of classification results."""
        results = [
            {
                "category": "BREAKING_CHANGE",
                "severity": "CRITICAL",
                "confidence": 0.9
            },
            {
                "category": "DEPRECATION",
                "severity": "HIGH",
                "confidence": 0.8
            }
        ]
        
        validation = classifier.validate_classification_results(results)
        
        assert validation["valid"] is True
        assert validation["result_count"] == 2
        assert abs(validation["avg_confidence"] - 0.85) < 0.001  # Handle floating point precision
        assert len(validation["issues"]) == 0

    def test_validate_classification_results_empty(self, classifier):
        """Test validation with empty results."""
        validation = classifier.validate_classification_results([])
        
        assert validation["valid"] is True
        assert validation["result_count"] == 0
        assert validation["avg_confidence"] == 0.0

    def test_validate_classification_results_low_confidence(self, classifier):
        """Test validation with low confidence results."""
        results = [
            {
                "category": "BREAKING_CHANGE",
                "severity": "CRITICAL",
                "confidence": 0.5  # Below threshold of 0.7
            }
        ]
        
        validation = classifier.validate_classification_results(results)
        
        assert validation["valid"] is False
        assert len(validation["issues"]) > 0
        assert "below confidence threshold" in validation["issues"][0]

    def test_severity_distribution(self, classifier):
        """Test severity distribution calculation."""
        results = [
            {"category": "BREAKING_CHANGE", "severity": "CRITICAL", "confidence": 0.9},
            {"category": "DEPRECATION", "severity": "HIGH", "confidence": 0.8},
            {"category": "FEATURE_ADDITION", "severity": "INFO", "confidence": 0.7}
        ]
        
        validation = classifier.validate_classification_results(results)
        
        severity_dist = validation["severity_distribution"]
        assert severity_dist["CRITICAL"] == 1
        assert severity_dist["HIGH"] == 1
        assert severity_dist["INFO"] == 1

    def test_category_distribution(self, classifier):
        """Test category distribution calculation."""
        results = [
            {"category": "BREAKING_CHANGE", "severity": "CRITICAL", "confidence": 0.9},
            {"category": "BREAKING_CHANGE", "severity": "HIGH", "confidence": 0.8},
            {"category": "DEPRECATION", "severity": "HIGH", "confidence": 0.7}
        ]
        
        validation = classifier.validate_classification_results(results)
        
        category_dist = validation["category_distribution"]
        assert category_dist["BREAKING_CHANGE"] == 2
        assert category_dist["DEPRECATION"] == 1

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