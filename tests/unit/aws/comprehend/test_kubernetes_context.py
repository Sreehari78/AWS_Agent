"""Unit tests for Kubernetes context analysis."""

import pytest
from src.eks_upgrade_agent.common.aws.comprehend.custom_classifier import CustomClassifier


@pytest.fixture
def classifier():
    """Create CustomClassifier instance."""
    return CustomClassifier(confidence_threshold=0.7)


class TestKubernetesContext:
    """Test cases for Kubernetes context analysis methods."""

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

    def test_analyze_kubernetes_context_empty_text(self, classifier):
        """Test Kubernetes context analysis with empty text."""
        context = classifier.analyze_kubernetes_context("")
        
        assert context["api_objects"] == []
        assert context["api_groups"] == []
        assert context["eks_addons"] == []
        assert context["version_references"] == []
        assert context["kubernetes_score"] == 0.0

    def test_analyze_kubernetes_context_mixed_content(self, classifier):
        """Test analysis with mixed Kubernetes and non-Kubernetes content."""
        text = """
        This document describes the Kubernetes v1.28 upgrade process.
        The Deployment and Service resources need to be updated.
        Also, make sure to update vpc-cni and coredns addons.
        Some random text about other topics that are not related.
        """
        
        context = classifier.analyze_kubernetes_context(text)
        
        # Should detect Kubernetes components
        assert "Deployment" in context["api_objects"]
        assert "Service" in context["api_objects"]
        assert "vpc-cni" in context["eks_addons"]
        assert "coredns" in context["eks_addons"]
        
        # Should have reasonable Kubernetes score
        assert 0.3 <= context["kubernetes_score"] <= 1.0

    def test_analyze_kubernetes_context_case_insensitive(self, classifier):
        """Test case-insensitive detection of Kubernetes components."""
        text = "deployment and DEPLOYMENT both should be detected"
        context = classifier.analyze_kubernetes_context(text)
        
        # Should detect both variations
        assert "Deployment" in context["api_objects"]
        assert context["kubernetes_score"] > 0