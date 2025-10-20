"""Unit tests for EntityExtractor."""

import pytest
from src.eks_upgrade_agent.common.aws.comprehend.entity_extractor import EntityExtractor
from src.eks_upgrade_agent.common.models.aws_ai import ComprehendEntity


class TestEntityExtractor:
    """Test cases for EntityExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create EntityExtractor instance."""
        return EntityExtractor(min_confidence=0.5)

    def test_initialization(self, extractor):
        """Test EntityExtractor initialization."""
        assert extractor.min_confidence == 0.5
        assert hasattr(extractor, 'patterns')
        assert hasattr(extractor.patterns, 'ENTITY_PATTERNS')
        assert hasattr(extractor.patterns, 'CONFIDENCE_THRESHOLDS')

    def test_extract_kubernetes_entities_api_versions(self, extractor):
        """Test extraction of API versions."""
        text = "The apps/v1 Deployment and extensions/v1beta1 Ingress are affected"
        entities = extractor.extract_kubernetes_entities(text)
        
        api_entities = [e for e in entities if e.type == "API_VERSION"]
        assert len(api_entities) >= 2
        
        api_texts = [e.text for e in api_entities]
        assert "apps/v1" in api_texts
        assert "extensions/v1beta1" in api_texts

    def test_extract_kubernetes_entities_resource_kinds(self, extractor):
        """Test extraction of Kubernetes resource kinds."""
        text = "Update your Deployment, Service, and ConfigMap resources"
        entities = extractor.extract_kubernetes_entities(text)
        
        resource_entities = [e for e in entities if e.type == "RESOURCE_KIND"]
        assert len(resource_entities) >= 3
        
        resource_texts = [e.text for e in resource_entities]
        assert "Deployment" in resource_texts
        assert "Service" in resource_texts
        assert "ConfigMap" in resource_texts

    def test_extract_kubernetes_entities_breaking_changes(self, extractor):
        """Test extraction of breaking change indicators."""
        text = "This is a BREAKING change. The API is deprecated and will be removed."
        entities = extractor.extract_kubernetes_entities(text)
        
        breaking_entities = [e for e in entities if e.type == "BREAKING_CHANGE_INDICATORS"]
        assert len(breaking_entities) >= 1
        
        breaking_texts = [e.text.lower() for e in breaking_entities]
        assert any("breaking" in text for text in breaking_texts)

    def test_extract_kubernetes_entities_version_numbers(self, extractor):
        """Test extraction of version numbers."""
        text = "Upgrade from 1.27.0 to 1.28.5 or 1.29.0-alpha.1"
        entities = extractor.extract_kubernetes_entities(text)
        
        version_entities = [e for e in entities if e.type == "VERSION_NUMBER"]
        assert len(version_entities) >= 3
        
        version_texts = [e.text for e in version_entities]
        assert "1.27.0" in version_texts
        assert "1.28.5" in version_texts
        assert "1.29.0-alpha.1" in version_texts

    def test_extract_kubernetes_entities_eks_components(self, extractor):
        """Test extraction of EKS components."""
        text = "Update kube-proxy, coredns, and vpc-cni to latest versions"
        entities = extractor.extract_kubernetes_entities(text)
        
        component_entities = [e for e in entities if e.type == "EKS_COMPONENT"]
        assert len(component_entities) >= 3
        
        component_texts = [e.text for e in component_entities]
        assert "kube-proxy" in component_texts
        assert "coredns" in component_texts
        assert "vpc-cni" in component_texts

    def test_filter_entities_by_confidence(self, extractor):
        """Test filtering entities by confidence threshold."""
        entities = [
            ComprehendEntity(text="high", type="TEST", confidence=0.9, begin_offset=0, end_offset=4),
            ComprehendEntity(text="medium", type="TEST", confidence=0.6, begin_offset=5, end_offset=11),
            ComprehendEntity(text="low", type="TEST", confidence=0.3, begin_offset=12, end_offset=15)
        ]
        
        # Filter with default threshold (0.5)
        filtered = extractor.filter_entities_by_confidence(entities)
        assert len(filtered) == 2
        assert all(e.confidence >= 0.5 for e in filtered)
        
        # Filter with higher threshold
        filtered_high = extractor.filter_entities_by_confidence(entities, min_confidence=0.8)
        assert len(filtered_high) == 1
        assert filtered_high[0].text == "high"

    def test_group_entities_by_type(self, extractor):
        """Test grouping entities by type."""
        entities = [
            ComprehendEntity(text="v1", type="API_VERSION", confidence=0.9, begin_offset=0, end_offset=2),
            ComprehendEntity(text="v2", type="API_VERSION", confidence=0.8, begin_offset=3, end_offset=5),
            ComprehendEntity(text="Pod", type="RESOURCE_KIND", confidence=0.9, begin_offset=6, end_offset=9)
        ]
        
        grouped = extractor.group_entities_by_type(entities)
        
        assert len(grouped) == 2
        assert "API_VERSION" in grouped
        assert "RESOURCE_KIND" in grouped
        assert len(grouped["API_VERSION"]) == 2
        assert len(grouped["RESOURCE_KIND"]) == 1

    def test_extract_breaking_changes(self, extractor):
        """Test extraction of breaking change information."""
        text = "This is a breaking change that affects the v1beta1 API. Users must migrate their resources."
        entities = [
            ComprehendEntity(
                text="breaking change", 
                type="BREAKING_CHANGE_INDICATORS", 
                confidence=0.9, 
                begin_offset=10, 
                end_offset=25
            )
        ]
        
        breaking_changes = extractor.extract_breaking_changes(entities, text)
        
        assert len(breaking_changes) == 1
        assert breaking_changes[0]["indicator"] == "breaking change"
        assert breaking_changes[0]["confidence"] == 0.9
        assert "context" in breaking_changes[0]
        assert "position" in breaking_changes[0]

    def test_extract_api_deprecations(self, extractor):
        """Test extraction of API deprecation information."""
        text = "The extensions/v1beta1 Ingress API is deprecated in v1.22 and will be removed in v1.25."
        
        entities = [
            ComprehendEntity(text="extensions/v1beta1", type="API_VERSION", confidence=0.9, begin_offset=4, end_offset=22),
            ComprehendEntity(text="Ingress", type="RESOURCE_KIND", confidence=0.9, begin_offset=23, end_offset=30),
            ComprehendEntity(text="deprecated", type="BREAKING_CHANGE_INDICATORS", confidence=0.8, begin_offset=38, end_offset=48)
        ]
        
        deprecations = extractor.extract_api_deprecations(entities, text)
        
        assert len(deprecations) == 1
        assert deprecations[0]["indicator"] == "deprecated"
        assert "extensions/v1beta1" in deprecations[0]["api_versions"]
        assert "Ingress" in deprecations[0]["resource_kinds"]

    def test_validate_entities_success(self, extractor):
        """Test successful entity validation."""
        entities = [
            ComprehendEntity(text="test1", type="TEST", confidence=0.9, begin_offset=0, end_offset=5),
            ComprehendEntity(text="test2", type="TEST", confidence=0.8, begin_offset=6, end_offset=11)
        ]
        
        validation = extractor.validate_entities(entities)
        
        assert validation["valid"] is True
        assert validation["entity_count"] == 2
        assert abs(validation["avg_confidence"] - 0.85) < 0.001  # Handle floating point precision
        assert len(validation["issues"]) == 0

    def test_validate_entities_empty_list(self, extractor):
        """Test validation with empty entity list."""
        validation = extractor.validate_entities([])
        
        assert validation["valid"] is True
        assert validation["entity_count"] == 0
        assert validation["avg_confidence"] == 0.0

    def test_validate_entities_overlapping(self, extractor):
        """Test validation with overlapping entities."""
        entities = [
            ComprehendEntity(text="test", type="TEST", confidence=0.9, begin_offset=0, end_offset=5),
            ComprehendEntity(text="est", type="TEST", confidence=0.8, begin_offset=1, end_offset=4)  # Overlaps
        ]
        
        validation = extractor.validate_entities(entities)
        
        assert validation["valid"] is False
        assert len(validation["issues"]) > 0
        assert "Overlapping entities" in validation["issues"][0]

    def test_confidence_distribution(self, extractor):
        """Test confidence distribution calculation."""
        entities = [
            ComprehendEntity(text="high1", type="TEST", confidence=0.9, begin_offset=0, end_offset=5),
            ComprehendEntity(text="high2", type="TEST", confidence=0.85, begin_offset=6, end_offset=11),
            ComprehendEntity(text="medium", type="TEST", confidence=0.6, begin_offset=12, end_offset=18),
            ComprehendEntity(text="low", type="TEST", confidence=0.3, begin_offset=19, end_offset=22)
        ]
        
        validation = extractor.validate_entities(entities)
        
        distribution = validation["confidence_distribution"]
        assert distribution["high (>0.8)"] == 2
        assert distribution["medium (0.5-0.8)"] == 1
        assert distribution["low (<0.5)"] == 1

    def test_empty_text_handling(self, extractor):
        """Test handling of empty or whitespace text."""
        assert extractor.extract_kubernetes_entities("") == []
        assert extractor.extract_kubernetes_entities("   ") == []
        assert extractor.extract_kubernetes_entities("\n\t") == []

    def test_case_insensitive_matching(self, extractor):
        """Test case-insensitive pattern matching."""
        text = "DEPLOYMENT and deployment both match"
        entities = extractor.extract_kubernetes_entities(text)
        
        resource_entities = [e for e in entities if e.type == "RESOURCE_KIND"]
        resource_texts = [e.text for e in resource_entities]
        
        assert "DEPLOYMENT" in resource_texts
        assert "deployment" in resource_texts