"""City metaphor renderer — Full Cyberpunk Visual Overhaul.

6-layer depth rendering:
  Layer 0: Sky gradient + stars
  Layer 1: Far buildings (silhouette skyline)
  Layer 2: Ground / roads / crosswalks / traffic lights
  Layer 3: Main buildings (architectural detail, windows, roof mechanicals, awnings, antennas)
  Layer 4: Rain / particles / traffic
  Layer 5: HUD overlay (neon signs, labels, tooltips)

Cluster→District, Node→Block, Service→Building.
Building height = CPU usage, width = memory usage.
"""
from __future__ import annotations

import math
import random
import time
from typing import Any

from engine.metaphors.base import MetaphorRenderer


# State → color map (spec-mandated)
STATE_COLORS = {
    "healthy": "#4ade80",
    "running": "#60a5fa",
    "warning": "#fbbf24",
    "critical": "#ef4444",
    "stopped": "#374151",
    "idle": "#94a3b8",
    "degraded": "#f97316",
    "pending": "#a78bfa",
    "scaling": "#06b6d4",
    "unknown": "#6b7280",
}

# Neon glow colors per state
NEON_GLOW = {
    "healthy": "#22ff88",
    "running": "#44aaff",
    "warning": "#ffcc00",
    "critical": "#ff2222",
    "stopped": "#555555",
    "idle": "#8899aa",
    "degraded": "#ff8800",
    "pending": "#bb99ff",
    "scaling": "#00ddff",
    "unknown": "#778899",
}

# Background / environment
BG_COLOR = "#0a0a1a"
BG_COLOR_HORIZON = "#0d0d22"
GROUND_COLOR = "#0d0d22"
ROAD_COLOR = "#111128"

# Building constants
MIN_BUILDING_W = 12
MAX_BUILDING_W = 80
WINDOW_COLOR_HEALTHY = "#fbbf24"
WINDOW_COLOR_RUNNING = "#60a5fa"
WINDOW_COLOR_WARNING = "#f97316"
WINDOW_COLOR_CRITICAL = "#ef4444"
WINDOW_COLOR_IDLE = "#94a3b8"
WINDOW_COLOR_OFF = "#1a1a2e"
BUILDING_WALL = "#1a1a3e"

# Neon sign
NEON_SIGN_BG = "#0f0f2a"
NEON_SIGN_BORDER = "#ff00ff"

# Traffic particle (kept for test compat)
TRAFFIC_COLORS = ["#ff00ff", "#00ffff", "#ffff00", "#ff4488"]

# Star field
STAR_COUNT = 80

# Rain
RAIN_COUNT = 120

