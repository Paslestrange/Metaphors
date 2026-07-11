"""Unit tests for MockSource data provider."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.entities import Entity, EntityType, EntityState
from engine.sources.mock import MockSource


def test_mock_source_returns_entities():
    """MockSource.fetch returns a non-empty list of Entity instances."""
    src = MockSource()
    entities = src.fetch()
    assert len(entities) > 0, "fetch() must return at least one entity"
    for e in entities:
        assert isinstance(e, Entity), f"Expected Entity, got {type(e)}"


def test_mock_source_has_hierarchy():
    """MockSource produces CLUSTER, NODE, and SERVICE entity types."""
    src = MockSource()
    entities = src.fetch()
    types_present = {e.type for e in entities}
    assert EntityType.CLUSTER in types_present, "Missing CLUSTER type"
    assert EntityType.NODE in types_present, "Missing NODE type"
    assert EntityType.SERVICE in types_present, "Missing SERVICE type"


def test_mock_source_states():
    """MockSource produces at least one HEALTHY or RUNNING entity."""
    src = MockSource()
    entities = src.fetch()
    states_present = {e.state for e in entities}
    assert EntityState.HEALTHY in states_present or EntityState.RUNNING in states_present, \
        f"Expected HEALTHY or RUNNING state, got: {states_present}"


def test_mock_source_ids_unique():
    """All entity IDs from MockSource are unique (no duplicates)."""
    src = MockSource()
    entities = src.fetch()
    ids = [e.id for e in entities]
    assert len(ids) == len(set(ids)), \
        f"Duplicate IDs found: {[x for x in ids if ids.count(x) > 1]}"


if __name__ == "__main__":
    test_mock_source_returns_entities()
    test_mock_source_has_hierarchy()
    test_mock_source_states()
    test_mock_source_ids_unique()
    print("All tests passed.")
