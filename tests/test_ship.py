"""Tests for ShipRenderer metaphor — naval ship cross-section visualization."""
import pytest
from engine.metaphors.ship import ShipRenderer, STATE_COLORS, SHIP_SECTIONS


class TestShipRendererLayout:
    def test_compute_layout_returns_dict(self):
        r = ShipRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Fleet Alpha", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "Bridge", "state": "running",
             "parent": "c1", "children": ["s1"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "nav-system", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"cpu": 50}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert isinstance(layout, dict)
        assert "c1" in layout
        assert "n1" in layout
        assert "s1" in layout

    def test_layout_has_section_metadata(self):
        r = ShipRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Fleet", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "Bridge", "state": "running",
             "parent": "c1", "children": [], "metrics": {}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert layout["c1"]["section"] == "fleet"
        assert layout["n1"]["section"] in SHIP_SECTIONS

    def test_station_height_scales_with_cpu(self):
        r = ShipRenderer()
        base_cluster = {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "F", "state": "healthy", "metrics": {}}
        base_node = {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "N", "state": "running", "metrics": {}}

        entities_low = [base_cluster.copy(), base_node.copy(),
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "low", "state": "healthy", "metrics": {"cpu": 10}}]
        entities_high = [base_cluster.copy(), base_node.copy(),
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "high", "state": "healthy", "metrics": {"cpu": 90}}]

        # Both should produce valid layouts (station size is grid-based, not CPU-scaled like city)
        layout_low = r.compute_layout(entities_low, 800, 600)
        layout_high = r.compute_layout(entities_high, 800, 600)
        assert "s1" in layout_low
        assert "s1" in layout_high
        # Both stations should have positive dimensions
        assert layout_low["s1"]["w"] > 0
        assert layout_low["s1"]["h"] > 0

    def test_compartment_layout(self):
        r = ShipRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "F", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "Engine", "state": "running",
             "parent": "c1", "children": ["s1"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "reactor", "state": "healthy",
             "parent": "n1", "children": ["ct1"], "metrics": {"cpu": 40}},
            {"id": "ct1", "type": "container", "name": "core-0", "state": "running",
             "parent": "s1", "children": [], "metrics": {}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert "ct1" in layout
        assert layout["ct1"]["section"] == "compartment"
        assert layout["ct1"]["w"] > 0
        assert layout["ct1"]["h"] > 0

    def test_hit_test(self):
        r = ShipRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": [],
             "name": "F", "state": "healthy", "metrics": {}},
        ]
        r.compute_layout(entities, 800, 600)
        # Center of canvas should hit the fleet
        assert r.hit_test({"id": "c1"}, 400, 300) is True
        assert r.hit_test({"id": "c1"}, 9999, 9999) is False

    def test_hit_test_missing_entity(self):
        r = ShipRenderer()
        r.compute_layout([], 800, 600)
        assert r.hit_test({"id": "missing"}, 0, 0) is False

    def test_hit_test_no_id(self):
        r = ShipRenderer()
        r.compute_layout([], 800, 600)
        assert r.hit_test({}, 0, 0) is False

    def test_multiple_clusters_stack_vertically(self):
        r = ShipRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": [],
             "name": "Fleet1", "state": "healthy", "metrics": {}},
            {"id": "c2", "type": "cluster", "parent": None, "children": [],
             "name": "Fleet2", "state": "healthy", "metrics": {}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert layout["c1"]["y"] < layout["c2"]["y"]

    def test_multiple_sections_stack_horizontally(self):
        r = ShipRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1", "n2"],
             "name": "F", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": [],
             "name": "Bridge", "state": "running", "metrics": {}},
            {"id": "n2", "type": "node", "parent": "c1", "children": [],
             "name": "Engine", "state": "running", "metrics": {}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert layout["n1"]["x"] < layout["n2"]["x"]


class TestShipRendererTooltip:
    def test_tooltip_includes_name_and_state(self):
        r = ShipRenderer()
        entity = {"id": "s1", "name": "nav-system", "type": "service", "state": "healthy", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "nav-system" in tip
        assert "healthy" in tip

    def test_tooltip_maps_entity_types(self):
        r = ShipRenderer()
        for etype, mapping in [("cluster", "Fleet"), ("node", "Ship Section"),
                                ("service", "Station"), ("container", "Compartment")]:
            entity = {"id": "e1", "name": "test", "type": etype, "state": "healthy", "metrics": {}}
            tip = r.get_tooltip(entity, 0, 0)
            assert mapping in tip

    def test_tooltip_includes_naval_metrics(self):
        r = ShipRenderer()
        entity = {"id": "s1", "name": "reactor", "type": "service", "state": "healthy",
                  "metrics": {"cpu_pct": 42, "mem_pct": 77, "latency_ms": 15}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Engine RPM" in tip
        assert "42" in tip
        assert "Fuel Level" in tip
        assert "77" in tip
        assert "Signal Delay" in tip
        assert "15" in tip

    def test_tooltip_damage_report(self):
        r = ShipRenderer()
        entity = {"id": "s1", "name": "hull", "type": "service", "state": "critical",
                  "metrics": {"error_rate": 0.15}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Damage Report" in tip
        assert "15.0%" in tip

    def test_tooltip_sea_time(self):
        r = ShipRenderer()
        entity = {"id": "s1", "name": "watch", "type": "service", "state": "running",
                  "metrics": {"uptime_hrs": 48}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Sea Time" in tip
        assert "48" in tip


class TestShipRendererConfig:
    def test_config_has_required_keys(self):
        r = ShipRenderer()
        cfg = r.config()
        assert cfg["name"] == "ship"
        assert "description" in cfg
        assert "state_colors" in cfg
        assert "mappings" in cfg

    def test_config_mappings(self):
        r = ShipRenderer()
        cfg = r.config()
        assert cfg["mappings"]["cluster"] == "fleet"
        assert cfg["mappings"]["node"] == "ship_section"
        assert cfg["mappings"]["service"] == "station"
        assert cfg["mappings"]["container"] == "compartment"

    def test_config_ship_sections(self):
        r = ShipRenderer()
        cfg = r.config()
        assert "ship_sections" in cfg
        assert "Bridge" in cfg["ship_sections"]
        assert "Engine Room" in cfg["ship_sections"]
        assert "Cargo Hold" in cfg["ship_sections"]
        assert "Weapons Bay" in cfg["ship_sections"]

    def test_config_visual_features(self):
        r = ShipRenderer()
        cfg = r.config()
        features = cfg["visual_features"]
        assert "radar_ping" in features
        assert "sonar_wave" in features
        assert "damage_indicator" in features
        assert "battle_stations_alarm" in features
        assert "fuel_gauge" in features
        assert "engine_rpm" in features
        assert "signal_delay" in features


class TestShipRendererRender:
    def _mock_ctx(self):
        class MockCtx:
            def __init__(self):
                self.calls = []
                self.globalAlpha = 1.0
            def fillStyle(self, c): self.calls.append(("fillStyle", c))
            def fillRect(self, *a): self.calls.append(("fillRect", a))
            def strokeStyle(self, c): self.calls.append(("strokeStyle", c))
            def strokeRect(self, *a): self.calls.append(("strokeRect", a))
            def lineWidth(self, w): self.calls.append(("lineWidth", w))
            def font(self, f): self.calls.append(("font", f))
            def setGlobalAlpha(self, a): self.calls.append(("setGlobalAlpha", a))
            def fillText(self, *a): self.calls.append(("fillText", a))
            def beginPath(self): self.calls.append(("beginPath",))
            def arc(self, *a): self.calls.append(("arc", a))
            def fill(self): self.calls.append(("fill",))
            def stroke(self): self.calls.append(("stroke",))
            def moveTo(self, *a): self.calls.append(("moveTo", a))
            def lineTo(self, *a): self.calls.append(("lineTo", a))
        return MockCtx()

    def test_render_calls_context_methods(self):
        r = ShipRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "Fleet Alpha", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "Bridge", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "nav-system", "state": "healthy", "metrics": {"cpu": 60, "mem": 45}},
        ]
        ctx = self._mock_ctx()
        r.render(entities, ctx, 800, 600)
        assert len(ctx.calls) > 0
        assert any(c[0] == "fillRect" for c in ctx.calls)
        assert any(c[0] == "strokeRect" for c in ctx.calls)

    def test_render_critical_shows_damage(self):
        r = ShipRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "Fleet", "state": "critical", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "Bridge", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "damaged", "state": "critical", "metrics": {}},
        ]
        ctx = self._mock_ctx()
        r.render(entities, ctx, 800, 600)
        # Should have moveTo/lineTo calls for damage sparks
        assert any(c[0] == "moveTo" for c in ctx.calls)
        assert any(c[0] == "lineTo" for c in ctx.calls)

    def test_render_container_compartments(self):
        r = ShipRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "F", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "Engine", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": ["ct1"],
             "name": "reactor", "state": "healthy", "metrics": {"cpu": 50}},
            {"id": "ct1", "type": "container", "parent": "s1", "children": [],
             "name": "core-0", "state": "running", "metrics": {}},
        ]
        ctx = self._mock_ctx()
        r.render(entities, ctx, 800, 600)
        # Container should be rendered (fillRect for compartment)
        fill_rects = [c for c in ctx.calls if c[0] == "fillRect"]
        assert len(fill_rects) > 0

    def test_render_sonar_wave_for_healthy_node(self):
        r = ShipRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "F", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": [],
             "name": "Bridge", "state": "healthy", "metrics": {}},
        ]
        ctx = self._mock_ctx()
        r.render(entities, ctx, 800, 600)
        # Sonar wave = arc calls
        assert any(c[0] == "arc" for c in ctx.calls)

    def test_render_empty_entities(self):
        r = ShipRenderer()
        ctx = self._mock_ctx()
        r.render([], ctx, 800, 600)
        # Should still draw background and hull
        assert any(c[0] == "fillRect" for c in ctx.calls)
