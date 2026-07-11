"""Comprehensive unit tests for engine.entities module."""
import pytest
from engine.entities import Entity, EntityType, EntityState


# ---------------------------------------------------------------------------
# EntityType enum
# ---------------------------------------------------------------------------

class TestEntityType:
    """All EntityType values exist and round-trip."""

    EXPECTED = [
        "cluster", "node", "namespace", "service", "container",
        "process", "agent", "session", "queue", "database", "custom",
    ]

    def test_all_values_present(self):
        values = {e.value for e in EntityType}
        assert values == set(self.EXPECTED)

    def test_count(self):
        assert len(EntityType) == 11

    @pytest.mark.parametrize("val", EXPECTED)
    def test_lookup_by_value(self, val):
        assert EntityType(val).value == val

    def test_is_str_subclass(self):
        assert isinstance(EntityType.CLUSTER, str)


# ---------------------------------------------------------------------------
# EntityState enum
# ---------------------------------------------------------------------------

class TestEntityState:
    """All EntityState values exist and round-trip."""

    EXPECTED = [
        "unknown", "healthy", "running", "idle", "warning",
        "degraded", "critical", "stopped", "pending", "scaling",
    ]

    def test_all_values_present(self):
        values = {e.value for e in EntityState}
        assert values == set(self.EXPECTED)

    def test_count(self):
        assert len(EntityState) == 10

    @pytest.mark.parametrize("val", EXPECTED)
    def test_lookup_by_value(self, val):
        assert EntityState(val).value == val

    def test_is_str_subclass(self):
        assert isinstance(EntityState.HEALTHY, str)


# ---------------------------------------------------------------------------
# Entity creation — all fields
# ---------------------------------------------------------------------------

class TestCreateEntity:
    """Entity can be created with every field specified."""

    def test_all_fields(self):
        e = Entity(
            id="e1",
            type=EntityType.SERVICE,
            name="api-gateway",
            state=EntityState.HEALTHY,
            metrics={"cpu": 42.5, "mem": 1024},
            children=["c1", "c2"],
            parent="p1",
            labels={"env": "prod", "team": "platform"},
            annotations={"version": "1.2.3"},
            source="kubernetes",
        )
        assert e.id == "e1"
        assert e.type is EntityType.SERVICE
        assert e.name == "api-gateway"
        assert e.state is EntityState.HEALTHY
        assert e.metrics == {"cpu": 42.5, "mem": 1024}
        assert e.children == ["c1", "c2"]
        assert e.parent == "p1"
        assert e.labels == {"env": "prod", "team": "platform"}
        assert e.annotations == {"version": "1.2.3"}
        assert e.source == "kubernetes"

    def test_minimal_fields(self):
        """Only required fields (id, type, name)."""
        e = Entity(id="x", type=EntityType.NODE, name="n1")
        assert e.id == "x"
        assert e.type is EntityType.NODE
        assert e.name == "n1"


# ---------------------------------------------------------------------------
# Entity defaults
# ---------------------------------------------------------------------------

class TestEntityDefaults:
    """Optional fields have correct defaults."""

    def test_default_state(self):
        e = Entity(id="d1", type=EntityType.PROCESS, name="worker")
        assert e.state is EntityState.UNKNOWN

    def test_default_metrics(self):
        e = Entity(id="d2", type=EntityType.PROCESS, name="worker")
        assert e.metrics == {}

    def test_default_children(self):
        e = Entity(id="d3", type=EntityType.PROCESS, name="worker")
        assert e.children == []

    def test_default_parent(self):
        e = Entity(id="d4", type=EntityType.PROCESS, name="worker")
        assert e.parent is None

    def test_default_labels(self):
        e = Entity(id="d5", type=EntityType.PROCESS, name="worker")
        assert e.labels == {}

    def test_default_annotations(self):
        e = Entity(id="d6", type=EntityType.PROCESS, name="worker")
        assert e.annotations == {}

    def test_default_source(self):
        e = Entity(id="d7", type=EntityType.PROCESS, name="worker")
        assert e.source == ""

    def test_mutable_defaults_are_independent(self):
        """Each instance gets its own dict/list — no shared mutable state."""
        e1 = Entity(id="a", type=EntityType.AGENT, name="a1")
        e2 = Entity(id="b", type=EntityType.AGENT, name="a2")
        e1.metrics["x"] = 1
        e1.children.append("c")
        assert "x" not in e2.metrics
        assert "c" not in e2.children


# ---------------------------------------------------------------------------
# Entity hierarchy — parent/children relationships
# ---------------------------------------------------------------------------

class TestEntityHierarchy:
    """Parent/children wiring (IDs, not object refs)."""

    def test_parent_child_link(self):
        parent = Entity(id="parent", type=EntityType.CLUSTER, name="c1")
        child = Entity(id="child", type=EntityType.NODE, name="n1", parent="parent")
        parent.children.append("child")

        assert child.parent == "parent"
        assert "child" in parent.children

    def test_multiple_children(self):
        parent = Entity(id="ns", type=EntityType.NAMESPACE, name="default")
        for i in range(5):
            cid = f"svc-{i}"
            parent.children.append(cid)
        assert len(parent.children) == 5

    def test_orphan_entity(self):
        e = Entity(id="lonely", type=EntityType.DATABASE, name="db1")
        assert e.parent is None
        assert e.children == []

    def test_deep_hierarchy(self):
        """cluster -> namespace -> service -> container."""
        cluster = Entity(id="c", type=EntityType.CLUSTER, name="prod")
        ns = Entity(id="ns", type=EntityType.NAMESPACE, name="app", parent="c")
        svc = Entity(id="svc", type=EntityType.SERVICE, name="api", parent="ns")
        ctr = Entity(id="ctr", type=EntityType.CONTAINER, name="main", parent="svc")

        assert ctr.parent == "svc"
        assert svc.parent == "ns"
        assert ns.parent == "c"
        assert cluster.parent is None


