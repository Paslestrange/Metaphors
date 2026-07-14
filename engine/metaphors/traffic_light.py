"""Traffic Light metaphor renderer — Full Urban Night Overhaul.

Cluster=Intersection, Node=Road, Service=Traffic Light, Container=Lamp.

Top-down aerial view of an urban intersection at night with:
- Textured asphalt (noise pattern)
- Lane markings (dashed center lines, turn arrows)
- Zebra crosswalks at all approaches
- Realistic traffic light housings (pole, housing, visor, glowing lens)
- Street signs and intersection labels
- Sidewalks with curb details
- Ambient lighting (street lamps, signal glow, wet asphalt reflections)
- Distant building silhouettes around edges
- Rain particles + wet road reflections
- Vehicle particles (headlights/taillights) moving through intersection
"""
from __future__ import annotations

import math
import random
import time
from typing import Any

from engine.metaphors.base import MetaphorRenderer


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

STATE_COLORS = {
    "healthy":  "#22c55e",
    "running":  "#22c55e",
    "idle":     "#eab308",
    "warning":  "#eab308",
    "degraded": "#f97316",
    "critical": "#ef4444",
    "stopped":  "#6b7280",
    "pending":  "#a78bfa",
    "scaling":  "#06b6d4",
    "unknown":  "#4b5563",
}

ASPHALT       = "#1e1e1e"
ASPHALT_VAR   = "#242424"  # slightly lighter variant for noise
ROAD_MARKING  = "#fbbf24"
HOUSING       = "#111827"
HOUSING_LIGHT = "#1f2937"
SIDEWALK      = "#374151"
CURB          = "#4b5563"
BUILDING_BG   = "#0f1117"
BUILDING_WIN  = "#1e293b"

