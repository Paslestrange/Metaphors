"""Tests for SpaceStationRenderer metaphor."""
import pytest
from engine.metaphors.space import SpaceStationRenderer, STATE_COLORS


def _make_entities():
    """Standard test entity hierarchy."""
    return [
        {"id": "c1", "type": "cluster", "name": "Alpha Ring", "state": "healthy",
         "parent": None, "children": ["n1", "n2"], "metrics": {"cpu": 60, "mem": 40}},
        {"id": "n1", "type": "node", "name": "Lab Module", "state": "running",
         "parent": "c1", "children": ["s1"], "metrics": {"cpu": 50, "mem": 30}},
        {"id": "n2", "type": "node", "name": "Cargo Module", "state": "warning",
         "parent": "c1", "children": ["s2"], "metrics": {"cpu": 80, "mem": 90}},
        {"id": "s1", "type": "service", "name": "Experiment Pod", "state": "healthy",
         "parent": "n1", "children": ["ct1"], "metrics": {"cpu": 30, "mem": 20, "req_per_sec": 5}},
        {"id": "s2", "type": "service", "name": "Storage Pod", "state": "warning",
         "parent": "n2", "children": ["ct2"], "metrics": {"cpu": 85, "mem": 95, "req_per_sec": 12}},
        {"id": "ct1", "type": "container", "name": "Cryo Chamber", "state": "healthy",
         "parent": "s1", "children": [], "metrics": {"cpu": 10, "mem": 15}},
        {"id": "ct2", "type": "container", "name": "Fuel Cell", "state": "critical",
         "parent": "s2", "children": [], "metrics": {"cpu": 99, "mem": 98}},
    ]


class TestSpaceStationLayout:
    def test_compute_layout_returns_dict(self):
        r = SpaceStationRenderer()
        entities = _make_entities()
        layout = r.compute_layout(entities, 800, 600)
        assert isinstance(layout, dict)
        for eid in ["c1", "n1", "n2", "s1", "s2", "ct1", "ct2"]:
            assert eid in layout

    def test_radial_arrangement(self):
        """Modules (children of cluster) should be arranged radially around center."""
        r = SpaceStationRenderer()
        entities = _make_entities()
        layout = r.compute_layout(entities, 800, 600)
        # Cluster center should be near canvas center
        c1 = layout["c1"]
        assert abs(c1["cx"] - 400) < 50
        assert abs(c1["cy"] - 300) < 50
        # Modules should have angular positions
        n1 = layout["n1"]
        n2 = layout["n2"]
        assert "angle" in n1
        assert "angle" in n2
        assert n1["angle"] != n2["angle"]

    def test_empty_entities(self):
        r = SpaceStationRenderer()
        layout = r.compute_layout([], 800, 600)
        assert layout == {}

    def test_single_cluster_no_children(self):
        r = SpaceStationRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Solo", "state": "healthy",
             "parent": None, "children": [], "metrics": {}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert "c1" in layout

    def test_power_core_radius_scales_with_cpu(self):
        """CPU metric should influence power core glow (ring radius)."""
        r = SpaceStationRenderer()
        base = {"id": "c1", "type": "cluster", "parent": None, "children": [],
                "name": "Ring", "state": "healthy", "metrics": {}}

        low = [base.copy()]
        low[0]["metrics"] = {"cpu": 10}
        high = [base.copy()]
        high[0]["metrics"] = {"cpu": 90}

        layout_low = r.compute_layout(low, 800, 600)
        layout_high = r.compute_layout(high, 800, 600)
        assert layout_high["c1"]["core_radius"] > layout_low["c1"]["core_radius"]

    def test_storage_fill_scales_with_memory(self):
        """Memory metric should influence storage bay fill level."""
        r = SpaceStationRenderer()
        entities_low = [
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "pod", "state": "healthy", "metrics": {"mem": 10}},
        ]
        entities_high = [
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "pod", "state": "healthy", "metrics": {"mem": 90}},
        ]
        layout_low = r.compute_layout(entities_low, 800, 600)
        layout_high = r.compute_layout(entities_high, 800, 600)
        assert layout_high["s1"]["storage_fill"] > layout_low["s1"]["storage_fill"]


class TestSpaceStationHitTest:
    def test_hit_test_inside(self):
        r = SpaceStationRenderer()
        entities = _make_entities()
        r.compute_layout(entities, 800, 600)
        # Center of cluster should hit
        assert r.hit_test({"id": "c1"}, 400, 300) is True

    def test_hit_test_outside(self):
        r = SpaceStationRenderer()
        entities = _make_entities()
        r.compute_layout(entities, 800, 600)
        assert r.hit_test({"id": "c1"}, 0, 0) is False

    def test_hit_test_missing_entity(self):
        r = SpaceStationRenderer()
        r.compute_layout([], 800, 600)
        assert r.hit_test({"id": "missing"}, 0, 0) is False