# Far buildings
FAR_BUILDING_COUNT = 18


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex string."""
    return f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"


class TrafficParticle:
    """A single traffic particle moving along a road — headlight or taillight."""

    def __init__(self, x: float, y: float, road_y: float, speed: float, direction: str):
        self.x = x
        self.y = y
        self.road_y = road_y
        self.speed = speed
        self.direction = direction  # 'right' or 'left'
        self.size = random.uniform(2.0, 4.0)
        
        # Headlights (moving right): warm yellow/white
        # Taillights (moving left): red
        if direction == 'right':
            self.color = random.choice(["#ffeb3b", "#fff9c4", "#ffffff", "#ffe082"])
        else:
            self.color = random.choice(["#ff0000", "#ff3333", "#cc0000", "#ff1a1a"])
        self.glow_radius = self.size * 2.5

    def update(self, dt: float, canvas_w: int) -> None:
        self.x += self.speed * dt
        # Wrap around screen edges
        if self.x > canvas_w + 20:
            self.x = -20
        elif self.x < -20:
            self.x = canvas_w + 20

    def draw(self, ctx: Any) -> None:
        try:
            # Subtle glow effect
            ctx.globalAlpha(0.15)
            ctx.fillStyle(self.color)
            ctx.beginPath()
            ctx.arc(self.x, self.y, self.glow_radius, 0, math.pi * 2)
            ctx.fill()
            
            # Core light dot
            ctx.globalAlpha(0.9)
            ctx.fillStyle(self.color)
            ctx.beginPath()
            ctx.arc(self.x, self.y, self.size * 0.5, 0, math.pi * 2)
            ctx.fill()
            
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass


class RainDrop:
    """A single rain drop — vertical semi-transparent line."""

    def __init__(self, x: float, y: float, speed: float, length: float):
        self.x = x
        self.y = y
        self.speed = speed
        self.length = length
        self.alpha = random.uniform(0.05, 0.18)

    def update(self, dt: float, canvas_w: int, canvas_h: int) -> None:
        self.y += self.speed * dt
        if self.y > canvas_h:
            self.y = -self.length
            self.x = random.uniform(0, canvas_w)

    def draw(self, ctx: Any) -> None:
        try:
            ctx.globalAlpha(self.alpha)
            ctx.fillStyle("#8899cc")
            ctx.fillRect(self.x, self.y, 1, self.length)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass


class Star:
    """A single star in the sky."""

    def __init__(self, x: float, y: float, size: float, brightness: float):
        self.x = x
        self.y = y
        self.size = size
        self.brightness = brightness
        self.twinkle_speed = random.uniform(0.5, 3.0)
        self.phase = random.uniform(0, math.pi * 2)

    def draw(self, ctx: Any, now: float) -> None:
        alpha = self.brightness * (0.5 + 0.5 * math.sin(now * self.twinkle_speed + self.phase))
        try:
            ctx.globalAlpha(alpha)
            ctx.fillStyle("#ffffff")
            ctx.fillRect(self.x, self.y, self.size, self.size)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass


class FarBuilding:
    """Silhouette building in the background skyline."""

    def __init__(self, x: float, w: float, h: float):
        self.x = x
        self.w = w
        self.h = h
        # A few dim windows
        self.windows = []
        n_cols = max(1, int(w / 6))
        n_rows = max(1, int(h / 8))
        for r in range(n_rows):
            for c in range(n_cols):
                if random.random() < 0.3:
                    self.windows.append((
                        x + 2 + c * (w / max(n_cols, 1)),
                        r * 8 + 4,
                        random.choice(["#1a1a3e", "#222244", "#2a2a4a"]),
                    ))

    def draw(self, ctx: Any, base_y: float) -> None:
        # Dark silhouette
        try:
            ctx.globalAlpha(0.6)
            ctx.fillStyle("#0e0e24")
            ctx.fillRect(self.x, base_y - self.h, self.w, self.h)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass
        # Dim windows
        for wx, wy, wc in self.windows:
            try:
                ctx.globalAlpha(0.3)
                ctx.fillStyle(wc)
                ctx.fillRect(wx, base_y - self.h + wy, 3, 3)
                ctx.globalAlpha(1.0)
            except (AttributeError, TypeError):
                pass


class CityRenderer(MetaphorRenderer):
    """Neon Cyberpunk city metaphor — full visual overhaul.

    6-layer depth:
      0: Sky gradient + stars
      1: Far buildings (silhouette skyline)
      2: Ground / roads / crosswalks / traffic lights
      3: Main buildings with architectural detail
      4: Rain / traffic particles
      5: HUD (neon signs, labels)
    """

    name = "city"
    description = "Infrastructure as a neon cyberpunk city"

    def __init__(self):
        self._layout: dict[str, dict[str, float]] = {}
        self._particles: list[TrafficParticle] = []
        self._rain: list[RainDrop] = []
        self._stars: list[Star] = []
        self._far_buildings: list[FarBuilding] = []
        self._time_offset: float = 0.0
        self._rng = random.Random(42)
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compute_layout(
        self, entities: list[dict[str, Any]], w: int, h: int
    ) -> dict[str, dict[str, float]]:
        """Compute positions for all entities. Handles 0-500 entities."""
        layout: dict[str, dict[str, float]] = {}
        if not entities:
            self._layout = layout
            return layout

        entities = entities[:500]

        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        if not roots:
            self._layout = layout
            return layout

        n_roots = len(roots)
        district_w = w / max(n_roots, 1)

        for di, root in enumerate(roots):
            dx = di * district_w
            layout[root["id"]] = {"x": dx, "y": 0, "w": district_w, "h": h}

            children = [
                by_id[cid]
                for cid in (root.get("children") or [])
                if cid in by_id
            ]
            if not children:
                continue

            block_h = (h - 60) / max(len(children), 1)

            for bi, child in enumerate(children):
                by_ = bi * block_h
                layout[child["id"]] = {
                    "x": dx + 10,
                    "y": by_ + 30,
                    "w": district_w - 20,
                    "h": block_h - 10,
                }

                grandchildren = [
                    by_id[gcid]
                    for gcid in (child.get("children") or [])
                    if gcid in by_id
                ]
                if not grandchildren:
                    continue

                n_gc = len(grandchildren)
                total_gw = district_w - 40
                building_slot_w = total_gw / max(n_gc, 1)

                for gi, gc in enumerate(grandchildren):
                    metrics = gc.get("metrics") or {}
                    cpu = max(0, min(100, metrics.get("cpu", 50)))
                    mem = max(0, min(100, metrics.get("mem", 50)))

                    bw = max(MIN_BUILDING_W, MIN_BUILDING_W + (MAX_BUILDING_W - MIN_BUILDING_W) * (mem / 100))
                    bw = min(bw, building_slot_w - 4)
                    max_bh = block_h - 50
                    bh = max(15, max_bh * (cpu / 100))

                    bx = dx + 20 + gi * building_slot_w + (building_slot_w - bw) / 2
                    by_pos = by_ + 30 + (block_h - 50 - bh)

                    layout[gc["id"]] = {
                        "x": bx,
                        "y": by_pos,
                        "w": bw,
                        "h": bh,
                    }

        self._layout = layout
        self._init_scene(entities, w, h)
        return layout

    # ------------------------------------------------------------------
    # Scene initialization
    # ------------------------------------------------------------------

    def _init_scene(self, entities: list[dict[str, Any]], w: int, h: int) -> None:
        """Initialize stars, far buildings, rain, traffic particles."""
        # Stars
        self._stars = []
        for _ in range(STAR_COUNT):
            sx = self._rng.uniform(0, w)
            sy = self._rng.uniform(0, h * 0.35)
            ss = self._rng.uniform(0.5, 2.0)
            sb = self._rng.uniform(0.3, 0.9)
            self._stars.append(Star(sx, sy, ss, sb))

        # Far buildings (silhouette skyline at horizon)
        self._far_buildings = []
        horizon_y = h * 0.45
        fx = 0.0
        for _ in range(FAR_BUILDING_COUNT):
            fw = self._rng.uniform(15, 50)
            fh = self._rng.uniform(20, horizon_y * 0.6)
            self._far_buildings.append(FarBuilding(fx, fw, fh))
            fx += fw + self._rng.uniform(2, 12)
            if fx > w:
                break

        # Rain
        self._rain = []
        for _ in range(RAIN_COUNT):
            rx = self._rng.uniform(0, w)
            ry = self._rng.uniform(0, h)
            rs = self._rng.uniform(200, 500)
            rl = self._rng.uniform(6, 18)
            self._rain.append(RainDrop(rx, ry, rs, rl))

        # Traffic particles
        self._init_particles(entities, w, h)
        self._initialized = True

    def _init_particles(self, entities: list[dict[str, Any]], w: int, h: int) -> None:
        """Create traffic particles on the road strip.
        
        Density scales with entity count: more entities = more traffic.
        Headlights (yellow/white) move right, taillights (red) move left.
        """
        self._particles = []
        road_y = h - 30
        
        # Density based on entity count: base + scale
        n_entities = len(entities) if entities else 0
        n_particles = min(80, 5 + int(n_entities * 0.3))
        
        # Split roughly 50/50 between headlights and taillights
        n_headlights = n_particles // 2
        n_taillights = n_particles - n_headlights
        
        # Headlights (moving right) - warm yellow/white
        for _ in range(n_headlights):
            px = self._rng.uniform(0, w)
            py = road_y + self._rng.uniform(-3, 8)  # Upper lane
            # Speed: 0.5-2px per frame at 60fps = 30-120 px/sec
            speed = self._rng.uniform(30, 120)
            self._particles.append(TrafficParticle(px, py, road_y, speed, 'right'))
        
        # Taillights (moving left) - red
        for _ in range(n_taillights):
            px = self._rng.uniform(0, w)
            py = road_y + self._rng.uniform(8, 18)  # Lower lane
            speed = self._rng.uniform(30, 120)
            self._particles.append(TrafficParticle(px, py, road_y, -speed, 'left'))

    def _update_particles(self, dt: float, w: int, h: int) -> None:
        for p in self._particles:
            p.update(dt, w)
        for r in self._rain:
            r.update(dt, w, h)

    # ------------------------------------------------------------------
    # Render — 6-layer pipeline
    # ------------------------------------------------------------------

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the cyberpunk city with full visual overhaul."""
        layout = self.compute_layout(entities, w, h)
        now = time.monotonic()
        dt = now - self._time_offset if self._time_offset > 0 else 0.016
        self._time_offset = now
        self._update_particles(dt, w, h)

        # Layer 0: Sky gradient + stars
        self._draw_sky(ctx, w, h, now)

        # Layer 1: Far buildings (silhouette skyline)
        self._draw_far_buildings(ctx, w, h)

        # Layer 2: Ground / roads / crosswalks / traffic lights
        self._draw_ground_and_roads(ctx, w, h, now)

        # Districts (clusters) — neon border overlay
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            if entity.get("type", "") == "cluster":
                self._draw_district(ctx, entity, pos)

        # Blocks (nodes) — dark pads
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            if entity.get("type", "") == "node":
                self._draw_block(ctx, entity, pos)

        # Layer 3: Main buildings with architectural detail
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            if entity.get("type", "") == "service":
                self._draw_building(ctx, entity, pos, now)

        # Layer 4: Rain
        self._draw_rain(ctx)

        # Layer 4: Traffic particles
        for p in self._particles:
            p.draw(ctx)

        # Layer 2b: Ground reflections (wet road, mirrored building glow)
        self._draw_ground_reflections(ctx, entities, layout, w, h, now)

    # ------------------------------------------------------------------
    # Layer 0: Sky + Stars
    # ------------------------------------------------------------------

    def _draw_sky(self, ctx: Any, w: int, h: int, now: float) -> None:
        """Sky gradient: #0a0a1a (top) -> #0d0d22 (horizon) -> #1a1a2e (ground glow).

        Also renders: stars, moon glow, city haze (orange/purple neon tint).
        """
        # Layer 0a: Base sky fill -- deep dark blue-black
        ctx.fillStyle(BG_COLOR)
        ctx.fillRect(0, 0, w, h)

        # Layer 0b: Vertical gradient bands -- top -> horizon -> ground glow
        #   Top (#0a0a1a) -> mid-sky (#0c0c20) -> horizon (#0d0d22) -> ground glow (#1a1a2e)
        gradient_stops = [
            (0.00, BG_COLOR,         0.0),   # top
            (0.15, "#0b0b1e",        0.02),
            (0.28, "#0c0c20",        0.04),
            (0.40, BG_COLOR_HORIZON, 0.06),  # horizon band
            (0.48, "#0f0f24",        0.08),
            (0.55, "#141428",        0.10),
            (0.62, "#1a1a2e",        0.12),  # ground glow zone
            (0.70, "#1a1a2e",        0.08),  # fading ground glow
        ]
        for frac_val, color_val, alpha_val in gradient_stops:
            y_pos = frac_val * h * 0.55
            band_h = h * 0.55 / len(gradient_stops)
            try:
                ctx.globalAlpha(alpha_val)
                ctx.fillStyle(color_val)
                ctx.fillRect(0, y_pos, w, band_h + 2)  # +2 to avoid seams
                ctx.globalAlpha(1.0)
            except (AttributeError, TypeError):
                pass

        # Layer 0c: Moon glow -- soft circular gradient upper-right area
        #   Approximate with concentric overlapping fills, outer dim -> inner brighter
        moon_cx = w * 0.78
        moon_cy = h * 0.09
        moon_r = min(w, h) * 0.18
        moon_layers = 10
        for i in range(moon_layers, 0, -1):
            frac = i / moon_layers
            rx = moon_r * frac
            alpha = 0.015 + (1.0 - frac) * 0.04
            try:
                ctx.globalAlpha(alpha)
                ctx.fillStyle("#8888cc")
                ctx.fillRect(moon_cx - rx, moon_cy - rx * 0.6, rx * 2, rx * 1.2)
                ctx.globalAlpha(1.0)
            except (AttributeError, TypeError):
                pass
        # Moon core -- small bright disc
        try:
            ctx.globalAlpha(0.12)
            ctx.fillStyle("#aaaadd")
            core_r = moon_r * 0.12
            ctx.fillRect(moon_cx - core_r, moon_cy - core_r * 0.6, core_r * 2, core_r * 1.2)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Layer 0d: City haze -- horizontal gradient at horizon (orange/purple neon tint)
        #   Purple band (left-center)
        haze_y = h * 0.38
        haze_h = h * 0.14
        try:
            ctx.globalAlpha(0.07)
            ctx.fillStyle("#2a0a4a")  # deep purple
            ctx.fillRect(0, haze_y, w * 0.55, haze_h)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass
        #   Orange band (right-center, from neon signs)
        try:
            ctx.globalAlpha(0.05)
            ctx.fillStyle("#4a1a0a")  # deep orange
            ctx.fillRect(w * 0.35, haze_y, w * 0.65, haze_h)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass
        #   Blend strip -- purple-orange mix in middle
        try:
            ctx.globalAlpha(0.04)
            ctx.fillStyle("#3a0a2a")  # magenta blend
            ctx.fillRect(w * 0.25, haze_y + haze_h * 0.2, w * 0.5, haze_h * 0.6)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Layer 0e: Stars
        for star in self._stars:
            star.draw(ctx, now)

    # ------------------------------------------------------------------
    # Layer 1: Far Buildings (silhouette skyline)
    # ------------------------------------------------------------------

    def _draw_far_buildings(self, ctx: Any, w: int, h: int) -> None:
        """Silhouette skyline at the horizon."""
        horizon_y = h * 0.45
        for fb in self._far_buildings:
            fb.draw(ctx, horizon_y)

    # ------------------------------------------------------------------
    # Layer 2: Ground / Roads / Crosswalks / Traffic Lights
    # ------------------------------------------------------------------

    def _draw_ground_and_roads(self, ctx: Any, w: int, h: int, now: float) -> None:
        """Ground plane, road network with lanes, crosswalks, traffic lights."""
        ground_y = h - 50
        road_h = 50

        # Ground base
        ctx.fillStyle(GROUND_COLOR)
        ctx.fillRect(0, ground_y, w, road_h)

        # Road surface
        ctx.fillStyle(ROAD_COLOR)
        ctx.fillRect(0, ground_y + 5, w, road_h - 5)

        # Sidewalk strip
        try:
            ctx.globalAlpha(0.4)
            ctx.fillStyle("#1a1a30")
            ctx.fillRect(0, ground_y, w, 5)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Lane markings — dashed center line
        ctx.fillStyle("#2a2a4a")
        line_y = ground_y + 5 + (road_h - 5) / 2
        dash_x = 0.0
        while dash_x < w:
            ctx.fillRect(dash_x, line_y, 20, 1)
            dash_x += 40

        # Second lane line (upper)
        try:
            ctx.globalAlpha(0.3)
            lane2_y = ground_y + 5 + (road_h - 5) * 0.25
            dash_x = 10.0
            while dash_x < w:
                ctx.fillRect(dash_x, lane2_y, 15, 1)
                dash_x += 50
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Crosswalks at intervals
        crosswalk_interval = max(150, w / 5)
        cx = crosswalk_interval / 2
        while cx < w:
            self._draw_crosswalk(ctx, cx, ground_y + 5, road_h - 5)
            cx += crosswalk_interval

        # Traffic lights at crosswalks
        cx = crosswalk_interval / 2
        tl_idx = 0
        while cx < w:
            self._draw_traffic_light(ctx, cx + 15, ground_y - 2, now, tl_idx)
            cx += crosswalk_interval
            tl_idx += 1

    def _draw_crosswalk(self, ctx: Any, cx: float, road_y: float, road_h: float) -> None:
        """Draw a crosswalk (zebra stripes) at the given x position."""
        stripe_w = 3
        stripe_gap = 4
        n_stripes = int(road_h / (stripe_w + stripe_gap))
        try:
            ctx.globalAlpha(0.25)
            ctx.fillStyle("#cccccc")
            for i in range(n_stripes):
                sy = road_y + i * (stripe_w + stripe_gap)
                ctx.fillRect(cx - 8, sy, 16, stripe_w)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

    def _draw_traffic_light(self, ctx: Any, x: float, y: float, now: float, idx: int) -> None:
        """Draw a traffic light with cycling colors."""
        # Pole
        ctx.fillStyle("#2a2a3a")
        ctx.fillRect(x, y - 12, 2, 14)

        # Housing
        ctx.fillStyle("#1a1a2a")
        ctx.fillRect(x - 2, y - 18, 6, 10)

        # Cycle through red/yellow/green based on time + offset
        cycle = (now * 0.5 + idx * 2.1) % 6
        if cycle < 2.5:
            light_color = "#ff2222"  # red
        elif cycle < 3.5:
            light_color = "#ffaa00"  # yellow
        else:
            light_color = "#22ff44"  # green

        try:
            ctx.globalAlpha(0.8)
            ctx.fillStyle(light_color)
            ctx.fillRect(x - 1, y - 17, 3, 3)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

    # ------------------------------------------------------------------
    # Layer 3: Buildings with architectural detail
    # ------------------------------------------------------------------

    def _draw_building(
        self, ctx: Any, entity: dict, pos: dict, now: float
    ) -> None:
        """Building with full architectural detail: walls, windows, roof, awning, antenna."""
        state = entity.get("state", "unknown")
        color = STATE_COLORS.get(state, STATE_COLORS["unknown"])
        glow = NEON_GLOW.get(state, NEON_GLOW["unknown"])

        bx, by, bw, bh = pos["x"], pos["y"], pos["w"], pos["h"]

        # Building body — dark wall color
        ctx.fillStyle(BUILDING_WALL)
        ctx.fillRect(bx, by, bw, bh)

        # Side shading (left darker, right lighter for depth)
        try:
            ctx.globalAlpha(0.15)
            ctx.fillStyle("#000000")
            ctx.fillRect(bx, by, bw * 0.15, bh)
            ctx.globalAlpha(0.08)
            ctx.fillStyle("#ffffff")
            ctx.fillRect(bx + bw * 0.85, by, bw * 0.15, bh)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Ventilation grilles on sides (horizontal lines)
        if bh > 40 and bw > 20:
            self._draw_ventilation_grilles(ctx, pos)

        # Building outline with neon glow
        try:
            if state == "warning":
                pulse = 0.5 + 0.5 * math.sin(now * 4)
                ctx.shadowBlur(6 + 10 * pulse)
            elif state == "critical":
                strobe = 0.5 + 0.5 * math.sin(now * 8)
                ctx.shadowBlur(8 + 12 * strobe)
            else:
                ctx.shadowBlur(4)
            ctx.shadowColor(glow)
        except (AttributeError, TypeError):
            pass

        ctx.strokeStyle(color)
        ctx.lineWidth(1.5)
        ctx.strokeRect(bx, by, bw, bh)

        try:
            ctx.shadowBlur(0)
        except (AttributeError, TypeError):
            pass

        # Roof cornice — visible ledge at building top
        if bh > 20 and bw > 14:
            try:
                ctx.fillStyle("#222244")
                ctx.fillRect(bx - 1, by - 2, bw + 2, 3)  # slight overhang
                ctx.globalAlpha(0.3)
                ctx.fillStyle("#3a3a5e")
                ctx.fillRect(bx - 1, by - 3, bw + 2, 1)  # lighter top edge
                ctx.globalAlpha(1.0)
            except (AttributeError, TypeError):
                pass

        # Floor separators
        if bh > 30 and bw > 14:
            self._draw_floor_lines(ctx, pos, state)

        # Windows with architectural detail
        if bh > 25 and bw > 14:
            self._draw_windows(ctx, entity, pos, state, now)

        # Roof mechanicals (HVAC units, antenna)
        if bw > 16 and bh > 20:
            self._draw_roof_details(ctx, pos, state, now)

        # Entrance awning at ground floor
        if bh > 35 and bw > 18:
            self._draw_entrance(ctx, pos, color)

        # Neon sign (service name) with flicker
        if bw > 20:
            self._draw_neon_sign(ctx, entity, pos, color, glow, now)

        # Fire/smoke for critical
        if state == "critical":
            self._draw_fire_smoke(ctx, pos, now)

    def _draw_floor_lines(self, ctx: Any, pos: dict, state: str) -> None:
        """Horizontal floor separator lines for architectural detail."""
        bx, by, bw, bh = pos["x"], pos["y"], pos["w"], pos["h"]
        floor_gap = max(12, bh / 6)
        fy = by + floor_gap
        try:
            ctx.globalAlpha(0.2)
            ctx.fillStyle("#2a2a4e")
            while fy < by + bh - 8:
                ctx.fillRect(bx + 1, fy, bw - 2, 1)
                fy += floor_gap
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

    def _draw_ventilation_grilles(self, ctx: Any, pos: dict) -> None:
        """Ventilation grilles on building sides — horizontal lines."""
        bx, by, bw, bh = pos["x"], pos["y"], pos["w"], pos["h"]
        grille_h = bh * 0.3
        grille_y = by + bh * 0.5

        # Left side grille
        try:
            ctx.globalAlpha(0.15)
            ctx.fillStyle("#3a3a5a")
            for i in range(4):
                gy = grille_y + i * 3
                if gy < by + bh - 5:
                    ctx.fillRect(bx + 2, gy, bw * 0.08, 1)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Right side grille
        try:
            ctx.globalAlpha(0.15)
            ctx.fillStyle("#3a3a5a")
            for i in range(4):
                gy = grille_y + i * 3
                if gy < by + bh - 5:
                    ctx.fillRect(bx + bw * 0.9, gy, bw * 0.08, 1)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

    def _draw_windows(
        self, ctx: Any, entity: dict, pos: dict, state: str, now: float
    ) -> None:
        """Draw window grid with individual lit/dark per window, state-based patterns.

        Spec-mandated lit percentages per state:
          healthy:  70-90% lit warm yellow (#fbbf24), subtle flicker
          running:  50-70% lit blue (#60a5fa), steady
          warning:  30-50% lit orange (#f97316), pulsing
          critical: 10-20% lit red (#ef4444), strobe
          stopped:  0-5% lit (near dark), maybe one security light
          idle:     20-30% lit dim grey (#94a3b8)
        """
        bx, by, bw, bh = pos["x"], pos["y"], pos["w"], pos["h"]

        win_w = max(3, min(5, bw / 8))
        win_h = max(3, min(5, bh / 10))
        gap_x = max(win_w + 2, bw / max(2, int(bw / 8)))
        gap_y = max(win_h + 3, bh / max(2, int(bh / 8)))

        # Stable per-entity seed so window pattern doesn't jump between frames
        entity_seed = hash(entity.get("id", "x")) % 10000

        wy = by + 5
        row = 0
        while wy < by + bh - 8:
            wx = bx + 3
            col = 0
            while wx < bx + bw - 5:
                # Deterministic per-window hash (0-99)
                win_hash = (entity_seed + row * 31 + col * 17) % 100

                # --- State-based window rendering ---
                if state == "stopped":
                    # 0-5% lit — near dark, one possible security light
                    if win_hash < 3:
                        ctx.fillStyle("#334455")  # dim security light
                    elif win_hash < 5:
                        ctx.fillStyle("#111122")  # barely visible
                    else:
                        ctx.fillStyle(WINDOW_COLOR_OFF)

                elif state == "healthy":
                    # 70-90% lit warm yellow, subtle flicker on random windows
                    if win_hash < 80:
                        ctx.fillStyle(WINDOW_COLOR_HEALTHY)
                        # Subtle flicker on ~10% of lit windows (hash 70-80)
                        if win_hash >= 70:
                            flicker = 0.6 + 0.4 * math.sin(now * 6 + win_hash)
                            try:
                                ctx.globalAlpha(flicker)
                            except (AttributeError, TypeError):
                                pass
                    else:
                        ctx.fillStyle(WINDOW_COLOR_OFF)

                elif state == "running":
                    # 50-70% lit blue (#60a5fa), steady
                    if win_hash < 60:
                        ctx.fillStyle(WINDOW_COLOR_RUNNING)
                    else:
                        ctx.fillStyle(WINDOW_COLOR_OFF)

                elif state == "warning":
                    # 30-50% lit orange (#f97316), pulsing
                    if win_hash < 40:
                        ctx.fillStyle(WINDOW_COLOR_WARNING)
                        pulse = 0.5 + 0.5 * math.sin(now * 4 + row * 0.5)
                        try:
                            ctx.globalAlpha(0.5 + 0.5 * pulse)
                        except (AttributeError, TypeError):
                            pass
                    else:
                        ctx.fillStyle(WINDOW_COLOR_OFF)

                elif state == "critical":
                    # 10-20% lit red (#ef4444), strobe
                    if win_hash < 15:
                        ctx.fillStyle(WINDOW_COLOR_CRITICAL)
                        strobe = 0.5 + 0.5 * math.sin(now * 8 + col * 1.2)
                        try:
                            ctx.globalAlpha(0.4 + 0.6 * strobe)
                        except (AttributeError, TypeError):
                            pass
                    else:
                        ctx.fillStyle(WINDOW_COLOR_OFF)

                elif state == "idle":
                    # 20-30% lit dim grey (#94a3b8)
                    if win_hash < 25:
                        ctx.fillStyle(WINDOW_COLOR_IDLE)
                    else:
                        ctx.fillStyle(WINDOW_COLOR_OFF)

                else:
                    # Unknown/other states — dim grey fallback
                    if win_hash < 20:
                        ctx.fillStyle("#334455")
                    else:
                        ctx.fillStyle(WINDOW_COLOR_OFF)

                # Draw the window fill
                ctx.fillRect(wx, wy, win_w, win_h)

                # Window frame border (subtle outline for architectural detail)
                try:
                    ctx.globalAlpha(0.25)
                    ctx.strokeStyle("#1a1a2e")
                    ctx.lineWidth(0.5)
                    ctx.strokeRect(wx, wy, win_w, win_h)
                except (AttributeError, TypeError):
                    pass

                # Reset alpha for next window
                try:
                    ctx.globalAlpha(1.0)
                except (AttributeError, TypeError):
                    pass

                wx += gap_x
                col += 1
            wy += gap_y
            row += 1

    def _draw_roof_details(self, ctx: Any, pos: dict, state: str, now: float) -> None:
        """Roof mechanicals: HVAC units, antenna, satellite dish."""
        bx, by, bw, bh = pos["x"], pos["y"], pos["w"], pos["h"]
        roof_y = by

        # HVAC unit(s) — small rectangles on roof
        hvac_w = max(3, bw * 0.12)
        hvac_h = max(2, min(5, bh * 0.05))
        ctx.fillStyle("#2a2a40")
        ctx.fillRect(bx + bw * 0.15, roof_y - 3 - hvac_h, hvac_w, hvac_h)
        if bw > 30:
            ctx.fillRect(bx + bw * 0.6, roof_y - 3 - hvac_h, hvac_w, hvac_h)

        # Antenna — only on tall buildings (>100px height)
        if bh > 100 and bw > 20:
            antenna_x = bx + bw * 0.5
            antenna_h = max(6, bh * 0.08)
            ctx.fillStyle("#3a3a5a")
            ctx.fillRect(antenna_x, roof_y - 3 - hvac_h - antenna_h, 1, antenna_h)

            # Blinking light on antenna tip
            blink = math.sin(now * 3) > 0.3
            if blink:
                try:
                    ctx.globalAlpha(0.9)
                    ctx.fillStyle("#ff2222" if state == "critical" else "#ff4444")
                    ctx.fillRect(antenna_x - 1, roof_y - 3 - hvac_h - antenna_h - 1, 2, 2)
                    ctx.globalAlpha(1.0)
                except (AttributeError, TypeError):
                    pass

        # Satellite dish (for wider buildings)
        if bw > 40:
            dish_x = bx + bw * 0.8
            dish_y = roof_y - 3 - hvac_h - 2
            try:
                ctx.globalAlpha(0.6)
                ctx.fillStyle("#3a3a5a")
                # Simple dish shape — small triangle/arc approximation
                ctx.fillRect(dish_x, dish_y - 3, 5, 1)
                ctx.fillRect(dish_x + 1, dish_y - 2, 3, 1)
                ctx.fillRect(dish_x + 2, dish_y - 1, 1, 2)
                ctx.globalAlpha(1.0)
            except (AttributeError, TypeError):
                pass

    def _draw_entrance(self, ctx: Any, pos: dict, color: str) -> None:
        """Ground floor entrance with awning and double doors."""
        bx, by, bw, bh = pos["x"], pos["y"], pos["w"], pos["h"]
        ground_y = by + bh

        # Door dimensions
        door_w = max(6, bw * 0.2)
        door_h = max(6, min(12, bh * 0.12))
        door_x = bx + (bw - door_w) / 2
        door_y = ground_y - door_h

        # Door frame (slightly larger than doors)
        ctx.fillStyle("#1a1a30")
        ctx.fillRect(door_x - 1, door_y - 1, door_w + 2, door_h + 1)

        # Double doors — two panels with center divider
        half_w = door_w / 2 - 0.5
        ctx.fillStyle("#0a0a18")
        ctx.fillRect(door_x, door_y, half_w, door_h)
        ctx.fillRect(door_x + half_w + 1, door_y, half_w, door_h)

        # Door handles (tiny bright dots)
        try:
            ctx.fillStyle(color)
            ctx.globalAlpha(0.7)
            ctx.fillRect(door_x + half_w - 1.5, door_y + door_h * 0.55, 1, 1)
            ctx.fillRect(door_x + half_w + 1.5, door_y + door_h * 0.55, 1, 1)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Awning — wider overhang with angled front edge
        awning_w = door_w + 8
        awning_x = door_x - 4
        awning_y = door_y - 4
        try:
            ctx.globalAlpha(0.4)
            ctx.fillStyle(color)
            ctx.fillRect(awning_x, awning_y, awning_w, 2)
            # Angled front lip
            ctx.globalAlpha(0.25)
            ctx.fillRect(awning_x + 1, awning_y + 2, awning_w - 2, 1)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Light spill from entrance onto ground
        try:
            ctx.globalAlpha(0.1)
            ctx.fillStyle(color)
            ctx.fillRect(door_x - 3, ground_y - 1, door_w + 6, 4)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

    def _draw_neon_sign(
        self, ctx: Any, entity: dict, pos: dict, color: str, glow: str, now: float
    ) -> None:
        """Neon sign with building name, glow, and subtle flicker.

        Spec:
        - Text rendered with glow effect (shadowBlur 8-15px)
        - Color matches entity state (green=healthy, orange=warning, red=critical)
        - Subtle flicker: random frames reduce opacity to 0.7 for 1-2 frames
        - Font: monospace, 10-12px
        - Positioned above building, not overlapping
        - Background plate: dark rounded rectangle behind text for readability
        """
        name = entity.get("name", "")[:12]
        font_size = 11  # 10-12px range
        char_w = 7  # approximate monospace char width at 11px
        sign_w = min(pos["w"] + 6, len(name) * char_w + 10)
        sign_h = 16
        sign_x = pos["x"] + (pos["w"] - sign_w) / 2
        sign_y = pos["y"] - sign_h - 4  # positioned above, not overlapping

        if sign_y < 0:
            sign_y = pos["y"] + 2

        # --- Background plate: dark rounded rectangle ---
        radius = 3
        try:
            ctx.fillStyle(NEON_SIGN_BG)
            ctx.beginPath() if hasattr(ctx, "beginPath") else None
            # Rounded rect via arcTo
            ctx.moveTo(sign_x + radius, sign_y)
            ctx.arcTo(sign_x + sign_w, sign_y, sign_x + sign_w, sign_y + sign_h, radius)
            ctx.arcTo(sign_x + sign_w, sign_y + sign_h, sign_x, sign_y + sign_h, radius)
            ctx.arcTo(sign_x, sign_y + sign_h, sign_x, sign_y, radius)
            ctx.arcTo(sign_x, sign_y, sign_x + sign_w, sign_y, radius)
            ctx.closePath() if hasattr(ctx, "closePath") else None
            ctx.fill() if hasattr(ctx, "fill") else None
        except (AttributeError, TypeError):
            # Fallback to sharp rect if arcTo not available
            ctx.fillStyle(NEON_SIGN_BG)
            ctx.fillRect(sign_x, sign_y, sign_w, sign_h)

        # --- Neon border with glow (shadowBlur 8-15px) ---
        try:
            ctx.shadowBlur(12)  # 8-15px range, centered at 12
            ctx.shadowColor(glow)
        except (AttributeError, TypeError):
            pass

        ctx.strokeStyle(color)
        ctx.lineWidth(1)
        try:
            ctx.beginPath() if hasattr(ctx, "beginPath") else None
            ctx.moveTo(sign_x + radius, sign_y)
            ctx.arcTo(sign_x + sign_w, sign_y, sign_x + sign_w, sign_y + sign_h, radius)
            ctx.arcTo(sign_x + sign_w, sign_y + sign_h, sign_x, sign_y + sign_h, radius)
            ctx.arcTo(sign_x, sign_y + sign_h, sign_x, sign_y, radius)
            ctx.arcTo(sign_x, sign_y, sign_x + sign_w, sign_y, radius)
            ctx.closePath() if hasattr(ctx, "closePath") else None
            ctx.stroke() if hasattr(ctx, "stroke") else None
        except (AttributeError, TypeError):
            ctx.strokeRect(sign_x, sign_y, sign_w, sign_h)

        # --- Text with discrete random flicker ---
        # Flicker: ~15% of frames drop opacity to 0.7, deterministic per entity+time bucket
        entity_hash = hash(entity.get("id", ""))
        frame_bucket = int(now * 10)  # 100ms buckets for 1-2 frame duration
        flicker_seed = (entity_hash + frame_bucket) % 100
        if flicker_seed < 15:
            alpha = 0.7  # dimmed frame
        else:
            alpha = 1.0  # normal frame
        try:
            ctx.globalAlpha(alpha)
        except (AttributeError, TypeError):
            pass

        # Glow on text itself
        try:
            ctx.shadowBlur(10)
            ctx.shadowColor(color)
        except (AttributeError, TypeError):
            pass

        ctx.fillStyle(color)
        ctx.font(f"{font_size}px 'Courier New', monospace")
        ctx.fillText(name, sign_x + 5, sign_y + 12)

        try:
            ctx.globalAlpha(1.0)
            ctx.shadowBlur(0)
        except (AttributeError, TypeError):
            pass

    def _draw_fire_smoke(self, ctx: Any, pos: dict, now: float) -> None:
        """Fire and smoke particles for critical buildings."""
        fire_colors = ["#ff4400", "#ff6600", "#ffaa00", "#ff2200"]
        for i in range(5):
            fx = pos["x"] + self._rng.uniform(0, pos["w"])
            fy = pos["y"] - self._rng.uniform(2, 12)
            phase = math.sin(now * 8 + i * 1.3)
            fy += phase * 3
            fc = fire_colors[i % len(fire_colors)]
            try:
                ctx.globalAlpha(0.6 + 0.3 * abs(phase))
                ctx.fillStyle(fc)
                ctx.fillRect(fx, fy, 3, 4)
                ctx.globalAlpha(1.0)
            except (AttributeError, TypeError):
                pass

        # Smoke above fire
        smoke_y = pos["y"] - 15
        for i in range(3):
            sx = pos["x"] + pos["w"] / 2 + math.sin(now * 2 + i) * 8
            sy = smoke_y - i * 6 + math.sin(now * 3 + i * 0.7) * 2
            try:
                ctx.globalAlpha(0.2 - i * 0.05)
                ctx.fillStyle("#444444")
                ctx.fillRect(sx - 4, sy, 8, 5)
                ctx.globalAlpha(1.0)
            except (AttributeError, TypeError):
                pass

    # ------------------------------------------------------------------
    # Layer 4: Rain
    # ------------------------------------------------------------------

    def _draw_rain(self, ctx: Any) -> None:
        """Vertical semi-transparent rain lines."""
        for drop in self._rain:
            drop.draw(ctx)

    # ------------------------------------------------------------------
    # Layer 2b: Ground reflections (wet road, mirrored building glow)
    # ------------------------------------------------------------------

    def _draw_ground_reflections(
        self, ctx: Any, entities: list, layout: dict, w: int, h: int, now: float
    ) -> None:
        """Wet road effect — mirrored building glow on road surface.

        - Vertical gradient 20-40px tall mirroring building glow downward
        - Neon sign colors reflected in wet road surface
        - Semi-transparent overlay (alpha 0.15-0.25)
        - Horizontal blur via multiple offset draws
        - Only on ground level, not on buildings
        """
        ground_y = h - 50
        road_y = ground_y + 5
        road_h = h - road_y

        # Base wet-road shimmer overlay (very subtle full-width sheen)
        shimmer = math.sin(now * 1.5)
        try:
            ctx.globalAlpha(0.06 + 0.02 * shimmer)
            ctx.fillStyle("#4488ff")
            ctx.fillRect(0, road_y, w, road_h)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Reflection params
        REFLECTION_H_MIN = 20
        REFLECTION_H_MAX = 40
        BLUR_OFFSETS = (-3, -1.5, 0, 1.5, 3)  # horizontal blur offsets

        # Collect neon sign positions from buildings for neon reflections
        neon_reflections: list[tuple[float, float, str]] = []

        # Mirrored glow from each building — vertical gradient
        for entity in entities:
            if entity.get("type", "") != "service":
                continue
            pos = layout.get(entity["id"])
            if not pos:
                continue
            state = entity.get("state", "unknown")
            color = STATE_COLORS.get(state, STATE_COLORS["unknown"])
            neon_color = NEON_GLOW.get(state, NEON_GLOW["unknown"])

            bx, bw, bh = pos["x"], pos["w"], pos["h"]

            # Reflection height scales with building height, clamped 20-40px
            ref_h = max(REFLECTION_H_MIN, min(REFLECTION_H_MAX, bh * 0.25))
            ref_y_start = road_y + 2

            # Draw vertical gradient: bright at top (near building base), fading down
            gradient_steps = 6
            for step in range(gradient_steps):
                frac = step / gradient_steps
                y = ref_y_start + frac * ref_h
                band_h = ref_h / gradient_steps
                alpha = (0.22 - frac * 0.18)  # 0.22 at top → 0.04 at bottom

                # Horizontal blur: draw band multiple times with x-offset
                for offset in BLUR_OFFSETS:
                    try:
                        ctx.globalAlpha(alpha * 0.25)  # split across 5 offsets
                        ctx.fillStyle(neon_color)
                        ctx.fillRect(bx + offset, y, bw, band_h + 1)
                        ctx.globalAlpha(1.0)
                    except (AttributeError, TypeError):
                        pass

            # Track neon sign color for secondary reflections
            neon_reflections.append((bx + bw * 0.5, bw * 0.8, neon_color))

        # Neon sign color reflections — elongated horizontal streaks on road
        for nx, nw, nc in neon_reflections:
            streak_w = nw * 1.5
            streak_h = min(road_h - 4, 15)
            streak_y = road_y + 8

            for offset in BLUR_OFFSETS:
                try:
                    ctx.globalAlpha(0.18 * 0.25)  # blur split
                    ctx.fillStyle(nc)
                    ctx.fillRect(nx - streak_w / 2 + offset, streak_y, streak_w, streak_h)
                    ctx.globalAlpha(1.0)
                except (AttributeError, TypeError):
                    pass

        # Ambient neon reflections (pooled from sign palette) — wide soft glow
        reflection_colors = ["#ff00ff", "#00ffff", "#ffff00"]
        for i, rc in enumerate(reflection_colors):
            rx = (w / (len(reflection_colors) + 1)) * (i + 1)
            rw = 50 + 25 * math.sin(now * 2 + i)
            ref_h_amb = min(road_h - 4, 30)

            for offset in BLUR_OFFSETS:
                try:
                    ctx.globalAlpha(0.20 * 0.25)
                    ctx.fillStyle(rc)
                    ctx.fillRect(rx - rw / 2 + offset, road_y + 5, rw, ref_h_amb)
                    ctx.globalAlpha(1.0)
                except (AttributeError, TypeError):
                    pass

    # ------------------------------------------------------------------
    # District / Block drawing
    # ------------------------------------------------------------------

    def _draw_district(self, ctx: Any, entity: dict, pos: dict) -> None:
        """District border with neon glow."""
        color = STATE_COLORS.get(entity.get("state", "unknown"), STATE_COLORS["unknown"])
        glow = NEON_GLOW.get(entity.get("state", "unknown"), NEON_GLOW["unknown"])

        try:
            ctx.shadowBlur(12)
            ctx.shadowColor(glow)
        except (AttributeError, TypeError):
            pass

        ctx.strokeStyle(color)
        ctx.lineWidth(2)
        ctx.strokeRect(pos["x"] + 2, pos["y"] + 2, pos["w"] - 4, pos["h"] - 4)

        try:
            ctx.shadowBlur(0)
        except (AttributeError, TypeError):
            pass

        # District label — neon sign style
        ctx.fillStyle(NEON_SIGN_BG)
        label_w = min(160, pos["w"] - 16)
        ctx.fillRect(pos["x"] + 8, pos["y"] + 4, label_w, 22)

        try:
            ctx.shadowBlur(8)
            ctx.shadowColor(glow)
        except (AttributeError, TypeError):
            pass

        ctx.fillStyle(color)
        ctx.font("bold 13px 'Courier New', monospace")
        ctx.fillText(entity.get("name", "")[:20], pos["x"] + 14, pos["y"] + 19)

        try:
            ctx.shadowBlur(0)
        except (AttributeError, TypeError):
            pass

    def _draw_block(self, ctx: Any, entity: dict, pos: dict) -> None:
        """Block (node) — dark pad with subtle border."""
        ctx.fillStyle("#0a0a18")
        ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])

        ctx.strokeStyle("#1a1a3a")
        ctx.lineWidth(1)
        ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

        # Block label
        ctx.fillStyle("#4a4a6a")
        ctx.font("10px 'Courier New', monospace")
        ctx.fillText(entity.get("name", "")[:16], pos["x"] + 4, pos["y"] + 14)

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _darken(hex_color: str, factor: float) -> str:
        """Darken a hex color by a factor (0=black, 1=original)."""
        r, g, b = _hex_to_rgb(hex_color)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ------------------------------------------------------------------
    # Interface methods
    # ------------------------------------------------------------------

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Generate tooltip text for an entity."""
        lines = [
            f"{entity.get('name', '?')} ({entity.get('type', '?')})",
            f"State: {entity.get('state', 'unknown')}",
        ]
        m = entity.get("metrics") or {}
        if "cpu" in m:
            lines.append(f"CPU: {m['cpu']}%")
        if "mem" in m:
            lines.append(f"Mem: {m['mem']}%")
        if "cpu_pct" in m:
            lines.append(f"CPU: {m['cpu_pct']}%")
        if "mem_pct" in m:
            lines.append(f"Mem: {m['mem_pct']}%")
        if "req_per_sec" in m:
            lines.append(f"RPS: {m['req_per_sec']}")
        if "error_rate" in m:
            lines.append(f"Errors: {m['error_rate'] * 100:.1f}%")
        if "count" in m:
            lines.append(f"Count: {m['count']}")
        if "uptime_hrs" in m:
            lines.append(f"Uptime: {m['uptime_hrs']}h")
        return "\n".join(lines)

    def hit_test(self, entity: dict[str, Any], x: int, y: int) -> bool:
        """Check if (x,y) falls within this entity's layout bounds."""
        pos = self._layout.get(entity.get("id"))
        if not pos:
            return False
        return (
            pos["x"] <= x <= pos["x"] + pos["w"]
            and pos["y"] <= y <= pos["y"] + pos["h"]
        )

    def config(self) -> dict[str, Any]:
        """Return metaphor configuration metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "state_colors": STATE_COLORS,
            "neon_glow": NEON_GLOW,
            "mappings": {
                "cluster": "district",
                "node": "block",
                "service": "building",
            },
            "features": [
                "neon_glow",
                "rain_reflections",
                "traffic_particles",
                "fire_smoke_critical",
                "pulsing_warning",
                "neon_signs",
                "building_height_cpu",
                "building_width_memory",
                "sky_stars",
                "far_buildings_skyline",
                "road_network",
                "crosswalks",
                "traffic_lights",
                "rain_effect",
                "ground_reflections",
                "architectural_detail",
                "window_patterns",
                "roof_mechanicals",
                "entrance_awning",
                "antenna_blink",
            ],
        }
