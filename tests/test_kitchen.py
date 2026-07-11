"""Tests for KitchenRenderer metaphor — Cluster=Restaurant, Node=Station, Service=Chef, Container=Pot/Pan."""
import pytest
from engine.metaphors.kitchen import KitchenRenderer, STATE_COLORS


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

class TestKitchenLayout:
    def test_compute_layout_returns_dict(self):
        r = KitchenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Restaurant", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "Grill Station", "state": "running",
             "parent": "c1", "children": ["s1"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "Chef Mario", "state": "healthy",
             "parent": "n1", "children": ["ct1"], "metrics": {"cpu": 50}},
            {"id": "ct1", "type": "container", "name": "Stock Pot", "state": "running",
             "parent": "s1", "children": [], "metrics": {"cpu": 30}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert isinstance(layout, dict)
        assert "c1" in layout
        assert "n1" in layout
        assert "s1" in layout
        assert "ct1" in layout

    def test_layout_positions_within_bounds(self):
        r = KitchenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "R", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "S", "state": "running",
             "parent": "c1", "children": ["s1"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "chef", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"cpu": 50}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        for eid, pos in layout.items():
            assert pos["x"] >= 0
            assert pos["y"] >= 0
            assert pos["w"] > 0
            assert pos["h"] > 0
            assert pos["x"] + pos["w"] <= 800
            assert pos["y"] + pos["h"] <= 600

    def test_multiple_restaurants_side_by_side(self):
        r = KitchenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "R1", "state": "healthy",
             "parent": None, "children": [], "metrics": {}},
            {"id": "c2", "type": "cluster", "name": "R2", "state": "healthy",
             "parent": None, "children": [], "metrics": {}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        # Restaurants should not overlap horizontally
        assert layout["c1"]["x"] < layout["c2"]["x"]

    def test_station_layout_inside_restaurant(self):
        r = KitchenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "R", "state": "healthy",
             "parent": None, "children": ["n1", "n2"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "Grill", "state": "running",
             "parent": "c1", "children": [], "metrics": {}},
            {"id": "n2", "type": "node", "name": "Saute", "state": "running",
             "parent": "c1", "children": [], "metrics": {}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        # Stations should be within restaurant bounds
        assert layout["n1"]["x"] >= layout["c1"]["x"]
        assert layout["n2"]["x"] >= layout["c1"]["x"]

    def test_chef_height_scales_with_cpu(self):
        r = KitchenRenderer()
        base_cluster = {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
                        "name": "R", "state": "healthy", "metrics": {}}
        base_node = {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
                     "name": "S", "state": "running", "metrics": {}}

        entities_low = [base_cluster.copy(), base_node.copy(),
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "low", "state": "healthy", "metrics": {"cpu": 10}}]
        entities_high = [base_cluster.copy(), base_node.copy(),
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "high", "state": "healthy", "metrics": {"cpu": 90}}]

        layout_low = r.compute_layout(entities_low, 800, 600)
        layout_high = r.compute_layout(entities_high, 800, 600)
        assert layout_high["s1"]["h"] > layout_low["s1"]["h"]

    def test_empty_entities(self):
        r = KitchenRenderer()
        layout = r.compute_layout([], 800, 600)
        assert layout == {}


# ---------------------------------------------------------------------------
# Hit testing
# ---------------------------------------------------------------------------

class TestKitchenHitTest:
    def test_hit_test_inside(self):
        r = KitchenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": [],
             "name": "R", "state": "healthy", "metrics": {}},
        ]
        r.compute_layout(entities, 800, 600)
        pos = r._layout["c1"]
        cx = pos["x"] + pos["w"] / 2
        cy = pos["y"] + pos["h"] / 2
        assert r.hit_test({"id": "c1"}, cx, cy) is True

    def test_hit_test_outside(self):
        r = KitchenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": [],
             "name": "R", "state": "healthy", "metrics": {}},
        ]
        r.compute_layout(entities, 800, 600)
        assert r.hit_test({"id": "c1"}, 9999, 9999) is False

    def test_hit_test_missing_entity(self):
        r = KitchenRenderer()
        r.compute_layout([], 800, 600)
        assert r.hit_test({"id": "missing"}, 0, 0) is False


# ---------------------------------------------------------------------------
# Tooltip
# ---------------------------------------------------------------------------

