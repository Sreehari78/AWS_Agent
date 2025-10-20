"""Tests for collection management functionality."""

import pytest
from pathlib import Path

from src.eks_upgrade_agent.common.models.artifacts import ArtifactCollection


class TestCollectionManagement:
    """Test cases for collection management operations."""

    def test_create_collection(self, artifacts_manager, sample_session):
        """Test creating an artifact collection."""
        collection = artifacts_manager.create_collection(
            session_id=sample_session.session_id,
            collection_name="Test Collection",
            description="Test collection description"
        )
        
        assert isinstance(collection, ArtifactCollection)
        assert collection.name == "Test Collection"
        assert collection.description == "Test collection description"
        # Collection should be added to the session
        updated_session = artifacts_manager.get_session(sample_session.session_id)
        assert collection.collection_id in updated_session.collections
        
        # Check that collection exists in session
        assert collection.collection_id in updated_session.collections

    def test_create_collection_invalid_session(self, artifacts_manager):
        """Test creating collection with invalid session."""
        collection = artifacts_manager.create_collection(
            session_id="nonexistent",
            collection_name="Test Collection"
        )
        assert collection is None

    def test_get_collection(self, artifacts_manager, sample_session):
        """Test getting a collection by ID from session."""
        collection = artifacts_manager.create_collection(
            session_id=sample_session.session_id,
            collection_name="Test Collection"
        )
        
        # Get collection from session
        updated_session = artifacts_manager.get_session(sample_session.session_id)
        retrieved = updated_session.collections.get(collection.collection_id)
        assert retrieved is not None
        assert retrieved.collection_id == collection.collection_id
        
        # Test nonexistent collection
        assert updated_session.collections.get("nonexistent") is None

    def test_list_collections(self, artifacts_manager, sample_session):
        """Test listing collections in a session."""
        # Initially empty
        session = artifacts_manager.get_session(sample_session.session_id)
        assert len(session.collections) == 0
        
        # Create collections
        collection1 = artifacts_manager.create_collection(
            sample_session.session_id, "Collection 1"
        )
        collection2 = artifacts_manager.create_collection(
            sample_session.session_id, "Collection 2"
        )
        
        # Get updated session
        updated_session = artifacts_manager.get_session(sample_session.session_id)
        collections = list(updated_session.collections.values())
        assert len(collections) == 2
        
        collection_ids = [c.collection_id for c in collections]
        assert collection1.collection_id in collection_ids
        assert collection2.collection_id in collection_ids

    def test_collection_directory_structure(self, artifacts_manager, sample_session, temp_dir):
        """Test collection directory structure."""
        collection = artifacts_manager.create_collection(
            sample_session.session_id, "Test Collection"
        )
        
        # Check that collection exists in session
        updated_session = artifacts_manager.get_session(sample_session.session_id)
        assert collection.collection_id in updated_session.collections
        
        # Check session directory exists
        session_dir = Path(sample_session.base_directory)
        assert session_dir.exists()
        assert session_dir.is_dir()