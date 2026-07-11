"""Tests for FactoryRenderer metaphor — assembly line visualization."""
import pytest
from engine.metaphors.factory import FactoryRenderer, STATE_COLORS


class TestFactoryRendererLayout:
    def test_compute_layout_returns_dict(self):
        r = FactoryRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Factory A", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "Line 1", "state": "running",
             "parent": "c1", "children": ["s1"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "Press", "state": "healthy",
             "parent": "n1", "children": ["ct1"], "metrics": {"cpu": 50}},
            {"id": "ct1", "type": "container", "name": "Belt A", "state": "running",
             "parent": "s1", "children": [], "metrics": {}},
        ]
        layout = r.compute_layout(entities, 1000, 600)
        assert isinstance(layout, dict)
        assert "c1" in layout
        assert "n1" in layout
        assert "s1" in layout
        assert "ct1" in layout

    def test_linear_assembly_arrangement(self):
        """Services (machines) should be arranged left-to-right in assembly line order."""
        r = FactoryRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Factory", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "Line", "state": "running",
             "parent": "c1", "children": ["s1", "s2", "s3"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "M1", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"cpu": 30}},
            {"id": "s2", "type": "service", "name": "M2", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"cpu": 50}},
            {"id": "s3", "type": "service", "name": "M3", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"cpu": 70}},
        ]
        layout = r.compute_layout(entities, 1000, 600)
        # Machines should be arranged left to right
        assert layout["s1"]["x"] < layout["s2"]["x"] < layout["s3"]["x"]

    def test_machine_size_scales_with_cpu(self):
        """Machine (service) visual height should scale with CPU usage."""
        r = FactoryRenderer()
        base_cluster = {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
                        "name": "F", "state": "healthy", "metrics": {}}
        base_node = {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
                     "name": "L", "state": "running", "metrics": {}}

        entities_low = [base_cluster.copy(), base_node.copy(),
                        {"id": "s1", "type": "service", "parent": "n1", "children": [],
                         "name": "low", "state": "healthy", "metrics": {"cpu": 10}}]
        entities_high = [base_cluster.copy(), base_node.copy(),
                         {"id": "s1", "type": "service", "parent": "n1", "children": [],
                          "name": "high", "state": "healthy", "metrics": {"cpu": 90}}]

        layout_low = r.compute_layout(entities_low, 1000, 600)
        layout_high = r.compute_layout(entities_high, 1000, 600)
        assert layout_high["s1"]["h"] > layout_low["s1"]["h"]

    def test_empty_entities(self):
        r = FactoryRenderer()
        layout = r.compute_layout([], 800, 600)
        assert layout == {}

    def test_hit_test(self):
        r = FactoryRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": [],
             "name": "F", "state": "healthy", "metrics": {}},
        ]
        r.compute_layout(entities, 800, 600)
        assert r.hit_test({"id": "c1"}, 100, 100) is True
        assert r.hit_test({"id": "c1"}, 9999, 9999) is False

    def test_hit_test_missing_entity(self):
        r = FactoryRenderer()
        r.compute_layout([], 800, 600)
        assert r.hit_test({"id": "missing"}, 0, 0) is False