class TestSpaceStationTooltip:
    def test_tooltip_includes_name_and_state(self):
        r = SpaceStationRenderer()
        entity = {"id": "n1", "name": "Lab Module", "type": "node",
                  "state": "running", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Lab Module" in tip
        assert "nominal" in tip  # "running" maps to "nominal" in life support

    def test_tooltip_includes_metrics(self):
        r = SpaceStationRenderer()
        entity = {"id": "s1", "name": "Pod", "type": "service", "state": "healthy",
                  "metrics": {"cpu": 42, "mem": 77, "req_per_sec": 5}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "42" in tip
        assert "77" in tip
        assert "power core" in tip.lower() or "cpu" in tip.lower()

    def test_tooltip_life_support_mapping(self):
        r = SpaceStationRenderer()
        entity = {"id": "n1", "name": "Module", "type": "node",
                  "state": "critical", "metrics": {"cpu": 99}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "life support" in tip.lower() or "critical" in tip.lower()


class TestSpaceStationConfig:
    def test_config_has_required_keys(self):
        r = SpaceStationRenderer()
        cfg = r.config()
        assert cfg["name"] == "space"
        assert "description" in cfg
        assert "state_colors" in cfg
        assert "mappings" in cfg
        assert cfg["mappings"]["cluster"] == "station ring"
        assert cfg["mappings"]["node"] == "module"
        assert cfg["mappings"]["service"] == "pod"
        assert cfg["mappings"]["container"] == "compartment"


class TestSpaceStationRender:
    def test_render_calls_context_methods(self):
        r = SpaceStationRenderer()
        entities = _make_entities()

        class MockCtx:
            def __init__(self):
                self.calls = []
            def fillStyle(self, c): self.calls.append(("fillStyle", c))
            def fillRect(self, *a): self.calls.append(("fillRect", a))
            def strokeStyle(self, c): self.calls.append(("strokeStyle", c))
            def strokeRect(self, *a): self.calls.append(("strokeRect", a))
            def lineWidth(self, w): self.calls.append(("lineWidth", w))
            def font(self, f): self.calls.append(("font", f))
            def fillText(self, *a): self.calls.append(("fillText", a))
            def beginPath(self): self.calls.append(("beginPath",))
            def arc(self, *a): self.calls.append(("arc", a))
            def stroke(self): self.calls.append(("stroke",))
            def fill(self): self.calls.append(("fill",))
            def moveTo(self, *a): self.calls.append(("moveTo", a))
            def lineTo(self, *a): self.calls.append(("lineTo", a))
            def closePath(self): self.calls.append(("closePath",))
            def save(self): self.calls.append(("save",))
            def restore(self): self.calls.append(("restore",))
            def globalAlpha(self, a): self.calls.append(("globalAlpha", a))

        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        assert len(ctx.calls) > 0
        # Should draw background (dark space)
        assert any(c[0] == "fillRect" for c in ctx.calls)
        # Should draw arcs (station rings, modules)
        assert any(c[0] == "arc" for c in ctx.calls)

    def test_render_draws_stars(self):
        """Background should include star rendering."""
        r = SpaceStationRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Ring", "state": "healthy",
             "parent": None, "children": [], "metrics": {}},
        ]

        class MockCtx:
            def __init__(self):
                self.calls = []
            def fillStyle(self, c): self.calls.append(("fillStyle", c))
            def fillRect(self, *a): self.calls.append(("fillRect", a))
            def strokeStyle(self, c): self.calls.append(("strokeStyle", c))
            def strokeRect(self, *a): self.calls.append(("strokeRect", a))
            def lineWidth(self, w): self.calls.append(("lineWidth", w))
            def font(self, f): self.calls.append(("font", f))
            def fillText(self, *a): self.calls.append(("fillText", a))
            def beginPath(self): self.calls.append(("beginPath",))
            def arc(self, *a): self.calls.append(("arc", a))
            def stroke(self): self.calls.append(("stroke",))
            def fill(self): self.calls.append(("fill",))
            def moveTo(self, *a): self.calls.append(("moveTo", a))
            def lineTo(self, *a): self.calls.append(("lineTo", a))
            def closePath(self): self.calls.append(("closePath",))
            def save(self): self.calls.append(("save",))
            def restore(self): self.calls.append(("restore",))
            def globalAlpha(self, a): self.calls.append(("globalAlpha", a))

        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        # Stars are small filled rects or arcs in the background
        fill_calls = [c for c in ctx.calls if c[0] == "fillRect"]
        assert len(fill_calls) > 1  # At least background + some stars


class TestSpaceStationBreachAnimation:
    def test_critical_state_has_breach_flag(self):
        """Entities in critical state should have breach animation data."""
        r = SpaceStationRenderer()
        entities = _make_entities()
        layout = r.compute_layout(entities, 800, 600)
        # ct2 is critical
        assert layout["ct2"].get("breach") is True
        # s2 is warning, not critical
        assert layout["s2"].get("breach") is not True

    def test_healthy_no_breach(self):
        r = SpaceStationRenderer()
        entities = _make_entities()
        layout = r.compute_layout(entities, 800, 600)
        assert layout["ct1"].get("breach") is not True


class TestSpaceStationDockingPorts:
    def test_docking_port_glow_with_requests(self):
        """Services with req_per_sec should have docking port glow."""
        r = SpaceStationRenderer()
        entities = [
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "busy", "state": "healthy", "metrics": {"req_per_sec": 50}},
            {"id": "s2", "type": "service", "parent": "n1", "children": [],
             "name": "idle", "state": "healthy", "metrics": {"req_per_sec": 0}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert layout["s1"]["docking_glow"] > layout["s2"]["docking_glow"]

    def test_no_metrics_no_docking_glow(self):
        r = SpaceStationRenderer()
        entities = [
            {"id": "s1", "type": "service", "parent": None, "children": [],
             "name": "bare", "state": "healthy", "metrics": {}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert layout["s1"]["docking_glow"] == 0.0
