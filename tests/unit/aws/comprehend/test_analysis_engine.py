"""Unit tests for Comprehend analysis engine."""

import pytest
from unittest.mock import Mock, patch

from src.eks_upgrade_agent.common.aws.comprehend.analysis_engine import AnalysisEngine
from src.eks_upgrade_agent.common.models.aws_ai import ComprehendEntity


@pytest.fixture
def analysis_engine():
    """Create AnalysisEngine instance."""
    return AnalysisEngine()


@pytest.fixture
def sample_comprehend_entities():
    """Sample Comprehend entities for testing."""
    return [
        ComprehendEntity(
            text="Kubernetes",
            type="ORGANIZATION",
            confidence=0.95,
            begin_offset=0,
            end_offset=10
        ),
        ComprehendEntity(
            text="v1.28",
            type="OTHER",
            confidence=0.85,
            begin_offset=20,
            end_offset=25
        )
    ]


class TestAnalysisEngine:
    """Test cases for AnalysisEngine."""

    def test_initialization(self, analysis_engine):
        """Test AnalysisEngine initialization."""
        assert analysis_engine.entity_extractor is not None
        assert analysis_engine.custom_classifier is not None
        assert analysis_engine.result_processor is not None

    def test_analyze_kubernetes_text_structure(self, analysis_engine, sample_comprehend_entities):
        """Test analyze_kubernetes_text returns proper structure."""
        text = "Kubernetes v1.28 introduces breaking changes"
        
        result = analysis_engine.analyze_kubernetes_text(text, sample_comprehend_entities)
        
        # Check required fields
        assert "analysis_id" in result
        assert "input_text_length" in result
        assert "processing_time" in result
        assert "entities" in result
        assert "classifications" in result
        assert "kubernetes_context" in result
        assert "breaking_changes" in result
        assert "api_deprecations" in result
        assert "action_items" in result
        assert "validation" in result
        assert "summary" in result

    def test_analyze_kubernetes_text_entities(self, analysis_engine, sample_comprehend_entities):
        """Test entity processing in analysis."""
        text = "Kubernetes v1.28 Deployment deprecated"
        
        result = analysis_engine.analyze_kubernetes_text(text, sample_comprehend_entities)
        
        entities = result["entities"]
        assert "comprehend_entities" in entities
        assert "kubernetes_entities" in entities
        assert "filtered_entities" in entities
        assert "entity_count" in entities
        
        # Should have both input entities and extracted K8s entities
        assert len(entities["comprehend_entities"]) == 2
        assert entities["entity_count"] >= 0

    def test_analyze_kubernetes_text_classifications(self, analysis_engine, sample_comprehend_entities):
        """Test classification processing in analysis."""
        text = "BREAKING CHANGE: The v1beta1 API is deprecated and removed"
        
        result = analysis_engine.analyze_kubernetes_text(text, sample_comprehend_entities)
        
        classifications = result["classifications"]
        assert isinstance(classifications, list)
        
        # Should detect breaking change and deprecation
        categories = [c["category"] for c in classifications]
        assert "BREAKING_CHANGE" in categories or "DEPRECATION" in categories

    def test_analyze_kubernetes_text_context(self, analysis_engine, sample_comprehend_entities):
        """Test Kubernetes context analysis."""
        text = "Update your Deployment and Service resources for vpc-cni v1.28"
        
        result = analysis_engine.analyze_kubernetes_text(text, sample_comprehend_entities)
        
        k8s_context = result["kubernetes_context"]
        assert "api_objects" in k8s_context
        assert "api_groups" in k8s_context
        assert "eks_addons" in k8s_context
        assert "version_references" in k8s_context
        assert "kubernetes_score" in k8s_context
        
        # Should detect Deployment, Service, and vpc-cni
        assert "Deployment" in k8s_context["api_objects"]
        assert "Service" in k8s_context["api_objects"]
        assert "vpc-cni" in k8s_context["eks_addons"]

    def test_detect_breaking_changes_structure(self, analysis_engine, sample_comprehend_entities):
        """Test detect_breaking_changes returns proper structure."""
        release_notes = "BREAKING: v1beta1 Ingress API removed in v1.28"
        
        result = analysis_engine.detect_breaking_changes(release_notes, sample_comprehend_entities)
        
        # Check required fields
        assert "analysis_id" in result
        assert "breaking_changes" in result
        assert "api_deprecations" in result
        assert "critical_actions" in result
        assert "kubernetes_components" in result
        assert "severity_assessment" in result
        assert "processing_time" in result

    def test_detect_breaking_changes_severity(self, analysis_engine, sample_comprehend_entities):
        """Test severity assessment in breaking changes."""
        release_notes = "BREAKING CHANGE: API removed. DEPRECATED: Old API. Security fix CVE-2023-1234"
        
        result = analysis_engine.detect_breaking_changes(release_notes, sample_comprehend_entities)
        
        severity = result["severity_assessment"]
        assert "overall_score" in severity
        assert "requires_immediate_action" in severity
        assert "migration_required" in severity
        
        # Should have high severity due to breaking changes
        assert severity["overall_score"] > 0

    def test_detect_breaking_changes_critical_actions(self, analysis_engine, sample_comprehend_entities):
        """Test critical actions extraction."""
        release_notes = "BREAKING CHANGE: Immediate action required for v1beta1 removal"
        
        result = analysis_engine.detect_breaking_changes(release_notes, sample_comprehend_entities)
        
        critical_actions = result["critical_actions"]
        assert isinstance(critical_actions, list)
        
        # Should have critical actions for breaking changes
        if critical_actions:
            for action in critical_actions:
                assert action["severity"] in ["CRITICAL", "HIGH"]

    def test_empty_text_handling(self, analysis_engine):
        """Test handling of empty text."""
        result = analysis_engine.analyze_kubernetes_text("", [])
        
        assert result["input_text_length"] == 0
        assert result["entities"]["entity_count"] == 0
        assert len(result["classifications"]) == 0

    def test_error_handling(self, analysis_engine):
        """Test error handling in analysis engine."""
        # Mock entity extractor to raise exception
        with patch.object(analysis_engine.entity_extractor, 'extract_kubernetes_entities') as mock_extract:
            mock_extract.side_effect = Exception("Test error")
            
            with pytest.raises(Exception, match="Test error"):
                analysis_engine.analyze_kubernetes_text("test", [])