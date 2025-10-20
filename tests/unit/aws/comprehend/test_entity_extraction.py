"""Unit tests for entity extraction functionality."""

import pytest
from src.eks_upgrade_agent.common.aws.comprehend.entity_extractor import EntityExtractor
from src.eks_upgrade_agent.common.models.aws_ai import ComprehendEntity


@pytest.fixture
def extractor():
    """Create EntityExtractor instance."""
    return EntityExtractor(min_confidence=0.5)


class TestEntityExtraction:
    """Test cases for entity extraction methods."""

    def test_extract_api_versions(self, extractor):
        """Test extraction of API versions."""
        text = "The apps/v1 Deployment and extensions/v1beta1 Ingress are affected"
        entities = extractor.extract_kubernetes_entities(text)
        
        api_entities = [e for e in entities if e.type == "API_VERSION"]
        assert len(api_entities) >= 2
        
        api_texts = [e.text for e in api_entities]
        assert "apps/v1" in api_texts
        assert "extensions/v1beta1" in api_texts

    def test_extract_resource_kinds(self, extractor):
        """Test extraction of Kubernetes resource kinds."""
        text = "Update your Deployment, Service, and ConfigMap resources"
        entities = extractor.extract_kubernetes_entities(text)
        
        resource_entities = [e for e in entities if e.type == "RESOURCE_KIND"]
        assert len(resource_entities) >= 3
        
        resource_texts = [e.text for e in resource_entities]
        assert "Deployment" in resource_texts
        assert "Service" in resource_texts
        assert "ConfigMap" in resource_texts

    def test_extract_version_numbers(self, extractor):
        """Test extraction of version numbers."""
        text = "Upgrade from 1.27.0 to 1.28.5 or 1.29.0-alpha.1"
        entities = extractor.extract_kubernetes_entities(text)
        
        version_entities = [e for e in entities if e.type == "VERSION_NUMBER"]
        assert len(version_entities) >= 3
        
        version_texts = [e.text for e in version_entities]
        assert "1.27.0" in version_texts
        assert "1.28.5" in version_texts
        assert "1.29.0-alpha.1" in version_texts

    def test_extract_eks_components(self, extractor):
        """Test extraction of EKS components."""
        text = "Update kube-proxy, coredns, and vpc-cni to latest versions"
        entities = extractor.extract_kubernetes_entities(text)
        
        component_entities = [e for e in entities if e.type == "EKS_COMPONENT"]
        assert len(component_entities) >= 3
        
        component_texts = [e.text for e in component_entities]
        assert "kube-proxy" in component_texts
        assert "coredns" in component_texts
        assert "vpc-cni" in component_texts

    def test_extract_breaking_change_indicators(self, extractor):
        """Test extraction of breaking change indicators."""
        text = "This is a BREAKING change. The API is deprecated and will be removed."
        entities = extractor.extract_kubernetes_entities(text)
        
        breaking_entities = [e for e in entities if e.type == "BREAKING_CHANGE_INDICATORS"]
        assert len(breaking_entities) >= 1
        
        breaking_texts = [e.text.lower() for e in breaking_entities]
        assert any("breaking" in text for text in breaking_texts)

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