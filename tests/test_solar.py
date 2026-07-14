"""Tests for SolarRenderer metaphor — Cluster=Galaxy, Node=Star System, Service=Planet, Container=Moon."""
import math
import pytest
from engine.metaphors.solar import SolarRenderer, STATE_COLORS


class TestSolarRendererLayout:
    def test_compute_layout_returns_dict(self):
        r = SolarRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Galaxy-1", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "Star-1", "state": "running",
             "parent": "c1", "children": ["s1"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "Planet-1", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"mem": 50, "cpu": 30}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert isinstance(layout, dict)
        assert "c1" in layout
        assert "n1" in layout
        assert "s1" in layout

    def test_planet_size_scales_with_memory(self):
        r = SolarRenderer()
        base_cluster = {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
                        "name": "G", "state": "healthy", "metrics": {}}
        base_node = {"id": "n1", "type": "node", "parent": "c1", "children": ["s1", "s2"],
                     "name": "S", "state": "running", "metrics": {}}

        entities = [base_cluster.copy(), base_node.copy(),
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "small", "state": "healthy", "metrics": {"mem": 10, "cpu": 20}},
            {"id": "s2", "type": "service", "parent": "n1", "children": [],
             "name": "large", "state": "healthy", "metrics": {"mem": 90, "cpu": 20}}]

        layout = r.compute_layout(entities, 800, 600)
        # Planet with more memory should have larger radius
        assert layout["s2"]["radius"] > layout["s1"]["radius"]

    def test_planet_glow_scales_with_cpu(self):
        r = SolarRenderer()
        base_cluster = {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
                        "name": "G", "state": "healthy", "metrics": {}}
        base_node = {"id": "n1", "type": "node", "parent": "c1", "children": ["s1", "s2"],
                     "name": "S", "state": "running", "metrics": {}}

        entities = [base_cluster.copy(), base_node.copy(),
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "low-cpu", "state": "healthy", "metrics": {"mem": 50, "cpu": 10}},
            {"id": "s2", "type": "service", "parent": "n1", "children": [],
             "name": "high-cpu", "state": "healthy", "metrics": {"mem": 50, "cpu": 90}}]

        layout = r.compute_layout(entities, 800, 600)
        assert layout["s2"]["glow"] > layout["s1"]["glow"]

    def test_orbital_radius_increases_with_index(self):
        r = SolarRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "G", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1", "s2", "s3"],
             "name": "S", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "p1", "state": "healthy", "metrics": {"mem": 30, "cpu": 20}},
            {"id": "s2", "type": "service", "parent": "n1", "children": [],
             "name": "p2", "state": "healthy", "metrics": {"mem": 30, "cpu": 20}},
            {"id": "s3", "type": "service", "parent": "n1", "children": [],
             "name": "p3", "state": "healthy", "metrics": {"mem": 30, "cpu": 20}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        # Orbital radii should increase for each subsequent planet
        assert layout["s2"]["orbit"] > layout["s1"]["orbit"]
        assert layout["s3"]["orbit"] > layout["s2"]["orbit"]

    def test_moon_orbits_service(self):
        r = SolarRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "G", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "S", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": ["ct1"],
             "name": "Planet", "state": "healthy", "metrics": {"mem": 50, "cpu": 30}},
            {"id": "ct1", "type": "container", "parent": "s1", "children": [],
             "name": "Moon", "state": "running", "metrics": {}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert "ct1" in layout
        assert layout["ct1"]["orbit_parent"] == "s1"

    def test_empty_entities(self):
        r = SolarRenderer()
        layout = r.compute_layout([], 800, 600)
        assert layout == {}


class TestSolarRendererHitTest:
    def test_hit_test_planet(self):
        r = SolarRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "G", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "S", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "P", "state": "healthy", "metrics": {"mem": 50, "cpu": 30}},
        ]
        r.compute_layout(entities, 800, 600)
        pos = r._layout["s1"]
        # Center of planet should hit
        assert r.hit_test({"id": "s1"}, pos["x"], pos["y"]) is True
        # Far away should miss
        assert r.hit_test({"id": "s1"}, 0, 0) is False

    def test_hit_test_missing_entity(self):
        r = SolarRenderer()
        r.compute_layout([], 800, 600)
        assert r.hit_test({"id": "missing"}, 0, 0) is False


