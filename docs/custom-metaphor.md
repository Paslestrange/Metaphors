# Creating a Custom Metaphor — Step-by-Step Guide

This tutorial walks you through building a new metaphor renderer from scratch.
By the end you'll have a working **"Traffic Light"** metaphor that visualizes
infrastructure as a road intersection with traffic signals.

---

## Table of Contents

1. [What Is a Metaphor?](#what-is-a-metaphor)
2. [The MetaphorRenderer Interface](#the-metaphorrenderer-interface)
3. [Step 1: Create the File](#step-1-create-the-file)
4. [Step 2: Implement compute_layout()](#step-2-implement-compute_layout)
5. [Step 3: Implement render()](#step-3-implement-render)
6. [Step 4: Implement get_tooltip() and hit_test()](#step-4-implement-get_tooltip-and-hit_test)
7. [Step 5: Register in engine/metaphors/__init__.py](#step-5-register-in-engine-metaphors__init__py)
8. [Step 6: Add to MetaphorRegistry](#step-6-add-to-metaphorregistry)
9. [Step 7: Write Tests](#step-7-write-tests)
10. [Step 8: Add to server.py](#step-8-add-to-serverpy)
11. [Complete Working Example: Traffic Light Metaphor](#complete-working-example-traffic-light-metaphor)

---

## What Is a Metaphor?

A **metaphor** is a visual theme that maps abstract infrastructure entities
(clusters, nodes, services, containers) to a concrete visual scene.

The Metaphors engine uses an **entity hierarchy**:

```
Cluster  →  Node  →  Service  →  Container
```

Each metaphor decides:
- **What each entity type looks like** (a building? a machine? a traffic light?)
- **How entities are positioned** on the canvas (grid? radial? linear?)
- **What visual properties map to metrics** (CPU → size? memory → color?)

Examples already in the project:
| Metaphor    | Cluster        | Node        | Service     | Container      |
|-------------|----------------|-------------|-------------|----------------|
| City        | Cityscape      | District    | Building    | Room           |
| Factory     | Factory Floor  | Workstation | Machine     | Conveyor Belt  |
| Kitchen     | Restaurant     | Station     | Chef        | Pot/Pan        |
| Solar       | Galaxy         | Star System | Planet      | Moon           |
| Garden      | Garden Bed     | Planting Row| Plant       | Branch         |
| Ship        | Fleet          | Ship Section| Station     | Compartment    |

Your metaphor just needs to pick a theme and implement 3 methods.

---

## The MetaphorRenderer Interface

Every metaphor inherits from `MetaphorRenderer` (defined in
`engine/metaphors/base.py`). It's an abstract base class with **3 required
methods**:

### 1. `render(entities, ctx, w, h) -> None`

The main drawing method. Called every frame.

| Parameter  | Description |
|------------|-------------|
| `entities` | `list[dict]` — all entity dicts from the scheduler |
| `ctx`      | Canvas rendering context (HTML5 Canvas API compatible) |
| `w`        | Canvas width in pixels |
| `h`        | Canvas height in pixels |

The `ctx` object supports standard Canvas2D calls:
- `ctx.fillStyle(color)` / `ctx.fillRect(x, y, w, h)`
- `ctx.strokeStyle(color)` / `ctx.strokeRect(x, y, w, h)`
- `ctx.beginPath()` / `ctx.arc(x, y, r, 0, 6.28)` / `ctx.fill()`
- `ctx.font("14px monospace")` / `ctx.fillText(text, x, y)`
- `ctx.lineWidth(n)`

### 2. `get_tooltip(entity, x, y) -> str | None`

Returns tooltip text when the user hovers over an entity.

| Parameter | Description |
|-----------|-------------|
| `entity`  | Single entity dict |
| `x`, `y`  | Mouse coordinates |

Return a multi-line string for the tooltip, or `None` if no tooltip.

### 3. `hit_test(entity, x, y) -> bool`

Tests whether a point falls inside this entity's rendered area.
Used for mouse interaction (click, hover).

| Parameter | Description |
|-----------|-------------|
| `entity`  | Single entity dict |
| `x`, `y`  | Mouse coordinates |

Return `True` if the point is inside the entity's bounds.

### Optional: `compute_layout(entities, w, h) -> dict`

Not part of the ABC, but every metaphor implements it. Computes
positions for all entities and stores them in `self._layout`.
Called at the start of `render()`.

Returns a dict mapping `entity_id -> {"x": float, "y": float, "w": float, "h": float}`.

### Optional: `config() -> dict`

Returns metadata about the metaphor (name, description, state colors,
entity mappings). Used by the `/api/metaphors/{name}` endpoint.

---

## Step 1: Create the File

Create your metaphor module at:

```
engine/metaphors/traffic_light.py
```

Use snake_case naming matching your metaphor name. Start with the skeleton:

```python
"""Traffic Light metaphor renderer — Cluster=Intersection, Node=Road,
Service=Traffic Light, Container=Lamp.

Urban road aesthetic: dark asphalt, signal colors (red/yellow/green).
"""
from __future__ import annotations
from typing import Any
from engine.metaphors.base import MetaphorRenderer


# State-to-signal color mapping
STATE_COLORS = {
    "healthy":  "#22c55e",   # green light — go
    "running":  "#22c55e",   # green light — go
    "idle":     "#eab308",   # yellow light — caution
    "warning":  "#eab308",   # yellow light — caution
    "degraded": "#f97316",   # orange — attention
    "critical": "#ef4444",   # red light — stop
    "stopped":  "#6b7280",   # dark — no signal
    "pending":  "#a78bfa",   # purple — waiting
    "scaling":  "#06b6d4",   # cyan — ramping
    "unknown":  "#4b5563",   # grey
}

# Structural colors
ASPHALT = "#1e1e1e"
ROAD_MARKING = "#fbbf24"
SIDEWALK = "#374151"
HOUSING = "#111827"


class TrafficLightRenderer(MetaphorRenderer):
    """Traffic Light metaphor: clusters are intersections, nodes are roads,
    services are traffic lights, containers are lamps.

    Signal color reflects entity state. Light size scales with CPU.
    """

    name = "traffic_light"
    description = "Infrastructure as a city traffic intersection"

    def __init__(self):
        self._layout: dict[str, dict[str, float]] = {}
```

---

## Step 2: Implement compute_layout()

This method decides where every entity goes on the canvas.

For the traffic light metaphor:
- **Clusters** (intersections) divide the canvas horizontally
- **Nodes** (roads) are lanes running through each intersection
- **Services** (traffic lights) sit at the edges of roads
- **Containers** (lamps) are the individual bulbs within a light

```python
    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, float]]:
        """Compute intersection layout.

        Clusters = intersections (horizontal split).
        Nodes = roads through intersection (vertical lanes).
        Services = traffic lights at road edges.
        Containers = individual lamps.
        """
        layout: dict[str, dict[str, float]] = {}
        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        if not roots:
            self._layout = layout
            return layout

        # Intersections divide canvas horizontally
        intersection_w = w / max(len(roots), 1)
        for i, root in enumerate(roots):
            ix = i * intersection_w
            layout[root["id"]] = {"x": ix, "y": 0, "w": intersection_w, "h": h}

            # Roads (nodes) are vertical lanes within each intersection
            children = [by_id[cid] for cid in (root.get("children") or []) if cid in by_id]
            if not children:
                continue
            lane_w = (intersection_w - 20) / max(len(children), 1)

            for li, child in enumerate(children):
                lx = ix + 10 + li * lane_w
                layout[child["id"]] = {
                    "x": lx, "y": 10,
                    "w": lane_w - 4, "h": h - 20,
                }

                # Traffic lights (services) sit along each road
                grandchildren = [by_id[gcid] for gcid in (child.get("children") or [])
                                 if gcid in by_id]
                if not grandchildren:
                    continue

                light_h = min(80, (h - 40) / max(len(grandchildren), 1))
                for gi, gc in enumerate(grandchildren):
                    cpu = (gc.get("metrics") or {}).get("cpu", 50)
                    light_w = 20 + (lane_w - 30) * (cpu / 100)
                    gx = lx + (lane_w - light_w) / 2
                    gy = 20 + gi * light_h

                    layout[gc["id"]] = {
                        "x": gx, "y": gy,
                        "w": light_w, "h": light_h - 8,
                    }

                    # Lamps (containers) inside each traffic light
                    great_grandchildren = [by_id[ggcid] for ggcid in (gc.get("children") or [])
                                           if ggcid in by_id]
                    lamp_h = (light_h - 16) / max(len(great_grandchildren), 1)
                    for ci, container in enumerate(great_grandchildren):
                        layout[container["id"]] = {
                            "x": gx + 4, "y": gy + 4 + ci * lamp_h,
                            "w": light_w - 8, "h": lamp_h - 2,
                        }

        self._layout = layout
        return layout
```

**Key pattern:** Always store the layout in `self._layout` so `hit_test()`
can use it later.

---

## Step 3: Implement render()

The `render()` method draws everything. Call `compute_layout()` first,
then iterate entities and draw based on their type.

```python
    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the traffic light metaphor."""
        layout = self.compute_layout(entities, w, h)

        # Background — dark asphalt
        ctx.fillStyle(ASPHALT)
        ctx.fillRect(0, 0, w, h)

        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue

            color = STATE_COLORS.get(entity.get("state", "unknown"), STATE_COLORS["unknown"])
            etype = entity.get("type", "")

            if etype == "cluster":
                # Intersection — asphalt with road markings
                ctx.fillStyle("#252525")
                ctx.fillRect(pos["x"] + 2, pos["y"] + 2, pos["w"] - 4, pos["h"] - 4)
                # Yellow center line
                ctx.fillStyle(ROAD_MARKING)
                ctx.fillRect(pos["x"] + pos["w"] / 2 - 1, pos["y"], 2, pos["h"])
                # Label
                ctx.fillStyle("#9ca3af")
                ctx.font("bold 13px monospace")
                ctx.fillText(entity.get("name", ""), pos["x"] + 8, pos["y"] + 18)

            elif etype == "node":
                # Road lane — dark grey with dashed markings
                ctx.fillStyle("#2a2a2a")
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                # Dashed center line
                ctx.fillStyle(ROAD_MARKING)
                dy = pos["y"] + 10
                while dy < pos["y"] + pos["h"] - 10:
                    ctx.fillRect(pos["x"] + pos["w"] / 2 - 1, dy, 2, 8)
                    dy += 16
                # Label
                ctx.fillStyle("#6b7280")
                ctx.font("10px monospace")
                ctx.fillText(entity.get("name", ""), pos["x"] + 4, pos["y"] + 14)

            elif etype == "service":
                # Traffic light housing — dark box with colored signal
                ctx.fillStyle(HOUSING)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle("#374151")
                ctx.lineWidth(2)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

                # Signal light (colored circle)
                cx = pos["x"] + pos["w"] / 2
                cy = pos["y"] + pos["h"] / 2
                radius = min(pos["w"], pos["h"]) / 3
                ctx.fillStyle(color)
                ctx.beginPath()
                ctx.arc(cx, cy, radius, 0, 6.28)
                ctx.fill()

                # Glow effect for active signals
                if entity.get("state") in ("healthy", "running"):
                    ctx.fillStyle(color.replace(")", ", 0.2)").replace("rgb", "rgba")
                    # Fallback: just draw a larger dim circle
                    ctx.globalAlpha(0.15)
                    ctx.beginPath()
                    ctx.arc(cx, cy, radius * 1.8, 0, 6.28)
                    ctx.fill()
                    ctx.globalAlpha(1.0)

                # Label below
                ctx.fillStyle("#d1d5db")
                ctx.font("9px monospace")
                name = entity.get("name", "")[:10]
                ctx.fillText(name, pos["x"] + 2, pos["y"] + pos["h"] + 12)

            elif etype == "container":
                # Individual lamp — small colored rectangle
                ctx.fillStyle(color)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle("#1f2937")
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])
```

---

## Step 4: Implement get_tooltip() and hit_test()

These enable mouse interaction.

### get_tooltip()

Return a human-readable string with entity info using your metaphor's
vocabulary:

```python
    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Generate tooltip text for an entity."""
        etype = entity.get("type", "?")
        metaphor_name = {
            "cluster": "Intersection",
            "node": "Road",
            "service": "Traffic Light",
            "container": "Lamp",
        }.get(etype, etype)

        signal_state = {
            "healthy": "GREEN — flowing",
            "running": "GREEN — flowing",
            "idle": "YELLOW — idle",
            "warning": "YELLOW — caution",
            "critical": "RED — stop!",
            "stopped": "OFF — no signal",
        }.get(entity.get("state", ""), "UNKNOWN")

        lines = [
            f"{entity.get('name', '?')} ({metaphor_name})",
            f"Signal: {signal_state}",
        ]
        m = entity.get("metrics") or {}
        if "cpu" in m:
            lines.append(f"Brightness (CPU): {m['cpu']}%")
        if "mem" in m:
            lines.append(f"Lamp Size (Mem): {m['mem']}%")
        if "req_per_sec" in m:
            lines.append(f"Traffic Flow: {m['req_per_sec']} cars/s")

        return "\n".join(lines)
```

### hit_test()

Check if the mouse coordinates fall inside the entity's layout rectangle:

```python
    def hit_test(self, entity: dict[str, Any], x: int, y: int) -> bool:
        """Check if (x,y) falls within this entity's rendered area."""
        pos = self._layout.get(entity.get("id"))
        if not pos:
            return False
        return (pos["x"] <= x <= pos["x"] + pos["w"] and
                pos["y"] <= y <= pos["y"] + pos["h"])
```

---

## Step 5: Register in engine/metaphors/__init__.py

Add your renderer to the package exports:

```python
"""Metaphor renderer plugin system."""
from engine.metaphors.base import MetaphorRenderer, MetaphorRegistry
from engine.metaphors.city import CityRenderer
from engine.metaphors.space import SpaceStationRenderer
from engine.metaphors.traffic_light import TrafficLightRenderer   # <-- ADD

__all__ = [
    "MetaphorRenderer", "MetaphorRegistry",
    "CityRenderer", "SpaceStationRenderer",
    "TrafficLightRenderer",   # <-- ADD
]
```

---

## Step 6: Add to MetaphorRegistry

The `MetaphorRegistry` is instantiated in `server.py`. You'll register your
renderer there (see Step 8). The registry itself is simple:

```python
registry = MetaphorRegistry()
registry.register("traffic_light", TrafficLightRenderer())
```

Once registered, the metaphor appears in:
- `GET /api/metaphors` — the list endpoint
- WebSocket `switch_metaphor` messages — live switching

---

## Step 7: Write Tests

Create `tests/test_traffic_light.py` following the project's test patterns:

```python
"""Tests for TrafficLightRenderer metaphor."""
import pytest
from engine.metaphors.traffic_light import TrafficLightRenderer, STATE_COLORS


# --- Fixtures ---

def make_entities():
    """Standard 4-level entity hierarchy for testing."""
    return [
        {"id": "c1", "type": "cluster", "name": "Main St & 1st",
         "state": "healthy", "parent": None, "children": ["n1", "n2"],
         "metrics": {}},
        {"id": "n1", "type": "node", "name": "Main St",
         "state": "running", "parent": "c1", "children": ["s1"],
         "metrics": {}},
        {"id": "n2", "type": "node", "name": "1st Ave",
         "state": "running", "parent": "c1", "children": ["s2"],
         "metrics": {}},
        {"id": "s1", "type": "service", "name": "North Light",
         "state": "healthy", "parent": "n1", "children": ["ct1"],
         "metrics": {"cpu": 60}},
        {"id": "s2", "type": "service", "name": "East Light",
         "state": "critical", "parent": "n2", "children": ["ct2"],
         "metrics": {"cpu": 90}},
        {"id": "ct1", "type": "container", "name": "Green Lamp",
         "state": "healthy", "parent": "s1", "children": [],
         "metrics": {"cpu": 30}},
        {"id": "ct2", "type": "container", "name": "Red Lamp",
         "state": "critical", "parent": "s2", "children": [],
         "metrics": {"cpu": 80}},
    ]


# --- Layout Tests ---

class TestTrafficLightLayout:
    def test_compute_layout_returns_dict(self):
        r = TrafficLightRenderer()
        layout = r.compute_layout(make_entities(), 800, 600)
        assert isinstance(layout, dict)
        assert "c1" in layout

    def test_all_entities_have_positions(self):
        r = TrafficLightRenderer()
        entities = make_entities()
        layout = r.compute_layout(entities, 800, 600)
        for e in entities:
            assert e["id"] in layout, f"Missing layout for {e['id']}"

    def test_positions_within_bounds(self):
        r = TrafficLightRenderer()
        layout = r.compute_layout(make_entities(), 800, 600)
        for eid, pos in layout.items():
            assert pos["x"] >= 0
            assert pos["y"] >= 0
            assert pos["w"] > 0
            assert pos["h"] > 0
            assert pos["x"] + pos["w"] <= 800
            assert pos["y"] + pos["h"] <= 600

    def test_empty_entities(self):
        r = TrafficLightRenderer()
        layout = r.compute_layout([], 800, 600)
        assert layout == {}


# --- Tooltip Tests ---

class TestTrafficLightTooltip:
    def test_tooltip_contains_name(self):
        r = TrafficLightRenderer()
        entity = {"id": "s1", "name": "North Light", "type": "service",
                  "state": "healthy", "metrics": {"cpu": 60}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "North Light" in tip
        assert "Traffic Light" in tip

    def test_tooltip_shows_signal_state(self):
        r = TrafficLightRenderer()
        entity = {"id": "s1", "name": "Light", "type": "service",
                  "state": "critical", "metrics": {}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "RED" in tip

    def test_tooltip_includes_metrics(self):
        r = TrafficLightRenderer()
        entity = {"id": "s1", "name": "Light", "type": "service",
                  "state": "healthy", "metrics": {"cpu": 75, "mem": 40}}
        tip = r.get_tooltip(entity, 0, 0)
        assert "75%" in tip
        assert "40%" in tip


# --- Hit Test ---

class TestTrafficLightHitTest:
    def test_hit_inside(self):
        r = TrafficLightRenderer()
        entities = make_entities()
        r.compute_layout(entities, 800, 600)
        pos = r._layout["c1"]
        # Point in center of cluster
        cx = pos["x"] + pos["w"] / 2
        cy = pos["y"] + pos["h"] / 2
        assert r.hit_test(entities[0], cx, cy) is True

    def test_hit_outside(self):
        r = TrafficLightRenderer()
        entities = make_entities()
        r.compute_layout(entities, 800, 600)
        assert r.hit_test(entities[0], -100, -100) is False

    def test_hit_unknown_entity(self):
        r = TrafficLightRenderer()
        r.compute_layout(make_entities(), 800, 600)
        entity = {"id": "nonexistent"}
        assert r.hit_test(entity, 0, 0) is False


# --- Render Tests ---

class MockCtx:
    """Mock canvas context for testing render calls."""
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
        return method


class TestTrafficLightRender:
    def test_render_calls_ctx(self):
        r = TrafficLightRenderer()
        ctx = MockCtx()
        r.render(make_entities(), ctx, 800, 600)
        assert len(ctx.calls) > 0

    def test_render_draws_background(self):
        r = TrafficLightRenderer()
        ctx = MockCtx()
        r.render(make_entities(), ctx, 800, 600)
        fill_calls = [c for c in ctx.calls if c[0] == "fillRect"]
        assert len(fill_calls) > 0
```

Run tests:
```bash
cd /home/pascal/workspace/Metaphors
python -m pytest tests/test_traffic_light.py -v
```

---

## Step 8: Add to server.py

Register the new renderer in `server.py`:

```python
# At the top, add the import:
from engine.metaphors.traffic_light import TrafficLightRenderer

# After the existing registry.register() calls, add:
registry.register("traffic_light", TrafficLightRenderer())
```

Also add a description in the `descriptions` dict inside `list_metaphors()`:

```python
descriptions = {
    "city": "Infrastructure as a cityscape",
    "solar": "Systems as orbiting celestial bodies",
    "forest": "Services as a living forest ecosystem",
    "traffic_light": "Infrastructure as traffic signals at an intersection",  # <-- ADD
}
```

---

## Complete Working Example: Traffic Light Metaphor

Below is the full, self-contained `engine/metaphors/traffic_light.py`:

```python
"""Traffic Light metaphor renderer — Cluster=Intersection, Node=Road,
Service=Traffic Light, Container=Lamp.

Urban road aesthetic: dark asphalt, signal colors (red/yellow/green).
"""
from __future__ import annotations
from typing import Any
from engine.metaphors.base import MetaphorRenderer


# State-to-signal color mapping
STATE_COLORS = {
    "healthy":  "#22c55e",   # green light — go
    "running":  "#22c55e",   # green light — go
    "idle":     "#eab308",   # yellow light — caution
    "warning":  "#eab308",   # yellow light — caution
    "degraded": "#f97316",   # orange — attention
    "critical": "#ef4444",   # red light — stop
    "stopped":  "#6b7280",   # dark — no signal
    "pending":  "#a78bfa",   # purple — waiting
    "scaling":  "#06b6d4",   # cyan — ramping
    "unknown":  "#4b5563",   # grey
}

ASPHALT = "#1e1e1e"
ROAD_MARKING = "#fbbf24"
HOUSING = "#111827"


class TrafficLightRenderer(MetaphorRenderer):
    """Traffic Light metaphor: clusters are intersections, nodes are roads,
    services are traffic lights, containers are lamps."""

    name = "traffic_light"
    description = "Infrastructure as a city traffic intersection"

    def __init__(self):
        self._layout: dict[str, dict[str, float]] = {}

    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, float]]:
        layout: dict[str, dict[str, float]] = {}
        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        if not roots:
            self._layout = layout
            return layout

        intersection_w = w / max(len(roots), 1)
        for i, root in enumerate(roots):
            ix = i * intersection_w
            layout[root["id"]] = {"x": ix, "y": 0, "w": intersection_w, "h": h}

            children = [by_id[cid] for cid in (root.get("children") or []) if cid in by_id]
            if not children:
                continue
            lane_w = (intersection_w - 20) / max(len(children), 1)

            for li, child in enumerate(children):
                lx = ix + 10 + li * lane_w
                layout[child["id"]] = {"x": lx, "y": 10, "w": lane_w - 4, "h": h - 20}

                grandchildren = [by_id[gcid] for gcid in (child.get("children") or []) if gcid in by_id]
                if not grandchildren:
                    continue
                light_h = min(80, (h - 40) / max(len(grandchildren), 1))
                for gi, gc in enumerate(grandchildren):
                    cpu = (gc.get("metrics") or {}).get("cpu", 50)
                    light_w = 20 + (lane_w - 30) * (cpu / 100)
                    gx = lx + (lane_w - light_w) / 2
                    gy = 20 + gi * light_h
                    layout[gc["id"]] = {"x": gx, "y": gy, "w": light_w, "h": light_h - 8}

                    great_grandchildren = [by_id[ggcid] for ggcid in (gc.get("children") or []) if ggcid in by_id]
                    lamp_h = (light_h - 16) / max(len(great_grandchildren), 1)
                    for ci, container in enumerate(great_grandchildren):
                        layout[container["id"]] = {"x": gx + 4, "y": gy + 4 + ci * lamp_h, "w": light_w - 8, "h": lamp_h - 2}

        self._layout = layout
        return layout

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        layout = self.compute_layout(entities, w, h)
        ctx.fillStyle(ASPHALT)
        ctx.fillRect(0, 0, w, h)

        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            color = STATE_COLORS.get(entity.get("state", "unknown"), STATE_COLORS["unknown"])
            etype = entity.get("type", "")

            if etype == "cluster":
                ctx.fillStyle("#252525")
                ctx.fillRect(pos["x"] + 2, pos["y"] + 2, pos["w"] - 4, pos["h"] - 4)
                ctx.fillStyle(ROAD_MARKING)
                ctx.fillRect(pos["x"] + pos["w"] / 2 - 1, pos["y"], 2, pos["h"])
                ctx.fillStyle("#9ca3af")
                ctx.font("bold 13px monospace")
                ctx.fillText(entity.get("name", ""), pos["x"] + 8, pos["y"] + 18)

            elif etype == "node":
                ctx.fillStyle("#2a2a2a")
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.fillStyle(ROAD_MARKING)
                dy = pos["y"] + 10
                while dy < pos["y"] + pos["h"] - 10:
                    ctx.fillRect(pos["x"] + pos["w"] / 2 - 1, dy, 2, 8)
                    dy += 16
                ctx.fillStyle("#6b7280")
                ctx.font("10px monospace")
                ctx.fillText(entity.get("name", ""), pos["x"] + 4, pos["y"] + 14)

            elif etype == "service":
                ctx.fillStyle(HOUSING)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle("#374151")
                ctx.lineWidth(2)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])
                cx = pos["x"] + pos["w"] / 2
                cy = pos["y"] + pos["h"] / 2
                radius = min(pos["w"], pos["h"]) / 3
                ctx.fillStyle(color)
                ctx.beginPath()
                ctx.arc(cx, cy, radius, 0, 6.28)
                ctx.fill()
                ctx.fillStyle("#d1d5db")
                ctx.font("9px monospace")
                ctx.fillText(entity.get("name", "")[:10], pos["x"] + 2, pos["y"] + pos["h"] + 12)

            elif etype == "container":
                ctx.fillStyle(color)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle("#1f2937")
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        etype = entity.get("type", "?")
        metaphor_name = {
            "cluster": "Intersection", "node": "Road",
            "service": "Traffic Light", "container": "Lamp",
        }.get(etype, etype)
        signal_state = {
            "healthy": "GREEN — flowing", "running": "GREEN — flowing",
            "idle": "YELLOW — idle", "warning": "YELLOW — caution",
            "critical": "RED — stop!", "stopped": "OFF — no signal",
        }.get(entity.get("state", ""), "UNKNOWN")
        lines = [f"{entity.get('name', '?')} ({metaphor_name})", f"Signal: {signal_state}"]
        m = entity.get("metrics") or {}
        if "cpu" in m:
            lines.append(f"Brightness (CPU): {m['cpu']}%")
        if "mem" in m:
            lines.append(f"Lamp Size (Mem): {m['mem']}%")
        return "\n".join(lines)

    def hit_test(self, entity: dict[str, Any], x: int, y: int) -> bool:
        pos = self._layout.get(entity.get("id"))
        if not pos:
            return False
        return (pos["x"] <= x <= pos["x"] + pos["w"] and
                pos["y"] <= y <= pos["y"] + pos["h"])

    def config(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "state_colors": STATE_COLORS,
            "mappings": {
                "cluster": "intersection",
                "node": "road",
                "service": "traffic_light",
                "container": "lamp",
            },
        }
```

---

## What It Looks Like

The traffic light metaphor renders a dark asphalt background with yellow road
markings. Each cluster is an intersection box, nodes are road lanes with
dashed center lines, services are dark traffic light housings with colored
signal circles (green=healthy, yellow=idle/warning, red=critical), and
containers are small colored lamp rectangles inside each housing.

```
┌─────────────────────────────────────────────────┐
│  Main St & 1st                    │              │
│  ┌──────────┐  ┌──────────┐     │              │
│  │ Main St  │  │ 1st Ave  │     │              │
│  │  │ │     │  │  │ │     │     │              │
│  │  │ │     │  │  │ │     │     │              │
│  │ ┌─┴─┐   │  │ ┌─┴─┐   │     │              │
│  │ │ ● │   │  │ │ ● │   │     │              │
│  │ │ ● │   │  │ │ ● │   │     │              │
│  │ └───┘   │  │ └───┘   │     │              │
│  └──────────┘  └──────────┘     │              │
│       🟢             🔴          │              │
│   (healthy)      (critical)     │              │
└─────────────────────────────────────────────────┘
```

---

## Checklist

- [ ] Created `engine/metaphors/<name>.py` with class inheriting `MetaphorRenderer`
- [ ] Implemented `compute_layout()` — stores result in `self._layout`
- [ ] Implemented `render()` — draws background, then each entity type
- [ ] Implemented `get_tooltip()` — returns metaphor-themed tooltip text
- [ ] Implemented `hit_test()` — checks `self._layout` bounds
- [ ] Added import + `__all__` entry in `engine/metaphors/__init__.py`
- [ ] Registered instance in `server.py` with `registry.register()`
- [ ] Added description in `server.py` `descriptions` dict
- [ ] Created `tests/test_<name>.py` with layout, tooltip, hit_test, render tests
- [ ] All tests pass: `python -m pytest tests/test_<name>.py -v`
