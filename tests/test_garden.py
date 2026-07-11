"""Tests for GardenRenderer metaphor — organic growth visualization."""
import pytest
from engine.metaphors.garden import GardenRenderer, HEALTH_COLORS, SUN_COLORS


class TestGardenRendererLayout:
    def test_compute_layout_returns_dict(self):
        r = GardenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Garden", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "Bed-1", "state": "running",
             "parent": "c1", "children": ["s1"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "Rose", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"cpu": 50}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert isinstance(layout, dict)
        assert "c1" in layout
        assert "n1" in layout
        assert "s1" in layout

    def test_plant_height_scales_with_cpu(self):
        """Plants grow taller with higher CPU usage."""
        r = GardenRenderer()
        base_cluster = {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "G", "state": "healthy", "metrics": {}}
        base_node = {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "B", "state": "running", "metrics": {}}

        entities_low = [base_cluster.copy(), base_node.copy(),
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "low", "state": "healthy", "metrics": {"cpu": 10}}]
        entities_high = [base_cluster.copy(), base_node.copy(),
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "high", "state": "healthy", "metrics": {"cpu": 90}}]

        layout_low = r.compute_layout(entities_low, 800, 600)
        layout_high = r.compute_layout(entities_high, 800, 600)
        assert layout_high["s1"]["h"] > layout_low["s1"]["h"]

    def test_organic_spacing(self):
        """compute_layout produces non-overlapping positions for sibling nodes."""
        r = GardenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1", "n2"],
             "name": "G", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1", "s2"],
             "name": "B1", "state": "running", "metrics": {}},
            {"id": "n2", "type": "node", "parent": "c1", "children": ["s3"],
             "name": "B2", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "P1", "state": "healthy", "metrics": {"cpu": 40}},
            {"id": "s2", "type": "service", "parent": "n1", "children": [],
             "name": "P2", "state": "healthy", "metrics": {"cpu": 60}},
            {"id": "s3", "type": "service", "parent": "n2", "children": [],
             "name": "P3", "state": "healthy", "metrics": {"cpu": 30}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        # Nodes are stacked vertically within same cluster — check no vertical overlap
        n1_pos = layout["n1"]
        n2_pos = layout["n2"]
        assert n1_pos["y"] + n1_pos["h"] <= n2_pos["y"] + 1  # 1px tolerance

    def test_hit_test(self):
        r = GardenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": [],
             "name": "G", "state": "healthy", "metrics": {}},
        ]
        r.compute_layout(entities, 800, 600)
        assert r.hit_test({"id": "c1"}, 100, 100) is True
        assert r.hit_test({"id": "c1"}, 9999, 9999) is False

    def test_hit_test_missing_entity(self):
        r = GardenRenderer()
        r.compute_layout([], 800, 600)
        assert r.hit_test({"id": "missing"}, 0, 0) is False

    def test_empty_entities(self):
        r = GardenRenderer()
        layout = r.compute_layout([], 800, 600)
        assert layout == {}


class TestGardenRendererTooltip:
    def test_tooltip_includes_name_and_state(self):
        r = GardenRenderer()
        entity = {"id": "s1", "name": "Rose", "type": "service", "state": "healthy", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Rose" in tip
        assert "healthy" in tip

    def test_tooltip_includes_metrics(self):
        r = GardenRenderer()
        entity = {"id": "s1", "name": "api", "type": "service", "state": "healthy",
                  "metrics": {"cpu": 42, "mem": 77}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "42" in tip
        assert "77" in tip

    def test_tooltip_for_container(self):
        r = GardenRenderer()
        entity = {"id": "ct1", "name": "branch-1", "type": "container", "state": "running",
                  "metrics": {"cpu": 30}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "branch-1" in tip


class TestGardenRendererConfig:
    def test_config_has_required_keys(self):
        r = GardenRenderer()
        cfg = r.config()
        assert cfg["name"] == "garden"
        assert "description" in cfg
        assert "state_colors" in cfg
        assert "mappings" in cfg
        assert cfg["mappings"]["cluster"] == "garden bed"
        assert cfg["mappings"]["node"] == "planting row"
        assert cfg["mappings"]["service"] == "plant"
        assert cfg["mappings"]["container"] == "branch"

    def test_health_color_mapping(self):
        """Leaf colors: green=healthy, yellow=warning, brown=critical."""
        assert "healthy" in HEALTH_COLORS
        assert "warning" in HEALTH_COLORS
        assert "critical" in HEALTH_COLORS
        # green-ish for healthy
        assert "4ade80" in HEALTH_COLORS["healthy"] or "22c55e" in HEALTH_COLORS["healthy"]
        # yellow-ish for warning
        assert "fbbf24" in HEALTH_COLORS["warning"] or "eab308" in HEALTH_COLORS["warning"]
        # brown-ish for critical
        assert "92400e" in HEALTH_COLORS["critical"] or "78350f" in HEALTH_COLORS["critical"]


class TestGardenRendererRender:
    def _make_ctx(self):
        """Create a MockCtx with all canvas methods used by GardenRenderer."""
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
            def fill(self): self.calls.append(("fill",))
            def moveTo(self, *a): self.calls.append(("moveTo", a))
            def lineTo(self, *a): self.calls.append(("lineTo", a))
            def stroke(self): self.calls.append(("stroke",))
            def closePath(self): self.calls.append(("closePath",))
            def save(self): self.calls.append(("save",))
            def restore(self): self.calls.append(("restore",))
            def globalAlpha(self, a): self.calls.append(("globalAlpha", a))
        return MockCtx()

    def test_render_calls_context_methods(self):
        r = GardenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "Garden", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "Bed-1", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "Rose", "state": "healthy", "metrics": {"cpu": 60}},
        ]
        ctx = self._make_ctx()
        r.render(entities, ctx, 800, 600)
        assert len(ctx.calls) > 0
        assert any(c[0] == "fillRect" for c in ctx.calls)

    def test_render_draws_sun_for_cluster_health(self):
        """Sun/light source represents overall cluster health."""
        r = GardenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": [],
             "name": "Garden", "state": "healthy", "metrics": {}},
        ]
        ctx = self._make_ctx()
        r.render(entities, ctx, 800, 600)
        assert any(c[0] == "arc" for c in ctx.calls)

    def test_render_idle_dew_drops(self):
        """Idle services get dew drops."""
        r = GardenRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "G", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "B", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "Idle", "state": "idle", "metrics": {"cpu": 2}},
        ]
        ctx = self._make_ctx()
        r.render(entities, ctx, 800, 600)
        arc_calls = [c for c in ctx.calls if c[0] == "arc"]
        assert len(arc_calls) > 0
