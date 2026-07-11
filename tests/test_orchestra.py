"""Tests for OrchestraRenderer metaphor."""
import pytest
from engine.metaphors.orchestra import OrchestraRenderer, STATE_COLORS, SECTION_COLORS


class TestOrchestraRendererLayout:
    def test_compute_layout_returns_dict(self):
        r = OrchestraRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Strings", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "First Chair", "state": "running",
             "parent": "c1", "children": ["s1"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "Violinist", "state": "healthy",
             "parent": "n1", "children": [], "metrics": {"cpu": 50}},
        ]
        layout = r.compute_layout(entities, 800, 600)
        assert isinstance(layout, dict)
        assert "c1" in layout
        assert "n1" in layout
        assert "s1" in layout

    def test_layout_positions_within_bounds(self):
        r = OrchestraRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Strings", "state": "healthy",
             "parent": None, "children": ["n1"], "metrics": {}},
            {"id": "n1", "type": "node", "name": "Chair 1", "state": "running",
             "parent": "c1", "children": ["s1"], "metrics": {}},
            {"id": "s1", "type": "service", "name": "Player", "state": "healthy",
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

    def test_volume_bars_scale_with_cpu(self):
        r = OrchestraRenderer()
        base_cluster = {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "Strings", "state": "healthy", "metrics": {}}
        base_node = {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "Chair 1", "state": "running", "metrics": {}}

        entities_low = [base_cluster.copy(), base_node.copy(),
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "low", "state": "healthy", "metrics": {"cpu": 10}}]
        entities_high = [base_cluster.copy(), base_node.copy(),
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "high", "state": "healthy", "metrics": {"cpu": 90}}]

        layout_low = r.compute_layout(entities_low, 800, 600)
        layout_high = r.compute_layout(entities_high, 800, 600)
        # Volume bar height should be greater for higher CPU
        assert layout_high["s1"]["volume_h"] > layout_low["s1"]["volume_h"]

    def test_tempo_computed_from_rps(self):
        r = OrchestraRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "name": "Orchestra", "state": "healthy",
             "parent": None, "children": [], "metrics": {"req_per_sec": 120}},
        ]
        r.compute_layout(entities, 800, 600)
        assert r.tempo_bpm == 120

    def test_empty_entities_layout(self):
        r = OrchestraRenderer()
        layout = r.compute_layout([], 800, 600)
        assert layout == {}

    def test_hit_test(self):
        r = OrchestraRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": [],
             "name": "Strings", "state": "healthy", "metrics": {}},
        ]
        r.compute_layout(entities, 800, 600)
        assert r.hit_test({"id": "c1"}, 100, 100) is True
        assert r.hit_test({"id": "c1"}, 9999, 9999) is False

    def test_hit_test_missing_entity(self):
        r = OrchestraRenderer()
        r.compute_layout([], 800, 600)
        assert r.hit_test({"id": "missing"}, 0, 0) is False


class TestOrchestraRendererTooltip:
    def test_tooltip_includes_name_and_state(self):
        r = OrchestraRenderer()
        entity = {"id": "s1", "name": "Violinist", "type": "service", "state": "healthy", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "Violinist" in tip
        assert "healthy" in tip

    def test_tooltip_includes_metrics(self):
        r = OrchestraRenderer()
        entity = {"id": "s1", "name": "Violinist", "type": "service", "state": "healthy",
                  "metrics": {"cpu": 42, "mem": 77}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "42" in tip
        assert "77" in tip

    def test_tooltip_includes_tempo(self):
        r = OrchestraRenderer()
        entity = {"id": "s1", "name": "Violinist", "type": "service", "state": "healthy",
                  "metrics": {"req_per_sec": 90}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "90" in tip


class TestOrchestraRendererConfig:
    def test_config_has_required_keys(self):
        r = OrchestraRenderer()
        cfg = r.config()
        assert cfg["name"] == "orchestra"
        assert "description" in cfg
        assert "state_colors" in cfg
        assert "mappings" in cfg
        assert cfg["mappings"]["cluster"] == "section"
        assert cfg["mappings"]["node"] == "chair"
        assert cfg["mappings"]["service"] == "musician"
        assert cfg["mappings"]["container"] == "instrument"

    def test_config_has_section_colors(self):
        r = OrchestraRenderer()
        cfg = r.config()
        assert "section_colors" in cfg


class TestOrchestraRendererRender:
    def test_render_calls_context_methods(self):
        r = OrchestraRenderer()
        entities = [
            {"id": "c1", "type": "cluster", "parent": None, "children": ["n1"],
             "name": "Strings", "state": "healthy", "metrics": {}},
            {"id": "n1", "type": "node", "parent": "c1", "children": ["s1"],
             "name": "First Chair", "state": "running", "metrics": {}},
            {"id": "s1", "type": "service", "parent": "n1", "children": [],
             "name": "Violinist", "state": "healthy", "metrics": {"cpu": 60}},
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
            def save(self): self.calls.append(("save",))
            def restore(self): self.calls.append(("restore",))
            def globalAlpha(self, a): self.calls.append(("globalAlpha", a))

        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        assert len(ctx.calls) > 0
        assert any(c[0] == "fillRect" for c in ctx.calls)

    def test_render_error_entity_has_discordant_flash(self):
        r = OrchestraRenderer()
        entities = [
            {"id": "s1", "type": "service", "parent": None, "children": [],
             "name": "Broken", "state": "critical", "metrics": {"cpu": 100}},
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
            def save(self): self.calls.append(("save",))
            def restore(self): self.calls.append(("restore",))
            def globalAlpha(self, a): self.calls.append(("globalAlpha", a))

        ctx = MockCtx()
        r.render(entities, ctx, 800, 600)
        # Should have red/critical color for error state
        assert any("fillStyle" == c[0] and "ef4444" in str(c[1]) for c in ctx.calls)

    def test_standing_ovation_for_all_healthy(self):
        r = OrchestraRenderer()
        entities = [
            {"id": "s1", "type": "service", "parent": None, "children": [],
             "name": "Player1", "state": "healthy", "metrics": {"cpu": 30}},
            {"id": "s2", "type": "service", "parent": None, "children": [],
             "name": "Player2", "state": "healthy", "metrics": {"cpu": 40}},
        ]
        is_ovation = r._check_standing_ovation(entities)
        assert is_ovation is True

    def test_no_ovation_with_errors(self):
        r = OrchestraRenderer()
        entities = [
            {"id": "s1", "type": "service", "parent": None, "children": [],
             "name": "Player1", "state": "healthy", "metrics": {"cpu": 30}},
            {"id": "s2", "type": "service", "parent": None, "children": [],
             "name": "Player2", "state": "critical", "metrics": {"cpu": 100}},
        ]
        is_ovation = r._check_standing_ovation(entities)
        assert is_ovation is False


class TestOrchestraSectionColors:
    def test_section_colors_defined(self):
        assert "strings" in SECTION_COLORS
        assert "brass" in SECTION_COLORS
        assert "woodwinds" in SECTION_COLORS
        assert "percussion" in SECTION_COLORS
