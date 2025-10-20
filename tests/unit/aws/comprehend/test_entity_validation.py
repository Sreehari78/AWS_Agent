"""Unit tests for entity validation functionality."""

import pytest
from src.eks_upgrade_agent.common.aws.comprehend.entity_extractor import EntityExtractor
from src.eks_upgrade_agent.common.models.aws_ai import ComprehendEntity


@pytest.fixture
def extractor():
    """Create EntityExtractor instance."""
    return EntityExtractor(min_confidence=0.5)


class TestEntityValidation:
    """Test cases for entity validation methods."""

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