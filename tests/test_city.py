"""Tests for CityRenderer metaphor."""
import pytest
from engine.metaphors.city import CityRenderer, STATE_COLORS


class TestCityRendererLayout:
    def test_compute_layout_returns_dict(self):
        r = CityRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Prod", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "node-1", "state": "running",
             "parent": "c1", "children": ["s1"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "api", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"cpu": 50}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert isinstance(layout, dict)
        assert "c1" in layout
        assert "n1" in layout
        assert "s1" in layout

    def test_building_height_scales_with_cpu(self):
        r = CityRenderer()
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
        assert layout_high["s1"]["h"] > layout_low["s1"]["h"]

    def test_hit_test(self):
        r = CityRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": [],
             "name": "P", "state": "healthy", "metrics": {}},
        ]
        r.compute_layout(entities, 800, 600)
        assert r.hit_test({"id": "c1"}, 100, 100) is True
        assert r.hit_test({"id": "c1"}, 9999, 9999) is False

    def test_hit_test_missing_entity(self):
        r = CityRenderer()
        r.compute_layout([], 800, 600)
        assert r.hit_test({"id": "missing"}, 0, 0) is False


class TestCityRendererTooltip:
    def test_tooltip_includes_name_and_state(self):
        r = CityRenderer()
        entity = {"id": "s1", "name": "api", "type": "service", "state": "healthy", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "api" in tip
        assert "healthy" in tip

    def test_tooltip_includes_metrics(self):
        r = CityRenderer()
        entity = {"id": "s1", "name": "api", "type": "service", "state": "healthy",
                  "metrics": {"cpu": 42, "mem": 77}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "42" in tip
        assert "77" in tip


class TestCityRendererConfig:
    def test_config_has_required_keys(self):
        r = CityRenderer()
        cfg = r.config()
        assert cfg["name"] == "city"
        assert "description" in cfg
        assert "state_colors" in cfg
        assert "mappings" in cfg
        assert cfg["mappings"]["cluster"] == "district"
        assert cfg["mappings"]["service"] == "building"


class TestCityRendererRender:
    def test_render_calls_context_methods(self):
        r = CityRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "Prod", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "node-1", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "api", "state": "healthy", "metrics": {"cpu": 60}},
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
        assert len(ctx.calls) > 0
        assert any(c[0] == "fillRect" for c in ctx.calls)
