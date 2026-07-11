"""Tests for TrafficLightRenderer metaphor — Cluster=Intersection, Node=Road,
Service=Traffic Light, Container=Lamp."""
import pytest
from engine.metaphors.traffic_light import TrafficLightRenderer, STATE_COLORS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_entities():
    """Standard 4-level entity hierarchy for testing."""
    return [
        {"id": "c1", "type": "cluster", "name": "Main St & 1st",
         "state": "healthy", "parent": None, "children": ["n1", "n2"],
         "metrics": {}},
        {"id": "n1", "type": "node", "name": "Main St",
         "state": "running", "parent": "c1", "children": ["s1"],
         "metrics": {}},
        {"id": "n2", "type": "node", "name": "1st Ave",
         "state": "running", "parent": "c1", "children": ["s2"],
         "metrics": {}},
        {"id": "s1", "type": "service", "name": "North Light",
         "state": "healthy", "parent": "n1", "children": ["ct1"],
         "metrics": {"cpu": 60}},
        {"id": "s2", "type": "service", "name": "East Light",
         "state": "critical", "parent": "n2", "children": ["ct2"],
         "metrics": {"cpu": 90}},
        {"id": "ct1", "type": "container", "name": "Green Lamp",
         "state": "healthy", "parent": "s1", "children": [],
         "metrics": {"cpu": 30}},
        {"id": "ct2", "type": "container", "name": "Red Lamp",
         "state": "critical", "parent": "s2", "children": [],
         "metrics": {"cpu": 80}},
    ]


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

