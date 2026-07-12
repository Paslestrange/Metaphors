"""Tests for SpaceStationRenderer metaphor — full visual overhaul."""
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


class MockCtx:
    """Mock canvas rendering context that records all calls."""
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
    def translate(self, *a): self.calls.append(("translate", a))
    def rotate(self, *a): self.calls.append(("rotate", a))
    def clip(self): self.calls.append(("clip",))
    def setLineDash(self, *a): self.calls.append(("setLineDash", a))


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
        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        # Stars are small filled rects in the background
        fill_calls = [c for c in ctx.calls if c[0] == "fillRect"]
        assert len(fill_calls) > 1  # At least background + some stars

    def test_render_generates_star_layers(self):
        """Renderer should generate 3-layer parallax star field."""
        r = SpaceStationRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Ring", "state": "healthy",
             "parent": None, "children": [], "metrics": {}},
        ]
        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        assert len(r._star_layers) == 3
        assert len(r._star_layers[0]) > 0  # distant stars
        assert len(r._star_layers[1]) > 0  # mid stars
        assert len(r._star_layers[2]) > 0  # close stars

    def test_render_generates_debris(self):
        """Renderer should generate floating debris particles."""
        r = SpaceStationRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Ring", "state": "healthy",
             "parent": None, "children": [], "metrics": {}},
        ]
        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        assert len(r._debris) > 0

    def test_render_draws_corridors(self):
        """Modules should be connected to hub via corridors."""
        r = SpaceStationRenderer()
        entities = _make_entities()
        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        # Corridors use moveTo + lineTo
        move_calls = [c for c in ctx.calls if c[0] == "moveTo"]
        line_calls = [c for c in ctx.calls if c[0] == "lineTo"]
        assert len(move_calls) > 0
        assert len(line_calls) > 0

    def test_render_draws_solar_panels(self):
        """Modules should have solar panels extending from them."""
        r = SpaceStationRenderer()
        entities = _make_entities()
        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        # Solar panels use save/restore/translate/rotate
        save_calls = [c for c in ctx.calls if c[0] == "save"]
        translate_calls = [c for c in ctx.calls if c[0] == "translate"]
        rotate_calls = [c for c in ctx.calls if c[0] == "rotate"]
        assert len(save_calls) > 0
        assert len(translate_calls) > 0
        assert len(rotate_calls) > 0

    def test_render_draws_docking_rings(self):
        """Services should have docking port rings."""
        r = SpaceStationRenderer()
        entities = _make_entities()
        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        # Multiple arc calls for docking rings
        arc_calls = [c for c in ctx.calls if c[0] == "arc"]
        assert len(arc_calls) > 5  # hub + modules + pods + effects

    def test_render_draws_led_indicators(self):
        """Modules should have LED-style life support indicators."""
        r = SpaceStationRenderer()
        entities = _make_entities()
        layout = r.compute_layout(entities, 800, 600)
        # Modules should have LED data
        assert "led_power" in layout["n1"]
        assert "led_data" in layout["n1"]
        assert "led_env" in layout["n1"]

    def test_render_draws_control_panels(self):
        """Hub and modules should have control panel glow."""
        r = SpaceStationRenderer()
        entities = _make_entities()
        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        # Control panels use fillRect for screens
        fill_rect_calls = [c for c in ctx.calls if c[0] == "fillRect"]
        assert len(fill_rect_calls) > 10  # background + stars + panels + compartments

    def test_render_emergency_lighting_for_critical(self):
        """Critical entities should trigger emergency lighting."""
        r = SpaceStationRenderer()
        entities = _make_entities()
        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        # Emergency lighting adds extra arc calls for pulse rings
        # ct2 is critical, so we should see extra arcs
        arc_calls = [c for c in ctx.calls if c[0] == "arc"]
        assert len(arc_calls) > 10  # many arcs from emergency pulses


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

    def test_breach_renders_sparks(self):
        """Critical entities should render spark effects."""
        r = SpaceStationRenderer()
        entities = _make_entities()
        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        # Breach sparks use moveTo/lineTo for spark lines
        # We already have corridors, but breach adds more
        move_calls = [c for c in ctx.calls if c[0] == "moveTo"]
        assert len(move_calls) > 5  # corridors + breach sparks


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

    def test_docking_color_green_when_available(self):
        """Low-traffic ports should show green (available) docking ring."""
        r = SpaceStationRenderer()
        entities = [
            {"id": "s1", "type": "service", "parent": None, "children": [],
             "name": "free", "state": "healthy", "metrics": {"req_per_sec": 2}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert layout["s1"]["docking_color"] == "#00ff88"
        assert layout["s1"]["docking_available"] is True

    def test_docking_color_red_when_occupied(self):
        """High-traffic ports should show red (occupied) docking ring."""
        r = SpaceStationRenderer()
        entities = [
            {"id": "s1", "type": "service", "parent": None, "children": [],
             "name": "busy", "state": "healthy", "metrics": {"req_per_sec": 50}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert layout["s1"]["docking_color"] == "#ff2222"
        assert layout["s1"]["docking_available"] is False


class TestSpaceStationShuttleTraffic:
    def test_shuttle_count_scales_with_requests(self):
        """Higher req_per_sec should produce more shuttle traffic."""
        r = SpaceStationRenderer()
        entities_low = [
            {"id": "s1", "type": "service", "parent": None, "children": [],
             "name": "low", "state": "healthy", "metrics": {"req_per_sec": 5}},
        ]
        entities_high = [
            {"id": "s1", "type": "service", "parent": None, "children": [],
             "name": "high", "state": "healthy", "metrics": {"req_per_sec": 50}},
        ]
        layout_low = r.compute_layout(entities_low, 800, 600)
        layout_high = r.compute_layout(entities_high, 800, 600)
        assert layout_high["s1"]["shuttle_count"] >= layout_low["s1"]["shuttle_count"]

    def test_no_requests_no_shuttles(self):
        """Zero request rate should produce no shuttle traffic."""
        r = SpaceStationRenderer()
        entities = [
            {"id": "s1", "type": "service", "parent": None, "children": [],
             "name": "idle", "state": "healthy", "metrics": {"req_per_sec": 0}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert layout["s1"]["shuttle_count"] == 0


class TestSpaceStationSolarPanels:
    def test_modules_have_solar_panel_data(self):
        """Modules should have solar panel geometry in layout."""
        r = SpaceStationRenderer()
        entities = _make_entities()
        layout = r.compute_layout(entities, 800, 600)
        assert "solar_angle" in layout["n1"]
        assert "solar_length" in layout["n1"]
        assert "solar_width" in layout["n1"]


class TestSpaceStationPowerCore:
    def test_power_core_glow_matches_cpu(self):
        """Power core glow intensity should match CPU usage."""
        r = SpaceStationRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Ring", "state": "healthy",
             "parent": None, "children": [], "metrics": {"cpu": 75}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert abs(layout["c1"]["power_glow"] - 0.75) < 0.01


class TestSpaceStationLifeSupport:
    def test_life_support_leds_present(self):
        """Modules should have 3 LED indicators."""
        r = SpaceStationRenderer()
        entities = _make_entities()
        layout = r.compute_layout(entities, 800, 600)
        assert "led_power" in layout["n1"]
        assert "led_data" in layout["n1"]
        assert "led_env" in layout["n1"]

    def test_life_support_color_matches_state(self):
        """Module life support color should match entity state."""
        r = SpaceStationRenderer()
        entities = _make_entities()
        layout = r.compute_layout(entities, 800, 600)
        # n1 is "running" → "#60a5fa"
        assert layout["n1"]["life_support_color"] == "#60a5fa"
        # n2 is "warning" → "#fbbf24"
        assert layout["n2"]["life_support_color"] == "#fbbf24"
