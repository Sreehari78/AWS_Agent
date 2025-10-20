"""Unit tests for Comprehend patterns and configurations."""

import pytest
from src.eks_upgrade_agent.common.aws.comprehend.patterns import (
    ClassificationCategory,
    SeverityLevel,
    KubernetesPatterns,
    ClassificationPatterns,
    KubernetesComponents
)


class TestClassificationCategory:
    """Test cases for ClassificationCategory enum."""

    def test_category_values(self):
        """Test classification category values."""
        assert ClassificationCategory.BREAKING_CHANGE.value == "BREAKING_CHANGE"
        assert ClassificationCategory.DEPRECATION.value == "DEPRECATION"
        assert ClassificationCategory.MIGRATION_REQUIRED.value == "MIGRATION_REQUIRED"
        assert ClassificationCategory.SECURITY_UPDATE.value == "SECURITY_UPDATE"

    def test_all_categories_defined(self):
        """Test that all expected categories are defined."""
        expected_categories = [
            "BREAKING_CHANGE", "DEPRECATION", "MIGRATION_REQUIRED",
            "SECURITY_UPDATE", "FEATURE_ADDITION", "BUG_FIX",
            "PERFORMANCE_IMPROVEMENT", "CONFIGURATION_CHANGE", "UNKNOWN"
        ]
        
        actual_categories = [cat.value for cat in ClassificationCategory]
        
        for expected in expected_categories:
            assert expected in actual_categories


class TestSeverityLevel:
    """Test cases for SeverityLevel enum."""

    def test_severity_values(self):
        """Test severity level values."""
        assert SeverityLevel.CRITICAL.value == "CRITICAL"
        assert SeverityLevel.HIGH.value == "HIGH"
        assert SeverityLevel.MEDIUM.value == "MEDIUM"
        assert SeverityLevel.LOW.value == "LOW"
        assert SeverityLevel.INFO.value == "INFO"


class TestKubernetesPatterns:
    """Test cases for KubernetesPatterns."""

    def test_entity_patterns_structure(self):
        """Test entity patterns structure."""
        patterns = KubernetesPatterns()
        
        assert "API_VERSION" in patterns.ENTITY_PATTERNS
        assert "RESOURCE_KIND" in patterns.ENTITY_PATTERNS
        assert "BREAKING_CHANGE_INDICATORS" in patterns.ENTITY_PATTERNS
        assert "VERSION_NUMBER" in patterns.ENTITY_PATTERNS
        assert "EKS_COMPONENT" in patterns.ENTITY_PATTERNS

    def test_confidence_thresholds_structure(self):
        """Test confidence thresholds structure."""
        patterns = KubernetesPatterns()
        
        assert "API_VERSION" in patterns.CONFIDENCE_THRESHOLDS
        assert "RESOURCE_KIND" in patterns.CONFIDENCE_THRESHOLDS
        assert patterns.CONFIDENCE_THRESHOLDS["API_VERSION"] == 0.9
        assert patterns.CONFIDENCE_THRESHOLDS["RESOURCE_KIND"] == 0.8

    def test_pattern_types(self):
        """Test that patterns are lists of strings."""
        patterns = KubernetesPatterns()
        
        for pattern_type, pattern_list in patterns.ENTITY_PATTERNS.items():
            assert isinstance(pattern_list, list)
            for pattern in pattern_list:
                assert isinstance(pattern, str)


class TestClassificationPatterns:
    """Test cases for ClassificationPatterns."""

    def test_patterns_structure(self):
        """Test classification patterns structure."""
        patterns = ClassificationPatterns()
        
        assert ClassificationCategory.BREAKING_CHANGE in patterns.PATTERNS
        assert ClassificationCategory.DEPRECATION in patterns.PATTERNS
        assert ClassificationCategory.MIGRATION_REQUIRED in patterns.PATTERNS

    def test_pattern_config_structure(self):
        """Test pattern configuration structure."""
        patterns = ClassificationPatterns()
        
        for category, config in patterns.PATTERNS.items():
            assert "patterns" in config
            assert "severity" in config
            assert "keywords" in config
            assert isinstance(config["patterns"], list)
            assert isinstance(config["keywords"], list)
            assert isinstance(config["severity"], SeverityLevel)

    def test_severity_assignments(self):
        """Test severity level assignments."""
        patterns = ClassificationPatterns()
        
        breaking_config = patterns.PATTERNS[ClassificationCategory.BREAKING_CHANGE]
        assert breaking_config["severity"] == SeverityLevel.CRITICAL
        
        deprecation_config = patterns.PATTERNS[ClassificationCategory.DEPRECATION]
        assert deprecation_config["severity"] == SeverityLevel.HIGH


class TestKubernetesComponents:
    """Test cases for KubernetesComponents."""

    def test_components_structure(self):
        """Test components structure."""
        components = KubernetesComponents()
        
        assert "API_OBJECTS" in components.COMPONENTS
        assert "API_GROUPS" in components.COMPONENTS
        assert "EKS_ADDONS" in components.COMPONENTS

    def test_api_objects_content(self):
        """Test API objects content."""
        components = KubernetesComponents()
        api_objects = components.COMPONENTS["API_OBJECTS"]
        
        expected_objects = ["Deployment", "Service", "Pod", "ConfigMap", "Secret"]
        for obj in expected_objects:
            assert obj in api_objects

    def test_eks_addons_content(self):
        """Test EKS addons content."""
        components = KubernetesComponents()
        eks_addons = components.COMPONENTS["EKS_ADDONS"]
        
        expected_addons = ["vpc-cni", "coredns", "kube-proxy"]
        for addon in expected_addons:
            assert addon in eks_addons

    def test_component_types(self):
        """Test that components are lists of strings."""
        components = KubernetesComponents()
        
        for component_type, component_list in components.COMPONENTS.items():
            assert isinstance(component_list, list)
            for component in component_list:
                assert isinstance(component, str)