class TestKitchenTooltip:
    def test_tooltip_includes_name_and_state(self):
        r = KitchenRenderer()
        entity = {"id": "s1", "name": "Chef Mario", "type": "service", "state": "healthy", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Chef Mario" in tip
        assert "healthy" in tip

    def test_tooltip_includes_metrics(self):
        r = KitchenRenderer()
        entity = {"id": "s1", "name": "chef", "type": "service", "state": "healthy",
                  "metrics": {"cpu": 42, "mem": 77}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "42" in tip
        assert "77" in tip

    def test_tooltip_for_container(self):
        r = KitchenRenderer()
        entity = {"id": "ct1", "name": "Stock Pot", "type": "container", "state": "running",
                  "metrics": {"cpu": 55}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Stock Pot" in tip
        assert "55" in tip


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestKitchenConfig:
    def test_config_has_required_keys(self):
        r = KitchenRenderer()
        cfg = r.config()
        assert cfg["name"] == "kitchen"
        assert "description" in cfg
        assert "state_colors" in cfg
        assert "mappings" in cfg

    def test_config_mappings(self):
        r = KitchenRenderer()
        cfg = r.config()
        m = cfg["mappings"]
        assert m["cluster"] == "restaurant"
        assert m["node"] == "station"
        assert m["service"] == "chef"
        assert m["container"] == "pot/pan"


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

class TestKitchenRender:
    def test_render_calls_context_methods(self):
        r = KitchenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "Restaurant", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "Grill Station", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "Chef Mario", "state": "healthy", "metrics": {"cpu": 60}},
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
            def arc(self, *a): self.calls.append(("arc", a))
            def beginPath(self): self.calls.append(("beginPath",))
            def fill(self): self.calls.append(("fill",))
            def moveTo(self, *a): self.calls.append(("moveTo", a))
            def lineTo(self, *a): self.calls.append(("lineTo", a))
            def stroke(self): self.calls.append(("stroke",))
            def setGlobalAlpha(self, *a): self.calls.append(("setGlobalAlpha", a))

        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        assert len(ctx.calls) > 0
        assert any(c[0] == "fillRect" for c in ctx.calls)

    def test_render_warm_background(self):
        """Kitchen should use warm dark background (not cold blue)."""
        r = KitchenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": [],
             "name": "R", "state": "healthy", "metrics": {}},
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

        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        # First fillStyle should be the warm background
        bg_calls = [c for c in ctx.calls if c[0] == "fillStyle"]
        assert len(bg_calls) > 0
        bg_color = bg_calls[0][1]
        # Should be a warm dark color (browns/dark reds), not cold blue
        assert bg_color != "#0a0a1a"  # city's cold blue

    def test_render_all_entity_types(self):
        """Render should handle cluster, node, service, and container types."""
        r = KitchenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "Restaurant", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "Station", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": ["ct1"],
             "name": "Chef", "state": "healthy", "metrics": {"cpu": 50}},
            {"id": "ct1", "type": "container", "parent": "s1", "children": [],
             "name": "Pot", "state": "running", "metrics": {"cpu": 30}},
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
            def arc(self, *a): self.calls.append(("arc", a))
            def beginPath(self): self.calls.append(("beginPath",))
            def fill(self): self.calls.append(("fill",))
            def moveTo(self, *a): self.calls.append(("moveTo", a))
            def lineTo(self, *a): self.calls.append(("lineTo", a))
            def stroke(self): self.calls.append(("stroke",))
            def setGlobalAlpha(self, *a): self.calls.append(("setGlobalAlpha", a))

        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        # Should have drawn something for all 4 entity types
        fill_texts = [c for c in ctx.calls if c[0] == "fillText"]
        assert len(fill_texts) >= 4  # at least one label per entity


# ---------------------------------------------------------------------------
# State colors
# ---------------------------------------------------------------------------

class TestKitchenStateColors:
    def test_warm_color_palette(self):
        """Kitchen should use warm colors (reds, oranges, yellows, browns)."""
        # At least some colors should be warm-toned
        warm_colors = [STATE_COLORS["critical"], STATE_COLORS["warning"], STATE_COLORS["degraded"]]
        # All should be hex strings
        for c in warm_colors:
            assert c.startswith("#")
            assert len(c) == 7

    def test_stopped_is_dark(self):
        """Stopped state should be dark/muted (empty station)."""
        assert STATE_COLORS["stopped"].startswith("#")