class TestTrafficLightLayout:
    def test_compute_layout_returns_dict(self):
        r = TrafficLightRenderer()
        layout = r.compute_layout(make_entities(), 800, 600)
        assert isinstance(layout, dict)
        assert "c1" in layout

    def test_all_entities_have_positions(self):
        r = TrafficLightRenderer()
        entities = make_entities()
        layout = r.compute_layout(entities, 800, 600)
        for e in entities:
            assert e["id"] in layout, f"Missing layout for {e['id']}"

    def test_positions_within_bounds(self):
        r = TrafficLightRenderer()
        layout = r.compute_layout(make_entities(), 800, 600)
        for eid, pos in layout.items():
            assert pos["x"] >= 0
            assert pos["y"] >= 0
            assert pos["w"] > 0
            assert pos["h"] > 0
            assert pos["x"] + pos["w"] <= 800
            assert pos["y"] + pos["h"] <= 600

    def test_empty_entities(self):
        r = TrafficLightRenderer()
        layout = r.compute_layout([], 800, 600)
        assert layout == {}

    def test_multiple_clusters_side_by_side(self):
        r = TrafficLightRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "A", "state": "healthy",
             "parent": None, "children": [], "metrics": {}},
            {"id": "c2", "type": "cluster", "name": "B", "state": "healthy",
             "parent": None, "children": [], "metrics": {}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert layout["c1"]["x"] < layout["c2"]["x"]

    def test_cpu_affects_light_width(self):
        r = TrafficLightRenderer()
        entities_low = [
            {"id": "c1", "type": "cluster", "name": "X", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "R", "state": "running",
             "parent": "c1", "children": ["s1"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "L", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"cpu": 20}},
        ]
        entities_high = [
            {"id": "c1", "type": "cluster", "name": "X", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "R", "state": "running",
             "parent": "c1", "children": ["s1"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "L", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"cpu": 90}},
        ]
        layout_low = r.compute_layout(entities_low, 800, 600)
        layout_high = r.compute_layout(entities_high, 800, 600)
        assert layout_high["s1"]["w"] > layout_low["s1"]["w"]


# ---------------------------------------------------------------------------
# Tooltip
# ---------------------------------------------------------------------------

class TestTrafficLightTooltip:
    def test_tooltip_contains_name(self):
        r = TrafficLightRenderer()
        entity = {"id": "s1", "name": "North Light", "type": "service",
                  "state": "healthy", "metrics": {"cpu": 60}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "North Light" in tip
        assert "Traffic Light" in tip

    def test_tooltip_shows_signal_state(self):
        r = TrafficLightRenderer()
        entity = {"id": "s1", "name": "Light", "type": "service",
                  "state": "critical", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "RED" in tip

    def test_tooltip_healthy_is_green(self):
        r = TrafficLightRenderer()
        entity = {"id": "s1", "name": "Light", "type": "service",
                  "state": "healthy", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "GREEN" in tip

    def test_tooltip_includes_metrics(self):
        r = TrafficLightRenderer()
        entity = {"id": "s1", "name": "Light", "type": "service",
                  "state": "healthy", "metrics": {"cpu": 75, "mem": 40}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "75%" in tip
        assert "40%" in tip

    def test_tooltip_cluster_mapping(self):
        r = TrafficLightRenderer()
        entity = {"id": "c1", "name": "Main & 1st", "type": "cluster",
                  "state": "healthy", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Intersection" in tip

    def test_tooltip_node_mapping(self):
        r = TrafficLightRenderer()
        entity = {"id": "n1", "name": "Main St", "type": "node",
                  "state": "running", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Road" in tip

    def test_tooltip_container_mapping(self):
        r = TrafficLightRenderer()
        entity = {"id": "ct1", "name": "Green Lamp", "type": "container",
                  "state": "healthy", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Lamp" in tip


# ---------------------------------------------------------------------------
# Hit Test
# ---------------------------------------------------------------------------

class TestTrafficLightHitTest:
    def test_hit_inside(self):
        r = TrafficLightRenderer()
        entities = make_entities()
        r.compute_layout(entities, 800, 600)
        pos = r._layout["c1"]
        cx = pos["x"] + pos["w"] / 2
        cy = pos["y"] + pos["h"] / 2
        assert r.hit_test(entities[0], cx, cy) is True

    def test_hit_outside(self):
        r = TrafficLightRenderer()
        entities = make_entities()
        r.compute_layout(entities, 800, 600)
        assert r.hit_test(entities[0], -100, -100) is False

    def test_hit_unknown_entity(self):
        r = TrafficLightRenderer()
        r.compute_layout(make_entities(), 800, 600)
        entity = {"id": "nonexistent"}
        assert r.hit_test(entity, 0, 0) is False

    def test_hit_service(self):
        r = TrafficLightRenderer()
        entities = make_entities()
        r.compute_layout(entities, 800, 600)
        pos = r._layout["s1"]
        cx = pos["x"] + pos["w"] / 2
        cy = pos["y"] + pos["h"] / 2
        svc = next(e for e in entities if e["id"] == "s1")
        assert r.hit_test(svc, cx, cy) is True


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

class MockCtx:
    """Mock canvas context for testing render calls."""
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return method


class TestTrafficLightRender:
    def test_render_calls_ctx(self):
        r = TrafficLightRenderer()
        ctx = MockCtx()
        r.render(make_entities(), ctx, 800, 600)
        assert len(ctx.calls) > 0

    def test_render_draws_background(self):
        r = TrafficLightRenderer()
        ctx = MockCtx()
        r.render(make_entities(), ctx, 800, 600)
        fill_calls = [c for c in ctx.calls if c[0] == "fillRect"]
        assert len(fill_calls) > 0

    def test_render_empty_entities(self):
        r = TrafficLightRenderer()
        ctx = MockCtx()
        r.render([], ctx, 800, 600)
        # Should still draw background
        fill_calls = [c for c in ctx.calls if c[0] == "fillRect"]
        assert len(fill_calls) >= 1

    def test_render_draws_all_entity_types(self):
        r = TrafficLightRenderer()
        ctx = MockCtx()
        r.render(make_entities(), ctx, 800, 600)
        # Should have arc calls (for service signal circles)
        arc_calls = [c for c in ctx.calls if c[0] == "arc"]
        assert len(arc_calls) > 0


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestTrafficLightConfig:
    def test_config_has_name(self):
        r = TrafficLightRenderer()
        cfg = r.config()
        assert cfg["name"] == "traffic_light"

    def test_config_has_description(self):
        r = TrafficLightRenderer()
        cfg = r.config()
        assert "description" in cfg

    def test_config_has_state_colors(self):
        r = TrafficLightRenderer()
        cfg = r.config()
        assert "state_colors" in cfg
        assert "healthy" in cfg["state_colors"]

    def test_config_has_mappings(self):
        r = TrafficLightRenderer()
        cfg = r.config()
        mappings = cfg["mappings"]
        assert mappings["cluster"] == "intersection"
        assert mappings["node"] == "road"
        assert mappings["service"] == "traffic_light"
        assert mappings["container"] == "lamp"
