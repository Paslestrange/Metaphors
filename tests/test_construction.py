"""Tests for ConstructionRenderer metaphor."""
import pytest
from engine.metaphors.construction import ConstructionRenderer, STATE_COLORS


class TestConstructionRendererLayout:
    def test_compute_layout_returns_dict(self):
        r = ConstructionRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Tower A", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "Floor 1", "state": "running",
             "parent": "c1", "children": ["s1"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "Office", "state": "healthy",
             "parent": "n1", "children": ["ct1"], "metrics": {"cpu": 50}},
            {"id": "ct1", "type": "container", "name": "North Wall", "state": "healthy",
             "parent": "s1", "children": [], "metrics": {}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert isinstance(layout, dict)
        assert "c1" in layout
        assert "n1" in layout
        assert "s1" in layout
        assert "ct1" in layout

    def test_vertical_building_layout(self):
        """Nodes (floors) should stack vertically."""
        r = ConstructionRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1", "n2"],
             "name": "Project", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": [],
             "name": "Floor 1", "state": "running", "metrics": {}},
            {"id": "n2", "type": "node", "parent": "c1", "children": [],
             "name": "Floor 2", "state": "running", "metrics": {}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        # Floor 2 should be above Floor 1 (lower y value)
        assert layout["n2"]["y"] < layout["n1"]["y"]

    def test_floor_height_scales_with_cpu(self):
        r = ConstructionRenderer()
        base_cluster = {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "P", "state": "healthy", "metrics": {}}
        base_node = {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "N", "state": "running", "metrics": {}}

        entities_low = [base_cluster.copy(), base_node.copy(),
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "low", "state": "healthy", "metrics": {"cpu": 10}}]
        entities_high = [base_cluster.copy(), base_node.copy(),
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "high", "state": "healthy", "metrics": {"cpu": 90}}]

        layout_low = r.compute_layout(entities_low, 800, 600)
        layout_high = r.compute_layout(entities_high, 800, 600)
        # Higher CPU = more complete floor = taller room
        assert layout_high["s1"]["h"] > layout_low["s1"]["h"]

    def test_hit_test(self):
        r = ConstructionRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": [],
             "name": "P", "state": "healthy", "metrics": {}},
        ]
        r.compute_layout(entities, 800, 600)
        assert r.hit_test({"id": "c1"}, 100, 100) is True
        assert r.hit_test({"id": "c1"}, 9999, 9999) is False

    def test_hit_test_missing_entity(self):
        r = ConstructionRenderer()
        r.compute_layout([], 800, 600)
        assert r.hit_test({"id": "missing"}, 0, 0) is False


class TestConstructionRendererTooltip:
    def test_tooltip_includes_name_and_state(self):
        r = ConstructionRenderer()
        entity = {"id": "s1", "name": "Office", "type": "service", "state": "healthy", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Office" in tip
        assert "healthy" in tip

    def test_tooltip_includes_metrics(self):
        r = ConstructionRenderer()
        entity = {"id": "s1", "name": "Office", "type": "service", "state": "healthy",
                  "metrics": {"cpu": 42, "mem": 77}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "42" in tip
        assert "77" in tip

    def test_tooltip_construction_theme(self):
        r = ConstructionRenderer()
        entity = {"id": "n1", "name": "Floor 3", "type": "node", "state": "warning",
                  "metrics": {"cpu": 85}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Floor 3" in tip
        # Should have construction-themed info
        assert "warning" in tip or "85" in tip


class TestConstructionRendererConfig:
    def test_config_has_required_keys(self):
        r = ConstructionRenderer()
        cfg = r.config()
        assert cfg["name"] == "construction"
        assert "description" in cfg
        assert "state_colors" in cfg
        assert "mappings" in cfg
        assert cfg["mappings"]["cluster"] == "building project"
        assert cfg["mappings"]["node"] == "floor"
        assert cfg["mappings"]["service"] == "room"
        assert cfg["mappings"]["container"] == "wall section"


class TestConstructionRendererRender:
    def test_render_calls_context_methods(self):
        r = ConstructionRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "Tower A", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "Floor 1", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": ["ct1"],
             "name": "Office", "state": "healthy", "metrics": {"cpu": 60}},
            {"id": "ct1", "type": "container", "parent": "s1", "children": [],
             "name": "North Wall", "state": "healthy", "metrics": {}},
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
            def moveTo(self, *a): self.calls.append(("moveTo", a))
            def lineTo(self, *a): self.calls.append(("lineTo", a))
            def stroke(self): self.calls.append(("stroke",))
            def arc(self, *a): self.calls.append(("arc", a))
            def fill(self): self.calls.append(("fill",))

        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        assert len(ctx.calls) > 0
        assert any(c[0] == "fillRect" for c in ctx.calls)

    def test_render_blueprint_background(self):
        """Should render blue blueprint background."""
        r = ConstructionRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": [],
             "name": "Project", "state": "healthy", "metrics": {}},
        ]

        class MockCtx:
            def __init__(self):
                self.fill_colors = []
            def fillStyle(self, c): self.fill_colors.append(c)
            def fillRect(self, *a): pass
            def strokeStyle(self, c): pass
            def strokeRect(self, *a): pass
            def lineWidth(self, w): pass
            def font(self, f): pass
            def fillText(self, *a): pass
            def beginPath(self): pass
            def moveTo(self, *a): pass
            def lineTo(self, *a): pass
            def stroke(self): pass
            def arc(self, *a): pass
            def fill(self): pass

        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        # First fill should be blueprint blue
        assert len(ctx.fill_colors) > 0
        assert ctx.fill_colors[0] == "#1e3a5f"  # Blueprint blue

    def test_render_warning_state(self):
        """Warning state should render safety signs."""
        r = ConstructionRenderer()
        entities = [
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "Room", "state": "warning", "metrics": {"cpu": 80}},
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
            def moveTo(self, *a): self.calls.append(("moveTo", a))
            def lineTo(self, *a): self.calls.append(("lineTo", a))
            def stroke(self): self.calls.append(("stroke",))
            def arc(self, *a): self.calls.append(("arc", a))
            def fill(self): self.calls.append(("fill",))

        ctx = MockCtx()
        r.compute_layout(entities, 800, 600)
        r.render(entities, ctx, 800, 600)
        # Should have warning-related rendering
        assert len(ctx.calls) > 0