class TestSolarRendererTooltip:
    def test_tooltip_includes_name_and_state(self):
        r = SolarRenderer()
        entity = {"id": "s1", "name": "api-planet", "type": "service",
                  "state": "healthy", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "api-planet" in tip
        assert "healthy" in tip

    def test_tooltip_includes_metrics(self):
        r = SolarRenderer()
        entity = {"id": "s1", "name": "api", "type": "service", "state": "healthy",
                  "metrics": {"cpu": 42, "mem": 77}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "42" in tip
        assert "77" in tip

    def test_tooltip_shows_mapping(self):
        r = SolarRenderer()
        entity = {"id": "s1", "name": "web", "type": "service", "state": "running",
                  "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Planet" in tip


class TestSolarRendererConfig:
    def test_config_has_required_keys(self):
        r = SolarRenderer()
        cfg = r.config()
        assert cfg["name"] == "solar"
        assert "description" in cfg
        assert "state_colors" in cfg
        assert "mappings" in cfg
        assert cfg["mappings"]["cluster"] == "galaxy"
        assert cfg["mappings"]["node"] == "star_system"
        assert cfg["mappings"]["service"] == "planet"
        assert cfg["mappings"]["container"] == "moon"


class TestSolarRendererRender:
    def test_render_calls_context_methods(self):
        r = SolarRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "Galaxy", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "Star", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "Planet", "state": "healthy", "metrics": {"mem": 60, "cpu": 40}},
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
            def fill(self): self.calls.append(("fill",))
            def stroke(self): self.calls.append(("stroke",))
            def closePath(self): self.calls.append(("closePath",))
            def save(self): self.calls.append(("save",))
            def restore(self): self.calls.append(("restore",))
            def createRadialGradient(self, *a): 
                self.calls.append(("createRadialGradient", a))
                return MockGradient()
            def createLinearGradient(self, *a):
                self.calls.append(("createLinearGradient", a))
                return MockGradient()
            def moveTo(self, *a): self.calls.append(("moveTo", a))
            def lineTo(self, *a): self.calls.append(("lineTo", a))
            def setLineDash(self, *a): self.calls.append(("setLineDash", a))
            def translate(self, *a): self.calls.append(("translate", a))
            def rotate(self, *a): self.calls.append(("rotate", a))
            def ellipse(self, *a): self.calls.append(("ellipse", a))
            def clip(self): self.calls.append(("clip",))
            def shadowColor(self, *a): self.calls.append(("shadowColor", a))
            def shadowBlur(self, *a): self.calls.append(("shadowBlur", a))
            def shadowColor(self, *a): self.calls.append(("shadowColor", a))
            def shadowBlur(self, *a): self.calls.append(("shadowBlur", a))

        class MockGradient:
            def addColorStop(self, *a): pass

        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        assert len(ctx.calls) > 0
        # Should draw background, orbital paths, planets
        assert any(c[0] == "fillRect" for c in ctx.calls)
        assert any(c[0] == "arc" for c in ctx.calls)


class TestSolarRendererVisualEffects:
    def test_asteroid_traffic_for_requests(self):
        """Services with req_per_sec should generate asteroid positions."""
        r = SolarRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "G", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "S", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "busy", "state": "healthy",
             "metrics": {"mem": 50, "cpu": 30, "req_per_sec": 100}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert "asteroids" in layout["s1"]
        assert len(layout["s1"]["asteroids"]) > 0

    def test_solar_flare_for_errors(self):
        """Services with high error_rate should have solar flare data."""
        r = SolarRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "G", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "S", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "errorful", "state": "critical",
             "metrics": {"mem": 50, "cpu": 30, "error_rate": 0.15}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert layout["s1"].get("flare") is True

    def test_aurora_for_healthy_services(self):
        """Healthy services should have aurora effect data."""
        r = SolarRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "G", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "S", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "healthy-planet", "state": "healthy",
             "metrics": {"mem": 50, "cpu": 30}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert layout["s1"].get("aurora") is True

    def test_collision_warning_for_critical(self):
        """Critical state services should have collision warning flag."""
        r = SolarRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "G", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "S", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "critical-planet", "state": "critical",
             "metrics": {"mem": 50, "cpu": 30}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert layout["s1"].get("collision_warning") is True

    def test_gravity_lines_for_dependencies(self):
        """Entities with dependencies should have gravity line data."""
        r = SolarRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "G", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1", "s2"],
             "name": "S", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "api", "state": "healthy",
             "metrics": {"mem": 50, "cpu": 30},
             "labels": {"depends_on": "s2"}},
            {"id": "s2", "type": "service", "parent": "n1", "children": [],
             "name": "db", "state": "healthy",
             "metrics": {"mem": 50, "cpu": 30}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert "gravity_lines" in layout["s1"]
        assert "s2" in layout["s1"]["gravity_lines"]
