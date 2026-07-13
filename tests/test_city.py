"""Tests for CityRenderer — Neon Cyberpunk aesthetic."""
import pytest
from engine.metaphors.city import (
    CityRenderer,
    STATE_COLORS,
    NEON_GLOW,
    TrafficParticle,
    _hex_to_rgb,
    MIN_BUILDING_W,
    MAX_BUILDING_W,
    BG_COLOR,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cluster(cid="c1", children=None, state="healthy"):
    return {
        "id": cid, "type": "cluster", "name": "Prod",
        "state": state, "parent": None,
        "children": children or ["n1"], "metrics": {},
    }


def _make_node(nid="n1", parent="c1", children=None, state="running"):
    return {
        "id": nid, "type": "node", "name": "node-1",
        "state": state, "parent": parent,
        "children": children or ["s1"], "metrics": {},
    }


def _make_service(sid="s1", parent="n1", cpu=50, mem=50, state="healthy"):
    return {
        "id": sid, "type": "service", "name": "api",
        "state": state, "parent": parent,
        "children": [], "metrics": {"cpu": cpu, "mem": mem},
    }


def _basic_entities(cpu=50, mem=50, state="healthy"):
    return [
        _make_cluster(),
        _make_node(),
        _make_service(cpu=cpu, mem=mem, state=state),
    ]


class MockCtx:
    """Mock canvas context that records all drawing calls."""

    def __init__(self):
        self.calls = []

    def fillStyle(self, c):
        self.calls.append(("fillStyle", c))

    def fillRect(self, *a):
        self.calls.append(("fillRect", a))

    def strokeStyle(self, c):
        self.calls.append(("strokeStyle", c))

    def strokeRect(self, *a):
        self.calls.append(("strokeRect", a))

    def lineWidth(self, w):
        self.calls.append(("lineWidth", w))

    def font(self, f):
        self.calls.append(("font", f))

    def fillText(self, *a):
        self.calls.append(("fillText", a))

    def shadowBlur(self, v):
        self.calls.append(("shadowBlur", v))

    def shadowColor(self, c):
        self.calls.append(("shadowColor", c))

    def globalAlpha(self, v):
        self.calls.append(("globalAlpha", v))

    def beginPath(self):
        self.calls.append(("beginPath",))

    def arc(self, *a):
        self.calls.append(("arc", a))

    def fill(self):
        self.calls.append(("fill",))


# ---------------------------------------------------------------------------
# Layout tests
# ---------------------------------------------------------------------------


class TestCityLayout:
    def test_empty_entities(self):
        r = CityRenderer()
        layout = r.compute_layout([], 800, 600)
        assert layout == {}

    def test_single_cluster(self):
        r = CityRenderer()
        entities = [_make_cluster(children=[])]
        layout = r.compute_layout(entities, 800, 600)
        assert "c1" in layout
        assert layout["c1"]["w"] == 800
        assert layout["c1"]["h"] == 600

    def test_full_hierarchy(self):
        r = CityRenderer()
        entities = _basic_entities()
        layout = r.compute_layout(entities, 800, 600)
        assert "c1" in layout
        assert "n1" in layout
        assert "s1" in layout

    def test_building_height_scales_with_cpu(self):
        r = CityRenderer()
        layout_low = r.compute_layout(_basic_entities(cpu=10), 800, 600)
        layout_high = r.compute_layout(_basic_entities(cpu=90), 800, 600)
        assert layout_high["s1"]["h"] > layout_low["s1"]["h"]

    def test_building_width_scales_with_memory(self):
        r = CityRenderer()
        layout_low = r.compute_layout(_basic_entities(mem=10), 800, 600)
        layout_high = r.compute_layout(_basic_entities(mem=90), 800, 600)
        assert layout_high["s1"]["w"] > layout_low["s1"]["w"]

    def test_building_width_bounded(self):
        r = CityRenderer()
        layout = r.compute_layout(_basic_entities(mem=100), 800, 600)
        assert layout["s1"]["w"] <= MAX_BUILDING_W
        layout0 = r.compute_layout(_basic_entities(mem=0), 800, 600)
        assert layout0["s1"]["w"] >= MIN_BUILDING_W

    def test_cpu_clamped_0_100(self):
        r = CityRenderer()
        layout_neg = r.compute_layout(_basic_entities(cpu=-50), 800, 600)
        layout_over = r.compute_layout(_basic_entities(cpu=200), 800, 600)
        # Negative CPU → minimum height
        assert layout_neg["s1"]["h"] >= 15
        # Over 100 → clamped to max
        assert layout_over["s1"]["h"] <= 600

    def test_multiple_clusters(self):
        r = CityRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "A", "state": "healthy",
             "parent": None, "children": [], "metrics": {}},
            {"id": "c2", "type": "cluster", "name": "B", "state": "running",
             "parent": None, "children": [], "metrics": {}},
            {"id": "c3", "type": "cluster", "name": "C", "state": "warning",
             "parent": None, "children": [], "metrics": {}},
        ]
        layout = r.compute_layout(entities, 900, 600)
        assert len(layout) == 3
        # Each district gets 1/3 of width
        assert abs(layout["c1"]["w"] - 300) < 1
        assert abs(layout["c2"]["w"] - 300) < 1

    def test_many_entities_500(self):
        """compute_layout must handle 500 entities without error."""
        r = CityRenderer()
        entities = []
        # 1 cluster, 10 nodes, 489 services = 500
        services = []
        for i in range(489):
            sid = f"s{i}"
            services.append(sid)
            entities.append({
                "id": sid, "type": "service", "name": f"svc-{i}",
                "state": "healthy", "parent": f"n{i % 10}",
                "children": [], "metrics": {"cpu": i % 100, "mem": 50},
            })
        for i in range(10):
            nid = f"n{i}"
            node_services = [s for s in services if services.index(s) % 10 == i][:50]
            entities.append({
                "id": nid, "type": "node", "name": f"node-{i}",
                "state": "running", "parent": "c1",
                "children": node_services, "metrics": {},
            })
        entities.append({
            "id": "c1", "type": "cluster", "name": "Prod",
            "state": "healthy", "parent": None,
            "children": [f"n{i}" for i in range(10)], "metrics": {},
        })
        layout = r.compute_layout(entities, 1200, 800)
        assert len(layout) == 500

    def test_over_500_capped(self):
        """Entities beyond 500 are capped."""
        r = CityRenderer()
        entities = []
        services = [f"s{i}" for i in range(510)]
        for sid in services:
            entities.append({
                "id": sid, "type": "service", "name": sid,
                "state": "healthy", "parent": "n1",
                "children": [], "metrics": {"cpu": 50, "mem": 50},
            })
        entities.append({
            "id": "n1", "type": "node", "name": "n1",
            "state": "running", "parent": "c1",
            "children": services, "metrics": {},
        })
        entities.append({
            "id": "c1", "type": "cluster", "name": "P",
            "state": "healthy", "parent": None,
            "children": ["n1"], "metrics": {},
        })
        layout = r.compute_layout(entities, 1200, 800)
        # Should be capped at 500
        assert len(layout) <= 500

    def test_no_roots(self):
        """Entities with no roots produce empty layout."""
        r = CityRenderer()
        entities = [
            {"id": "s1", "type": "service", "name": "api",
             "state": "healthy", "parent": "n1",
             "children": [], "metrics": {}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert layout == {}


# ---------------------------------------------------------------------------
# Render tests
# ---------------------------------------------------------------------------


class TestCityRender:
    def test_render_basic(self):
        r = CityRenderer()
        ctx = MockCtx()
        r.render(_basic_entities(), ctx, 800, 600)
        assert len(ctx.calls) > 0
        # Background drawn
        assert any(c[0] == "fillRect" for c in ctx.calls)

    def test_render_uses_bg_color(self):
        r = CityRenderer()
        ctx = MockCtx()
        r.render(_basic_entities(), ctx, 800, 600)
        fill_colors = [c[1] for c in ctx.calls if c[0] == "fillStyle"]
        assert BG_COLOR in fill_colors

    def test_render_neon_glow_calls(self):
        r = CityRenderer()
        ctx = MockCtx()
        r.render(_basic_entities(), ctx, 800, 600)
        # Should have shadowBlur/shadowColor calls for neon glow
        assert any(c[0] == "shadowBlur" for c in ctx.calls)
        assert any(c[0] == "shadowColor" for c in ctx.calls)

    def test_render_critical_state_has_fire(self):
        r = CityRenderer()
        ctx = MockCtx()
        r.render(_basic_entities(state="critical"), ctx, 800, 600)
        # Fire uses globalAlpha
        alpha_calls = [c for c in ctx.calls if c[0] == "globalAlpha"]
        assert len(alpha_calls) > 0

    def test_render_warning_state_has_pulse(self):
        r = CityRenderer()
        ctx = MockCtx()
        r.render(_basic_entities(state="warning"), ctx, 800, 600)
        # Warning triggers pulsing shadowBlur
        blur_vals = [c[1] for c in ctx.calls if c[0] == "shadowBlur"]
        # Should have non-zero blur values
        assert any(v > 0 for v in blur_vals)

    def test_render_empty_entities(self):
        r = CityRenderer()
        ctx = MockCtx()
        r.render([], ctx, 800, 600)
        # Should still draw background
        assert any(c[0] == "fillRect" for c in ctx.calls)

    def test_render_roads_and_reflections(self):
        r = CityRenderer()
        ctx = MockCtx()
        r.render(_basic_entities(), ctx, 800, 600)
        # Road uses ROAD_COLOR
        fill_colors = [c[1] for c in ctx.calls if c[0] == "fillStyle"]
        assert "#111128" in fill_colors  # ROAD_COLOR

    def test_render_traffic_particles(self):
        r = CityRenderer()
        ctx = MockCtx()
        r.render(_basic_entities(), ctx, 800, 600)
        # Particles call fillStyle with traffic colors
        fill_colors = [c[1] for c in ctx.calls if c[0] == "fillStyle"]
        traffic_present = any(c in ("#ff00ff", "#00ffff", "#ffff00", "#ff4488") for c in fill_colors)
        assert traffic_present

    def test_render_neon_signs(self):
        r = CityRenderer()
        ctx = MockCtx()
        r.render(_basic_entities(), ctx, 800, 600)
        # Neon sign draws fillText with service name
        text_calls = [c for c in ctx.calls if c[0] == "fillText"]
        names = [c[1] for c in text_calls if len(c) > 1]
        assert any("api" in str(n) for n in names)

    def test_render_multiple_states(self):
        r = CityRenderer()
        ctx = MockCtx()
        entities = [
            _make_cluster(children=["n1", "n2"]),
            _make_node(nid="n1", children=["s1"]),
            _make_node(nid="n2", children=["s2"]),
            _make_service(sid="s1", cpu=80, state="healthy"),
            _make_service(sid="s2", cpu=20, state="critical"),
        ]
        r.render(entities, ctx, 800, 600)
        assert len(ctx.calls) > 20


# ---------------------------------------------------------------------------
# Tooltip tests
# ---------------------------------------------------------------------------


class TestCityTooltip:
    def test_tooltip_includes_name_and_state(self):
        r = CityRenderer()
        entity = {"id": "s1", "name": "api", "type": "service", "state": "healthy", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "api" in tip
        assert "healthy" in tip

    def test_tooltip_includes_cpu_mem(self):
        r = CityRenderer()
        entity = {"id": "s1", "name": "api", "type": "service", "state": "healthy",
                  "metrics": {"cpu": 42, "mem": 77}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "42" in tip
        assert "77" in tip

    def test_tooltip_rps_and_errors(self):
        r = CityRenderer()
        entity = {"id": "s1", "name": "web", "type": "service", "state": "running",
                  "metrics": {"req_per_sec": 150, "error_rate": 0.02}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "150" in tip
        assert "2.0%" in tip


# ---------------------------------------------------------------------------
# Hit test
# ---------------------------------------------------------------------------


class TestCityHitTest:
    def test_hit_inside(self):
        r = CityRenderer()
        r.compute_layout(_basic_entities(), 800, 600)
        assert r.hit_test({"id": "c1"}, 100, 100) is True

    def test_hit_outside(self):
        r = CityRenderer()
        r.compute_layout(_basic_entities(), 800, 600)
        assert r.hit_test({"id": "c1"}, 9999, 9999) is False

    def test_hit_missing_entity(self):
        r = CityRenderer()
        r.compute_layout([], 800, 600)
        assert r.hit_test({"id": "missing"}, 0, 0) is False


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestCityConfig:
    def test_config_has_required_keys(self):
        r = CityRenderer()
        cfg = r.config()
        assert cfg["name"] == "city"
        assert "description" in cfg
        assert "state_colors" in cfg
        assert "mappings" in cfg
        assert cfg["mappings"]["cluster"] == "district"
        assert cfg["mappings"]["service"] == "building"

    def test_config_has_neon_features(self):
        r = CityRenderer()
        cfg = r.config()
        assert "neon_glow" in cfg
        assert "features" in cfg
        assert "neon_glow" in cfg["features"]
        assert "rain_reflections" in cfg["features"]
        assert "traffic_particles" in cfg["features"]
        assert "fire_smoke_critical" in cfg["features"]
        assert "pulsing_warning" in cfg["features"]
        assert "building_height_cpu" in cfg["features"]
        assert "building_width_memory" in cfg["features"]

    def test_state_colors_match_spec(self):
        assert STATE_COLORS["healthy"] == "#4ade80"
        assert STATE_COLORS["running"] == "#60a5fa"
        assert STATE_COLORS["warning"] == "#fbbf24"
        assert STATE_COLORS["critical"] == "#ef4444"
        assert STATE_COLORS["stopped"] == "#374151"


# ---------------------------------------------------------------------------
# Utility tests
# ---------------------------------------------------------------------------


class TestUtilities:
    def test_hex_to_rgb(self):
        assert _hex_to_rgb("#ff0000") == (255, 0, 0)
        assert _hex_to_rgb("#00ff00") == (0, 255, 0)
        assert _hex_to_rgb("#0a0a1a") == (10, 10, 26)

    def test_darken(self):
        r = CityRenderer()
        result = r._darken("#ffffff", 0.5)
        assert result == "#7f7f7f"

    def test_darken_zero(self):
        r = CityRenderer()
        result = r._darken("#ffffff", 0.0)
        assert result == "#000000"


# ---------------------------------------------------------------------------
# TrafficParticle
# ---------------------------------------------------------------------------


class TestTrafficParticle:
    def test_particle_update(self):
        p = TrafficParticle(100, 570, 570, 50, "#ff00ff")
        p.update(1.0, 800)
        assert p.x == 150

    def test_particle_wraps_right(self):
        p = TrafficParticle(799, 570, 570, 50, "#ff00ff")
        p.update(1.0, 800)
        assert p.x < 0  # wrapped around

    def test_particle_draw(self):
        p = TrafficParticle(100, 570, 570, 50, "#ff00ff")
        ctx = MockCtx()
        p.draw(ctx)
        # New draw uses arc+fill, not fillRect
        assert any(c[0] == "arc" for c in ctx.calls)
        assert any(c[0] == "fill" for c in ctx.calls)
        assert any(c[0] == "arc" for c in ctx.calls)
        assert any(c[0] == "fill" for c in ctx.calls)
