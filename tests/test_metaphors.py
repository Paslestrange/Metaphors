"""Tests for metaphor renderer plugin system."""
import pytest
from engine.metaphors.base import MetaphorRenderer, MetaphorRegistry


class DummyRenderer(MetaphorRenderer):
    """Concrete test implementation."""

    def __init__(self, label="dummy"):
        self.label = label
        self.render_calls = 0

    def render(self, entities, ctx, w, h):
        self.render_calls += 1

    def get_tooltip(self, entity, x, y):
        return f"{self.label}:{entity['id']}"

    def hit_test(self, entity, x, y):
        return x < 100 and y < 100


class TestMetaphorRendererABC:
    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            MetaphorRenderer()

    def test_concrete_subclass_works(self):
        r = DummyRenderer()
        assert r.render_calls == 0
        r.render([], None, 800, 600)
        assert r.render_calls == 1

    def test_get_tooltip(self):
        r = DummyRenderer("city")
        entity = {"id": "e1", "name": "web"}
        assert r.get_tooltip(entity, 0, 0) == "city:e1"

    def test_hit_test(self):
        r = DummyRenderer()
        entity = {"id": "e1"}
        assert r.hit_test(entity, 50, 50) is True
        assert r.hit_test(entity, 150, 150) is False

    def test_missing_method_raises(self):
        class Incomplete(MetaphorRenderer):
            def render(self, entities, ctx, w, h):
                pass
        with pytest.raises(TypeError):
            Incomplete()


class TestMetaphorRegistry:
    def test_register_and_get(self):
        reg = MetaphorRegistry()
        r = DummyRenderer()
        reg.register("city", r)
        assert reg.get("city") is r

    def test_get_missing_returns_none(self):
        reg = MetaphorRegistry()
        assert reg.get("nonexistent") is None

    def test_list_empty(self):
        reg = MetaphorRegistry()
        assert reg.list() == []

    def test_list_multiple(self):
        reg = MetaphorRegistry()
        reg.register("city", DummyRenderer("city"))
        reg.register("forest", DummyRenderer("forest"))
        reg.register("ocean", DummyRenderer("ocean"))
        names = reg.list()
        assert set(names) == {"city", "forest", "ocean"}

    def test_register_overwrites(self):
        reg = MetaphorRegistry()
        r1 = DummyRenderer("v1")
        r2 = DummyRenderer("v2")
        reg.register("city", r1)
        reg.register("city", r2)
        assert reg.get("city") is r2
        assert reg.get("city").label == "v2"

    def test_list_returns_copy(self):
        reg = MetaphorRegistry()
        reg.register("city", DummyRenderer())
        names = reg.list()
        names.append("hacked")
        assert "hacked" not in reg.list()