# ---------------------------------------------------------------------------
# to_dict serialization
# ---------------------------------------------------------------------------

class TestEntityToDict:
    """Entity.to_dict() produces correct dict representation."""

    def test_full_roundtrip(self):
        e = Entity(
            id="e1",
            type=EntityType.SERVICE,
            name="api",
            state=EntityState.RUNNING,
            metrics={"rps": 100},
            children=["c1"],
            parent="ns1",
            labels={"env": "staging"},
            annotations={"note": "test"},
            source="mock",
        )
        d = e.to_dict()
        assert d == {
            "id": "e1",
            "type": "service",
            "name": "api",
            "state": "running",
            "metrics": {"rps": 100},
            "children": ["c1"],
            "parent": "ns1",
            "labels": {"env": "staging"},
            "annotations": {"note": "test"},
            "source": "mock",
        }

    def test_defaults_serialized(self):
        e = Entity(id="x", type=EntityType.NODE, name="n1")
        d = e.to_dict()
        assert d["state"] == "unknown"
        assert d["metrics"] == {}
        assert d["children"] == []
        assert d["parent"] is None
        assert d["labels"] == {}
        assert d["annotations"] == {}
        assert d["source"] == ""

    def test_type_and_state_are_strings(self):
        e = Entity(id="z", type=EntityType.AGENT, name="a")
        d = e.to_dict()
        assert isinstance(d["type"], str)
        assert isinstance(d["state"], str)
        assert d["type"] == "agent"
        assert d["state"] == "unknown"


# ---------------------------------------------------------------------------
# from_dict deserialization
# ---------------------------------------------------------------------------

class TestEntityFromDict:
    """Entity.from_dict() reconstructs Entity from dict."""

    def test_full_dict(self):
        data = {
            "id": "e1",
            "type": "service",
            "name": "api",
            "state": "running",
            "metrics": {"rps": 100},
            "children": ["c1"],
            "parent": "ns1",
            "labels": {"env": "staging"},
            "annotations": {"note": "test"},
            "source": "mock",
        }
        e = Entity.from_dict(data)
        assert e.id == "e1"
        assert e.type is EntityType.SERVICE
        assert e.name == "api"
        assert e.state is EntityState.RUNNING
        assert e.metrics == {"rps": 100}
        assert e.children == ["c1"]
        assert e.parent == "ns1"
        assert e.labels == {"env": "staging"}
        assert e.annotations == {"note": "test"}
        assert e.source == "mock"

    def test_minimal_dict(self):
        """Only required keys; optional keys get defaults."""
        data = {"id": "m1", "type": "node", "name": "n1"}
        e = Entity.from_dict(data)
        assert e.state is EntityState.UNKNOWN
        assert e.metrics == {}
        assert e.children == []
        assert e.parent is None
        assert e.source == ""

    def test_missing_state_defaults_unknown(self):
        data = {"id": "x", "type": "process", "name": "p"}
        e = Entity.from_dict(data)
        assert e.state is EntityState.UNKNOWN

    def test_invalid_type_raises(self):
        data = {"id": "x", "type": "bogus", "name": "n"}
        with pytest.raises(ValueError):
            Entity.from_dict(data)

    def test_invalid_state_raises(self):
        data = {"id": "x", "type": "node", "name": "n", "state": "explode"}
        with pytest.raises(ValueError):
            Entity.from_dict(data)


# ---------------------------------------------------------------------------
# Serialization roundtrip (to_dict -> from_dict)
# ---------------------------------------------------------------------------

class TestSerializationRoundtrip:
    """to_dict -> from_dict -> to_dict produces identical output."""

    def test_roundtrip_full(self):
        original = Entity(
            id="rt1",
            type=EntityType.CONTAINER,
            name="redis",
            state=EntityState.DEGRADED,
            metrics={"latency_ms": 5},
            children=["sub1"],
            parent="svc1",
            labels={"tier": "cache"},
            annotations={"owner": "team-a"},
            source="docker",
        )
        d1 = original.to_dict()
        restored = Entity.from_dict(d1)
        d2 = restored.to_dict()
        assert d1 == d2

    def test_roundtrip_defaults(self):
        original = Entity(id="rt2", type=EntityType.QUEUE, name="jobs")
        d1 = original.to_dict()
        restored = Entity.from_dict(d1)
        d2 = restored.to_dict()
        assert d1 == d2

    def test_roundtrip_all_types(self):
        """Every EntityType survives a roundtrip."""
        for et in EntityType:
            e = Entity(id=f"rt-{et.value}", type=et, name=f"test-{et.value}")
            d = e.to_dict()
            restored = Entity.from_dict(d)
            assert restored.type is et

    def test_roundtrip_all_states(self):
        """Every EntityState survives a roundtrip."""
        for es in EntityState:
            e = Entity(id=f"rt-{es.value}", type=EntityType.CUSTOM, name="n", state=es)
            d = e.to_dict()
            restored = Entity.from_dict(d)
            assert restored.state is es