class TestFactoryRendererTooltip:
    def test_tooltip_includes_name_and_state(self):
        r = FactoryRenderer()
        entity = {"id": "s1", "name": "Press", "type": "service", "state": "healthy", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Press" in tip
        assert "healthy" in tip

    def test_tooltip_includes_cpu_as_gear_speed(self):
        r = FactoryRenderer()
        entity = {"id": "s1", "name": "Press", "type": "service", "state": "healthy",
                  "metrics": {"cpu": 75}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "75" in tip

    def test_tooltip_includes_throughput(self):
        r = FactoryRenderer()
        entity = {"id": "s1", "name": "Belt", "type": "container", "state": "running",
                  "metrics": {"throughput": 42}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "42" in tip

    def test_tooltip_includes_bottleneck_warning(self):
        r = FactoryRenderer()
        entity = {"id": "s1", "name": "Press", "type": "service", "state": "critical",
                  "metrics": {"cpu": 95, "queue_depth": 20}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "bottleneck" in tip.lower() or "critical" in tip.lower()


class TestFactoryRendererConfig:
    def test_config_has_required_keys(self):
        r = FactoryRenderer()
        cfg = r.config()
        assert cfg["name"] == "factory"
        assert "description" in cfg
        assert "state_colors" in cfg
        assert "mappings" in cfg

    def test_config_mappings(self):
        r = FactoryRenderer()
        cfg = r.config()
        assert cfg["mappings"]["cluster"] == "factory_floor"
        assert cfg["mappings"]["node"] == "workstation"
        assert cfg["mappings"]["service"] == "machine"
        assert cfg["mappings"]["container"] == "conveyor_belt"


class TestFactoryRendererRender:
    def test_render_calls_context_methods(self):
        r = FactoryRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "Factory A", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "Line 1", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": ["ct1"],
             "name": "Press", "state": "healthy", "metrics": {"cpu": 60}},
            {"id": "ct1", "type": "container", "parent": "s1", "children": [],
             "name": "Belt A", "state": "running", "metrics": {}},
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
            def closePath(self): self.calls.append(("closePath",))
            def fill(self): self.calls.append(("fill",))
            def stroke(self): self.calls.append(("stroke",))
            def save(self): self.calls.append(("save",))
            def restore(self): self.calls.append(("restore",))
            def translate(self, *a): self.calls.append(("translate", a))
            def rotate(self, *a): self.calls.append(("rotate", a))

        ctx = MockCtx()
        r.render(entities, ctx, 1000, 600)
        assert len(ctx.calls) > 0
        assert any(c[0] == "fillRect" for c in ctx.calls)

    def test_render_steampunk_colors(self):
        """Factory should use warm metal/copper/brass palette."""
        r = FactoryRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": [],
             "name": "Factory", "state": "healthy", "metrics": {}},
        ]

        class MockCtx:
            def __init__(self):
                self.colors = []
            def fillStyle(self, c): self.colors.append(c)
            def fillRect(self, *a): pass
            def strokeStyle(self, c): self.colors.append(c)
            def strokeRect(self, *a): pass
            def lineWidth(self, w): pass
            def font(self, f): pass
            def fillText(self, *a): pass
            def arc(self, *a): pass
            def beginPath(self): pass
            def closePath(self): pass
            def fill(self): pass
            def stroke(self): pass

        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        # Should use copper/brass tones, not cool blues
        copper_tones = ["#b87333", "#cd7f32", "#8b4513", "#d4a574", "#704214"]
        used_copper = any(any(tone in c for tone in copper_tones) for c in ctx.colors if isinstance(c, str))
        assert used_copper, f"Expected copper/brass tones, got {ctx.colors}"


class TestFactoryBottleneck:
    def test_bottleneck_detection_high_cpu(self):
        r = FactoryRenderer()
        entity = {"id": "s1", "type": "service", "name": "Press", "state": "warning",
                  "metrics": {"cpu": 90, "queue_depth": 15}}
        is_bottleneck = r.is_bottleneck(entity)
        assert is_bottleneck is True

    def test_no_bottleneck_normal_load(self):
        r = FactoryRenderer()
        entity = {"id": "s1", "type": "service", "name": "Press", "state": "healthy",
                  "metrics": {"cpu": 30, "queue_depth": 2}}
        is_bottleneck = r.is_bottleneck(entity)
        assert is_bottleneck is False


class TestFactoryThroughput:
    def test_throughput_counter(self):
        r = FactoryRenderer()
        entities = [
            {"id": "s1", "type": "service", "name": "Press", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"throughput": 120}},
        ]
        throughput = r.compute_throughput(entities)
        assert throughput == 120

    def test_throughput_aggregates_multiple(self):
        r = FactoryRenderer()
        entities = [
            {"id": "s1", "type": "service", "name": "M1", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"throughput": 50}},
            {"id": "s2", "type": "service", "name": "M2", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"throughput": 30}},
        ]
        throughput = r.compute_throughput(entities)
        assert throughput == 80
