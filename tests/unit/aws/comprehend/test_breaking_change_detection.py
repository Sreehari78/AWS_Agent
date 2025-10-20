"""Unit tests for breaking change detection functionality."""

import pytest
from src.eks_upgrade_agent.common.aws.comprehend.entity_extractor import EntityExtractor
from src.eks_upgrade_agent.common.models.aws_ai import ComprehendEntity


@pytest.fixture
def extractor():
    """Create EntityExtractor instance."""
    return EntityExtractor(min_confidence=0.5)


class TestBreakingChangeDetection:
    """Test cases for breaking change detection methods."""

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

    def test_extract_breaking_changes_multiple_indicators(self, extractor):
        """Test extraction with multiple breaking change indicators."""
        text = "BREAKING: API removed. DEPRECATED: Old version. Migration required for all users."
        
        entities = [
            ComprehendEntity(text="BREAKING", type="BREAKING_CHANGE_INDICATORS", confidence=0.9, begin_offset=0, end_offset=8),
            ComprehendEntity(text="removed", type="BREAKING_CHANGE_INDICATORS", confidence=0.8, begin_offset=14, end_offset=21),
            ComprehendEntity(text="DEPRECATED", type="BREAKING_CHANGE_INDICATORS", confidence=0.9, begin_offset=23, end_offset=33),
            ComprehendEntity(text="migration required", type="BREAKING_CHANGE_INDICATORS", confidence=0.8, begin_offset=48, end_offset=66)
        ]
        
        breaking_changes = extractor.extract_breaking_changes(entities, text)
        
        assert len(breaking_changes) == 4
        indicators = [bc["indicator"] for bc in breaking_changes]
        assert "BREAKING" in indicators
        assert "removed" in indicators
        assert "DEPRECATED" in indicators
        assert "migration required" in indicators

    def test_extract_api_deprecations_no_nearby_resources(self, extractor):
        """Test API deprecation extraction when no nearby resources found."""
        text = "Something is deprecated but no API info nearby."
        
        entities = [
            ComprehendEntity(text="deprecated", type="BREAKING_CHANGE_INDICATORS", confidence=0.8, begin_offset=13, end_offset=23)
        ]
        
        deprecations = extractor.extract_api_deprecations(entities, text)
        
        # Should not create deprecation entries without nearby API info
        assert len(deprecations) == 0

    def test_extract_breaking_changes_context_extraction(self, extractor):
        """Test context extraction around breaking changes."""
        text = "In the new version, there is a breaking change that removes the old API. This affects all users who depend on it."
        
        entities = [
            ComprehendEntity(text="breaking change", type="BREAKING_CHANGE_INDICATORS", confidence=0.9, begin_offset=32, end_offset=47)
        ]
        
        breaking_changes = extractor.extract_breaking_changes(entities, text)
        
        assert len(breaking_changes) == 1
        context = breaking_changes[0]["context"]
        
        # Context should include surrounding text
        assert "breaking change" in context
        assert len(context) > len("breaking change")  # Should have surrounding context

    def test_extract_api_deprecations_proximity_detection(self, extractor):
        """Test that API deprecations only match nearby resources."""
        # Create text where entities are more than 200 characters apart
        text = "The Deployment resource is great." + " " * 200 + "Much later in the text, something is deprecated but unrelated."
        
        entities = [
            ComprehendEntity(text="Deployment", type="RESOURCE_KIND", confidence=0.9, begin_offset=4, end_offset=14),
            ComprehendEntity(text="deprecated", type="BREAKING_CHANGE_INDICATORS", confidence=0.8, begin_offset=240, end_offset=250)
        ]
        
        deprecations = extractor.extract_api_deprecations(entities, text)
        
        # Should not match because Deployment and deprecated are too far apart (>200 chars)
        assert len(deprecations) == 0