# Particle counts
VEHICLE_COUNT   = 18
RAIN_COUNT      = 80
STREETLAMP_COUNT = 6


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _adjust_brightness(hex_color: str, factor: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------------
# Particle classes
# ---------------------------------------------------------------------------

class Vehicle:
    """Moving vehicle particle — headlight (warm) or taillight (red)."""

    def __init__(self, x: float, y: float, speed: float, direction: str,
                 lane_offset: float = 0.0):
        self.x = x
        self.y = y
        self.speed = speed
        self.direction = direction  # 'horizontal' or 'vertical'
        self.lane_offset = lane_offset  # 0=right lane, -1=left lane
        self.size = random.uniform(2.0, 3.5)

        if direction == 'horizontal':
            # Moving right: headlight (warm yellow/white)
            # Moving left: taillight (red)
            if speed > 0:
                self.color = random.choice(["#ffeb3b", "#fff9c4", "#ffffff"])
            else:
                self.color = random.choice(["#ff0000", "#ff3333", "#cc0000"])
        else:
            if speed > 0:
                self.color = random.choice(["#ffeb3b", "#fff9c4"])
            else:
                self.color = random.choice(["#ff0000", "#cc0000"])
        self.glow_r = self.size * 3

    def update(self, dt: float, w: int, h: int) -> None:
        if self.direction == 'horizontal':
            self.x += self.speed * dt
            if self.x > w + 20:
                self.x = -20
            elif self.x < -20:
                self.x = w + 20
        else:
            self.y += self.speed * dt
            if self.y > h + 20:
                self.y = -20
            elif self.y < -20:
                self.y = h + 20

    def draw(self, ctx: Any) -> None:
        try:
            ctx.globalAlpha(0.12)
            ctx.fillStyle(self.color)
            ctx.beginPath()
            ctx.arc(self.x, self.y, self.glow_r, 0, math.pi * 2)
            ctx.fill()

            ctx.globalAlpha(0.85)
            ctx.beginPath()
            ctx.arc(self.x, self.y, self.size * 0.5, 0, math.pi * 2)
            ctx.fill()
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass


class RainDrop:
    """Rain streak."""

    def __init__(self, x: float, y: float, speed: float, length: float):
        self.x = x
        self.y = y
        self.speed = speed
        self.length = length
        self.alpha = random.uniform(0.06, 0.2)

    def update(self, dt: float, w: int, h: int) -> None:
        self.y += self.speed * dt
        self.x += self.speed * 0.15 * dt  # slight diagonal
        if self.y > h:
            self.y = -self.length
            self.x = random.uniform(0, w)

    def draw(self, ctx: Any) -> None:
        try:
            ctx.globalAlpha(self.alpha)
            ctx.fillStyle("#8899bb")
            ctx.fillRect(self.x, self.y, 1, self.length)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass


class StreetLamp:
    """A static street lamp with light pool."""

    def __init__(self, x: float, y: float, radius: float):
        self.x = x
        self.y = y
        self.radius = radius

    def draw(self, ctx: Any, now: float) -> None:
        # Outer glow pool
        for layer in range(4, 0, -1):
            frac = layer / 4
            r = self.radius * frac
            try:
                ctx.globalAlpha(0.04 + (1.0 - frac) * 0.06)
                ctx.fillStyle("#fbbf24")
                ctx.beginPath()
                ctx.arc(self.x, self.y, r, 0, math.pi * 2)
                ctx.fill()
                ctx.globalAlpha(1.0)
            except (AttributeError, TypeError):
                pass
        # Lamp core
        try:
            ctx.globalAlpha(0.9)
            ctx.fillStyle("#fff5cc")
            ctx.beginPath()
            ctx.arc(self.x, self.y, 2, 0, math.pi * 2)
            ctx.fill()
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass


class Building:
    """Silhouette building at canvas edge."""

    def __init__(self, x: float, y: float, w: float, h: float, seed: int):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        rng = random.Random(seed)
        # Generate dim windows
        self.windows = []
        n_cols = max(1, int(w / 5))
        n_rows = max(1, int(h / 6))
        for r in range(n_rows):
            for c in range(n_cols):
                if rng.random() < 0.25:
                    self.windows.append((
                        x + 2 + c * (w / max(n_cols, 1)),
                        y + 2 + r * 6,
                        rng.choice(["#1a1a2e", "#222244", "#2a2a4a"]),
                    ))

    def draw(self, ctx: Any) -> None:
        try:
            ctx.globalAlpha(0.7)
            ctx.fillStyle(BUILDING_BG)
            ctx.fillRect(self.x, self.y, self.w, self.h)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass
        for wx, wy, wc in self.windows:
            try:
                ctx.globalAlpha(0.35)
                ctx.fillStyle(wc)
                ctx.fillRect(wx, wy, 2, 3)
                ctx.globalAlpha(1.0)
            except (AttributeError, TypeError):
                pass


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class TrafficLightRenderer(MetaphorRenderer):
    """Traffic Light metaphor — top-down urban intersection at night.

    Cluster → Intersection (zone with crosswalks, labels)
    Node    → Road (lane with markings, sidewalk)
    Service → Traffic Light (housing + pole + glowing lens)
    Container → Lamp (individual signal element)
    """

    name = "traffic_light"
    description = "Infrastructure as a city traffic intersection at night"

    def __init__(self):
        self._layout: dict[str, dict[str, float]] = {}
        self._vehicles: list[Vehicle] = []
        self._rain: list[RainDrop] = []
        self._lamps: list[StreetLamp] = []
        self._buildings: list[Building] = []
        self._asphalt_seed: int = 0
        self._time_offset: float = 0.0
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

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
        self._init_scene(entities, w, h)
        return layout

    # ------------------------------------------------------------------
    # Scene initialization
    # ------------------------------------------------------------------

    def _init_scene(self, entities: list[dict[str, Any]], w: int, h: int) -> None:
        rng = random.Random(42)

        # Vehicles — placed along road lanes
        self._vehicles = []
        roads = [e for e in entities if e.get("type") == "node"]
        for road in roads[:4]:
            pos = self._layout.get(road["id"])
            if not pos:
                continue
            for _ in range(VEHICLE_COUNT // max(len(roads), 1)):
                direction = "horizontal" if pos["h"] < pos["w"] else "vertical"
                if direction == "horizontal":
                    vx = rng.uniform(0, w)
                    vy = pos["y"] + pos["h"] * rng.choice([0.3, 0.7])
                    speed = rng.uniform(30, 80) * rng.choice([1, -1])
                else:
                    vx = pos["x"] + pos["w"] * rng.choice([0.3, 0.7])
                    vy = rng.uniform(0, h)
                    speed = rng.uniform(30, 80) * rng.choice([1, -1])
                self._vehicles.append(Vehicle(vx, vy, speed, direction))

        # Rain
        self._rain = []
        for _ in range(RAIN_COUNT):
            self._rain.append(RainDrop(
                rng.uniform(0, w), rng.uniform(0, h),
                rng.uniform(120, 250), rng.uniform(4, 10)
            ))

        # Street lamps along sidewalks
        self._lamps = []
        for road in roads[:4]:
            pos = self._layout.get(road["id"])
            if not pos:
                continue
            count = max(1, int(pos["h"] / 120) if pos["h"] > pos["w"] else int(pos["w"] / 120))
            is_horizontal = pos["w"] > pos["h"]
            for j in range(count):
                if is_horizontal:
                    sx = pos["x"] + 15 + j * (pos["w"] - 30) / max(count - 1, 1)
                    sy = pos["y"] + 6
                else:
                    sx = pos["x"] + 4
                    sy = pos["y"] + 15 + j * (pos["h"] - 30) / max(count - 1, 1)
                self._lamps.append(StreetLamp(sx, sy, 18 + rng.uniform(0, 8)))

        # Buildings along canvas edges
        self._buildings = []
        bidx = 0
        # Top edge buildings
        x = 0
        while x < w - 20:
            bw = rng.uniform(25, 60)
            bh = rng.uniform(15, 35)
            self._buildings.append(Building(x, 0, bw, bh, bidx))
            x += bw + rng.uniform(5, 15)
            bidx += 1
        # Bottom edge buildings
        x = 0
        while x < w - 20:
            bw = rng.uniform(25, 60)
            bh = rng.uniform(15, 35)
            self._buildings.append(Building(x, h - bh, bw, bh, bidx + 100))
            x += bw + rng.uniform(5, 15)
            bidx += 1
        # Left/right edge buildings (thin strips)
        y = 35
        while y < h - 35:
            bw = rng.uniform(12, 22)
            bh = rng.uniform(20, 40)
            self._buildings.append(Building(0, y, bw, bh, bidx + 200))
            self._buildings.append(Building(w - bw, y, bw, bh, bidx + 300))
            y += bh + rng.uniform(5, 15)
            bidx += 1

        self._asphalt_seed = rng.randint(0, 99999)
        self._initialized = True

    # ------------------------------------------------------------------
    # Render pipeline
    # ------------------------------------------------------------------

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        layout = self.compute_layout(entities, w, h)
        now = time.monotonic()
        dt = now - self._time_offset if self._time_offset > 0 else 0.016
        self._time_offset = now

        # Update particles
        for v in self._vehicles:
            v.update(dt, w, h)
        for r in self._rain:
            r.update(dt, w, h)

        # Layer 0: Asphalt base + noise texture
        self._draw_asphalt(ctx, w, h)

        # Layer 1: Building silhouettes (background)
        for b in self._buildings:
            b.draw(ctx)

        # Layer 2: Sidewalks, roads, markings, crosswalks
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            etype = entity.get("type", "")
            if etype == "cluster":
                self._draw_intersection_zone(ctx, entity, pos, w, h)
            elif etype == "node":
                self._draw_road(ctx, entity, pos, now)

        # Layer 3: Street lamps (light pools)
        for lamp in self._lamps:
            lamp.draw(ctx, now)

        # Layer 4: Traffic light housings + signals
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            etype = entity.get("type", "")
            if etype == "service":
                self._draw_traffic_light(ctx, entity, pos, now)
            elif etype == "container":
                self._draw_lamp(ctx, entity, pos, now)

        # Layer 5: Vehicles
        for v in self._vehicles:
            v.draw(ctx)

        # Layer 6: Signal glow reflections on wet asphalt
        self._draw_signal_reflections(ctx, entities, layout, w, h, now)

        # Layer 7: Rain
        for drop in self._rain:
            drop.draw(ctx)

        # Layer 8: HUD labels
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            if entity.get("type") == "cluster":
                self._draw_intersection_label(ctx, entity, pos)

    # ------------------------------------------------------------------
    # Layer 0: Asphalt texture
    # ------------------------------------------------------------------

    def _draw_asphalt(self, ctx: Any, w: int, h: int) -> None:
        """Asphalt with noise texture — not just flat grey."""
        # Base fill
        ctx.fillStyle(ASPHALT)
        ctx.fillRect(0, 0, w, h)

        # Noise texture — small dots creating subtle grain
        rng = random.Random(self._asphalt_seed)
        dot_count = int(w * h / 400)  # ~1 dot per 400px²
        for _ in range(dot_count):
            dx = rng.uniform(0, w)
            dy = rng.uniform(0, h)
            shade = rng.choice([ASPHALT_VAR, "#1a1a1a", "#222222", "#202020"])
            try:
                ctx.globalAlpha(0.3)
                ctx.fillStyle(shade)
                ctx.fillRect(dx, dy, rng.uniform(1, 3), rng.uniform(1, 3))
                ctx.globalAlpha(1.0)
            except (AttributeError, TypeError):
                pass

        # Subtle radial vignette — darker at edges
        vignette_steps = 8
        for i in range(vignette_steps):
            frac = i / vignette_steps
            inset = frac * min(w, h) * 0.3
            try:
                ctx.globalAlpha(0.04 + frac * 0.08)
                ctx.fillStyle("#000000")
                ctx.fillRect(inset, inset, w - 2 * inset, h - 2 * inset)
                ctx.globalAlpha(1.0)
            except (AttributeError, TypeError):
                pass

    # ------------------------------------------------------------------
    # Layer 2a: Intersection zone
    # ------------------------------------------------------------------

    def _draw_intersection_zone(self, ctx: Any, entity: dict, pos: dict,
                                 w: int, h: int) -> None:
        """Intersection — asphalt, stop lines, crosswalks at all 4 sides."""
        x, y, pw, ph = pos["x"], pos["y"], pos["w"], pos["h"]

        # Slightly lighter asphalt for intersection box
        ctx.fillStyle("#222222")
        ctx.fillRect(x + 2, y + 2, pw - 4, ph - 4)

        # Intersection outline (thin)
        try:
            ctx.globalAlpha(0.2)
            ctx.strokeStyle("#555555")
            ctx.lineWidth(1)
            ctx.strokeRect(x + 2, y + 2, pw - 4, ph - 4)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Crosswalks — zebra stripes on all 4 approaches
        crosswalk_depth = 14  # how far stripes extend from edge
        stripe_w = 3
        stripe_gap = 4

        # Top crosswalk (horizontal stripes)
        self._draw_zebra_crosswalk_h(ctx, x + 4, y + 2, pw - 8, crosswalk_depth)

        # Bottom crosswalk
        self._draw_zebra_crosswalk_h(ctx, x + 4, y + ph - crosswalk_depth - 2,
                                      pw - 8, crosswalk_depth)

        # Left crosswalk (vertical stripes)
        self._draw_zebra_crosswalk_v(ctx, x + 2, y + 4, crosswalk_depth, ph - 8)

        # Right crosswalk
        self._draw_zebra_crosswalk_v(ctx, x + pw - crosswalk_depth - 2, y + 4,
                                      crosswalk_depth, ph - 8)

        # Stop lines (thick white line before each crosswalk)
        try:
            ctx.globalAlpha(0.5)
            ctx.fillStyle("#ffffff")
            # Top stop line
            ctx.fillRect(x + 6, y + crosswalk_depth + 4, pw - 12, 2)
            # Bottom stop line
            ctx.fillRect(x + 6, y + ph - crosswalk_depth - 6, pw - 12, 2)
            # Left stop line
            ctx.fillRect(x + crosswalk_depth + 4, y + 6, 2, ph - 12)
            # Right stop line
            ctx.fillRect(x + pw - crosswalk_depth - 6, y + 6, 2, ph - 12)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

    def _draw_zebra_crosswalk_h(self, ctx: Any, cx: float, cy: float,
                                 cw: float, ch: float) -> None:
        """Horizontal zebra crosswalk (stripes run horizontally)."""
        n_stripes = max(1, int(cw / (3 + 4)))
        stripe_spacing = cw / max(n_stripes, 1)
        try:
            ctx.globalAlpha(0.35)
            ctx.fillStyle("#cccccc")
            for i in range(n_stripes):
                sx = cx + i * stripe_spacing
                ctx.fillRect(sx, cy, stripe_spacing * 0.6, ch)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

    def _draw_zebra_crosswalk_v(self, ctx: Any, cx: float, cy: float,
                                 cw: float, ch: float) -> None:
        """Vertical zebra crosswalk (stripes run vertically)."""
        n_stripes = max(1, int(ch / (3 + 4)))
        stripe_spacing = ch / max(n_stripes, 1)
        try:
            ctx.globalAlpha(0.35)
            ctx.fillStyle("#cccccc")
            for i in range(n_stripes):
                sy = cy + i * stripe_spacing
                ctx.fillRect(cx, sy, cw, stripe_spacing * 0.6)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

    # ------------------------------------------------------------------
    # Layer 2b: Road with lane markings
    # ------------------------------------------------------------------

    def _draw_road(self, ctx: Any, entity: dict, pos: dict, now: float) -> None:
        """Road — asphalt lane with dashed center, directional arrows, sidewalks."""
        x, y, pw, ph = pos["x"], pos["y"], pos["w"], pos["h"]

        # Road surface (slightly different asphalt)
        ctx.fillStyle("#1c1c1c")
        ctx.fillRect(x, y, pw, ph)

        # Sidewalks on both sides
        sidewalk_w = max(3, pw * 0.08)
        try:
            ctx.globalAlpha(0.6)
            ctx.fillStyle(SIDEWALK)
            ctx.fillRect(x, y, sidewalk_w, ph)
            ctx.fillRect(x + pw - sidewalk_w, y, sidewalk_w, ph)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Curb detail (brighter thin line between sidewalk and road)
        try:
            ctx.globalAlpha(0.3)
            ctx.fillStyle(CURB)
            ctx.fillRect(x + sidewalk_w, y, 1, ph)
            ctx.fillRect(x + pw - sidewalk_w - 1, y, 1, ph)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Dashed center line
        is_vertical = ph > pw
        if is_vertical:
            # Vertical dashed line down center
            cx_line = x + pw / 2
            dy = y + 8
            while dy < y + ph - 8:
                ctx.fillStyle(ROAD_MARKING)
                ctx.fillRect(cx_line - 1, dy, 2, 10)
                dy += 20
        else:
            # Horizontal dashed line
            cy_line = y + ph / 2
            dx = x + 8
            while dx < x + pw - 8:
                ctx.fillStyle(ROAD_MARKING)
                ctx.fillRect(dx, cy_line - 1, 10, 2)
                dx += 20

        # Directional arrows (subtle)
        if is_vertical and ph > 80:
            self._draw_directional_arrow(ctx, x + pw / 2 - 4, y + ph * 0.3, 8, "up")
            self._draw_directional_arrow(ctx, x + pw / 2 - 4, y + ph * 0.7, 8, "down")

        # Road label
        ctx.fillStyle("#4b5563")
        ctx.font("10px 'Courier New', monospace")
        name = entity.get("name", "")[:12]
        if is_vertical:
            ctx.fillText(name, x + sidewalk_w + 3, y + 14)
        else:
            ctx.fillText(name, x + 6, y + ph / 2 + 4)

    def _draw_directional_arrow(self, ctx: Any, ax: float, ay: float,
                                 size: float, direction: str) -> None:
        """Small directional arrow on road surface."""
        try:
            ctx.globalAlpha(0.2)
            ctx.fillStyle("#fbbf24")
            if direction == "up":
                # Triangle pointing up
                ctx.beginPath()
                ctx.moveTo(ax + size / 2, ay)
                ctx.lineTo(ax + size, ay + size)
                ctx.lineTo(ax, ay + size)
                ctx.closePath()
                ctx.fill()
            else:
                # Triangle pointing down
                ctx.beginPath()
                ctx.moveTo(ax, ay)
                ctx.lineTo(ax + size, ay)
                ctx.lineTo(ax + size / 2, ay + size)
                ctx.closePath()
                ctx.fill()
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

    # ------------------------------------------------------------------
    # Layer 4a: Traffic light housing (realistic)
    # ------------------------------------------------------------------

    def _draw_traffic_light(self, ctx: Any, entity: dict, pos: dict, now: float) -> None:
        """Realistic traffic light: pole, housing, visor, glowing lens."""
        state = entity.get("state", "unknown")
        color = STATE_COLORS.get(state, STATE_COLORS["unknown"])
        x, y, pw, ph = pos["x"], pos["y"], pos["w"], pos["h"]

        # Mounting pole (thin line extending up/down from housing)
        pole_x = x + pw / 2
        pole_w = max(2, pw * 0.12)
        try:
            ctx.globalAlpha(0.5)
            ctx.fillStyle("#374151")
            # Top pole segment
            ctx.fillRect(pole_x - pole_w / 2, y - 6, pole_w, 6)
            # Bottom pole segment
            ctx.fillRect(pole_x - pole_w / 2, y + ph, pole_w, 8)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Housing body — dark rectangular box with rounded feel
        ctx.fillStyle(HOUSING)
        ctx.fillRect(x, y, pw, ph)

        # Housing highlight (top edge lighter for 3D effect)
        try:
            ctx.globalAlpha(0.15)
            ctx.fillStyle("#374151")
            ctx.fillRect(x, y, pw, 2)
            ctx.globalAlpha(0.08)
            ctx.fillStyle("#ffffff")
            ctx.fillRect(x, y + 2, pw, 1)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Housing border
        ctx.strokeStyle("#374151")
        ctx.lineWidth(1.5)
        ctx.strokeRect(x, y, pw, ph)

        # Visor (horizontal bar above lens for shadow effect)
        visor_y = y + 2
        visor_h = max(2, ph * 0.12)
        try:
            ctx.globalAlpha(0.4)
            ctx.fillStyle("#0a0a0a")
            ctx.fillRect(x + 2, visor_y, pw - 4, visor_h)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Signal lens (colored circle)
        cx = x + pw / 2
        cy = y + ph * 0.5
        radius = min(pw, ph) / 3

        # Outer glow ring
        try:
            ctx.globalAlpha(0.12)
            ctx.fillStyle(color)
            ctx.beginPath()
            ctx.arc(cx, cy, radius * 2, 0, math.pi * 2)
            ctx.fill()
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Main lens fill
        ctx.fillStyle(color)
        ctx.beginPath()
        ctx.arc(cx, cy, radius, 0, math.pi * 2)
        ctx.fill()

        # Lens specular highlight (small bright dot)
        try:
            ctx.globalAlpha(0.4)
            ctx.fillStyle("#ffffff")
            ctx.beginPath()
            ctx.arc(cx - radius * 0.2, cy - radius * 0.2, radius * 0.25, 0, math.pi * 2)
            ctx.fill()
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Pulse animation for critical state
        if state == "critical":
            pulse = 0.5 + 0.5 * math.sin(now * 6)
            try:
                ctx.globalAlpha(0.15 * pulse)
                ctx.fillStyle(color)
                ctx.beginPath()
                ctx.arc(cx, cy, radius * 2.5, 0, math.pi * 2)
                ctx.fill()
                ctx.globalAlpha(1.0)
            except (AttributeError, TypeError):
                pass

        # Service label below
        ctx.fillStyle("#d1d5db")
        ctx.font("9px 'Courier New', monospace")
        name = entity.get("name", "")[:10]
        ctx.fillText(name, x + 2, y + ph + 12)

    # ------------------------------------------------------------------
    # Layer 4b: Lamp (container)
    # ------------------------------------------------------------------

    def _draw_lamp(self, ctx: Any, entity: dict, pos: dict, now: float) -> None:
        """Individual lamp — small glowing rectangle inside traffic light."""
        state = entity.get("state", "unknown")
        color = STATE_COLORS.get(state, STATE_COLORS["unknown"])
        x, y, pw, ph = pos["x"], pos["y"], pos["w"], pos["h"]

        # Lamp body
        ctx.fillStyle(HOUSING_LIGHT)
        ctx.fillRect(x, y, pw, ph)

        # Lamp glow
        glow_size = min(pw, ph) * 0.3
        try:
            ctx.globalAlpha(0.2)
            ctx.fillStyle(color)
            ctx.beginPath()
            ctx.arc(x + pw / 2, y + ph / 2, glow_size, 0, math.pi * 2)
            ctx.fill()
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Lamp center
        ctx.fillStyle(color)
        ctx.fillRect(x + 2, y + 2, pw - 4, ph - 4)

        # Subtle border
        ctx.strokeStyle("#1f2937")
        ctx.lineWidth(1)
        ctx.strokeRect(x, y, pw, ph)

    # ------------------------------------------------------------------
    # Layer 6: Signal glow reflections on wet road
    # ------------------------------------------------------------------

    def _draw_signal_reflections(self, ctx: Any, entities: list, layout: dict,
                                  w: int, h: int, now: float) -> None:
        """Signal glow reflected on wet asphalt — elongated vertical streaks."""
        shimmer = math.sin(now * 1.5)
        try:
            ctx.globalAlpha(0.03 + 0.01 * shimmer)
            ctx.fillStyle("#22c55e")
            ctx.fillRect(0, 0, w, h)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        for entity in entities:
            if entity.get("type") != "service":
                continue
            pos = layout.get(entity["id"])
            if not pos:
                continue
            state = entity.get("state", "unknown")
            color = STATE_COLORS.get(state, STATE_COLORS["unknown"])
            x, y, pw, ph = pos["x"], pos["y"], pos["w"], pos["h"]

            # Vertical reflection streak below signal
            ref_h = ph * 3
            ref_y = y + ph + 4
            steps = 8
            for s in range(steps):
                frac = s / steps
                alpha = (0.15 - frac * 0.12)  # 0.15 → 0.03
                if alpha <= 0:
                    break
                try:
                    ctx.globalAlpha(alpha)
                    ctx.fillStyle(color)
                    ctx.fillRect(x - 2, ref_y + frac * ref_h, pw + 4, ref_h / steps + 1)
                    ctx.globalAlpha(1.0)
                except (AttributeError, TypeError):
                    pass

    # ------------------------------------------------------------------
    # Layer 8: Intersection label
    # ------------------------------------------------------------------

    def _draw_intersection_label(self, ctx: Any, entity: dict, pos: dict) -> None:
        """Street sign style label for intersection."""
        name = entity.get("name", "")[:20]
        x, y, pw = pos["x"], pos["y"], pos["w"]

        # Sign plate
        sign_w = min(140, pw - 16)
        sign_h = 18
        sign_x = x + 8
        sign_y = y + 24

        # Plate background
        ctx.fillStyle("#1e3a5f")
        ctx.fillRect(sign_x, sign_y, sign_w, sign_h)

        # Plate border
        ctx.strokeStyle("#3b82f6")
        ctx.lineWidth(1)
        ctx.strokeRect(sign_x, sign_y, sign_w, sign_h)

        # Text
        ctx.fillStyle("#e2e8f0")
        ctx.font("bold 10px 'Courier New', monospace")
        ctx.fillText(name, sign_x + 4, sign_y + 13)

    # ------------------------------------------------------------------
    # Tooltip
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Hit test
    # ------------------------------------------------------------------

    def hit_test(self, entity: dict[str, Any], x: int, y: int) -> bool:
        """Check if (x,y) falls within this entity's rendered area."""
        pos = self._layout.get(entity.get("id"))
        if not pos:
            return False
        return (pos["x"] <= x <= pos["x"] + pos["w"] and
                pos["y"] <= y <= pos["y"] + pos["h"])

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def config(self) -> dict[str, Any]:
        """Return metaphor configuration metadata."""
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
