"""City metaphor renderer — Neon Cyberpunk aesthetic.

Cluster→District, Node→Block, Service→Building.
Building height = CPU usage, width = memory usage.
Neon glow, rain reflections, traffic particles, fire/smoke for critical.
"""
from __future__ import annotations

import math
import random
import time
from typing import Any

from engine.metaphors.base import MetaphorRenderer


# State → neon color map
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

# Neon glow colors per state (brighter version for glow)
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

# Background
BG_COLOR = "#0a0a1a"
GROUND_COLOR = "#0d0d22"
ROAD_COLOR = "#111128"

# Building constants
MIN_BUILDING_W = 12
MAX_BUILDING_W = 80
WINDOW_COLOR_HEALTHY = "#fbbf24"
WINDOW_COLOR_WARNING = "#f97316"
WINDOW_COLOR_OFF = "#1a1a2e"

# Neon sign
NEON_SIGN_BG = "#0f0f2a"
NEON_SIGN_BORDER = "#ff00ff"

# Traffic particle
TRAFFIC_COLORS = ["#ff00ff", "#00ffff", "#ffff00", "#ff4488"]


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


class TrafficParticle:
    """A single traffic particle moving along a road."""

    def __init__(self, x: float, y: float, road_y: float, speed: float, color: str):
        self.x = x
        self.y = y
        self.road_y = road_y
        self.speed = speed
        self.color = color
        self.size = random.uniform(1.5, 3.5)

    def update(self, dt: float, canvas_w: int) -> None:
        self.x += self.speed * dt
        if self.x > canvas_w + 10:
            self.x = -10
        elif self.x < -10:
            self.x = canvas_w + 10

    def draw(self, ctx: Any) -> None:
        try:
            ctx.fillStyle(self.color)
            ctx.globalAlpha(0.8)
            ctx.fillRect(self.x, self.y, self.size, self.size * 0.5)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass


class CityRenderer(MetaphorRenderer):
    """Neon Cyberpunk city metaphor.

    Clusters are districts with neon borders.
    Nodes are blocks (dark pads).
    Services are buildings — height=CPU, width=memory.
    Neon signs label services.
    Rain-slicked road reflections shimmer.
    Traffic particles flow on roads.
    Critical buildings emit fire/smoke.
    Warning buildings pulse with glow.
    """

    name = "city"
    description = "Infrastructure as a neon cyberpunk city"

    def __init__(self):
        self._layout: dict[str, dict[str, float]] = {}
        self._particles: list[TrafficParticle] = []
        self._time_offset: float = 0.0
        self._rng = random.Random(42)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compute_layout(
        self, entities: list[dict[str, Any]], w: int, h: int
    ) -> dict[str, dict[str, float]]:
        """Compute positions for all entities. Handles 0-500 entities.

        Building height = CPU (0-100%), width = memory (0-100%).
        """
        layout: dict[str, dict[str, float]] = {}
        if not entities:
            self._layout = layout
            return layout

        # Cap to 500 entities for performance
        entities = entities[:500]

        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        if not roots:
            # No hierarchy — treat all as flat
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

            block_h = (h - 60) / max(len(children), 1)  # reserve 60px for ground/roads

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

                    # Building width = memory, height = CPU
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
        self._init_particles(w, h)
        return layout

    # ------------------------------------------------------------------
    # Traffic particles
    # ------------------------------------------------------------------

    def _init_particles(self, w: int, h: int) -> None:
        """Create traffic particles on the road strip."""
        self._particles = []
        road_y = h - 30
        n_particles = max(5, min(40, w // 30))
        for _ in range(n_particles):
            px = self._rng.uniform(0, w)
            py = road_y + self._rng.uniform(-5, 15)
            speed = self._rng.uniform(30, 120) * (1 if self._rng.random() > 0.5 else -1)
            color = self._rng.choice(TRAFFIC_COLORS)
            self._particles.append(TrafficParticle(px, py, road_y, speed, color))

    def _update_particles(self, dt: float, w: int) -> None:
        for p in self._particles:
            p.update(dt, w)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the neon cyberpunk city."""
        layout = self.compute_layout(entities, w, h)
        now = time.monotonic()
        dt = now - self._time_offset if self._time_offset > 0 else 0.016
        self._time_offset = now
        self._update_particles(dt, w)

        # === Background ===
        self._draw_background(ctx, w, h)

        # === Districts (clusters) ===
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            etype = entity.get("type", "")
            if etype == "cluster":
                self._draw_district(ctx, entity, pos)

        # === Blocks (nodes) ===
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            etype = entity.get("type", "")
            if etype == "node":
                self._draw_block(ctx, entity, pos)

        # === Buildings (services) ===
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            etype = entity.get("type", "")
            if etype == "service":
                self._draw_building(ctx, entity, pos, now)

        # === Roads and reflections ===
        self._draw_roads(ctx, w, h, now)

        # === Traffic particles ===
        for p in self._particles:
            p.draw(ctx)

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_background(self, ctx: Any, w: int, h: int) -> None:
        """Dark sky with subtle gradient."""
        ctx.fillStyle(BG_COLOR)
        ctx.fillRect(0, 0, w, h)

        # Subtle sky gradient (darker at top, slightly lighter near horizon)
        try:
            ctx.globalAlpha(0.15)
            ctx.fillStyle("#1a0a3a")
            ctx.fillRect(0, 0, w, h * 0.4)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

    def _draw_district(self, ctx: Any, entity: dict, pos: dict) -> None:
        """District border with neon glow."""
        color = STATE_COLORS.get(entity.get("state", "unknown"), STATE_COLORS["unknown"])
        glow = NEON_GLOW.get(entity.get("state", "unknown"), NEON_GLOW["unknown"])

        # Neon glow border
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

    def _draw_building(
        self, ctx: Any, entity: dict, pos: dict, now: float
    ) -> None:
        """Building with neon cyberpunk details."""
        state = entity.get("state", "unknown")
        color = STATE_COLORS.get(state, STATE_COLORS["unknown"])
        glow = NEON_GLOW.get(state, NEON_GLOW["unknown"])

        # Building body — dark with colored accent
        body_color = self._darken(color, 0.3)
        ctx.fillStyle(body_color)
        ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])

        # Building outline with neon glow
        try:
            if state == "warning":
                # Pulsing glow for warning
                pulse = 0.5 + 0.5 * math.sin(now * 4)
                ctx.shadowBlur(6 + 10 * pulse)
            elif state == "critical":
                ctx.shadowBlur(15)
            else:
                ctx.shadowBlur(4)
            ctx.shadowColor(glow)
        except (AttributeError, TypeError):
            pass

        ctx.strokeStyle(color)
        ctx.lineWidth(1.5)
        ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

        try:
            ctx.shadowBlur(0)
        except (AttributeError, TypeError):
            pass

        # Windows
        if pos["h"] > 25 and pos["w"] > 14:
            self._draw_windows(ctx, entity, pos, state)

        # Neon sign (service name)
        if pos["w"] > 20:
            self._draw_neon_sign(ctx, entity, pos, color, glow)

        # Fire/smoke for critical
        if state == "critical":
            self._draw_fire_smoke(ctx, pos, now)

    def _draw_windows(
        self, ctx: Any, entity: dict, pos: dict, state: str
    ) -> None:
        """Draw window grid on building."""
        win_w = 4
        win_h = 4
        gap_x = 8
        gap_y = 10

        if state in ("healthy", "running"):
            win_color = WINDOW_COLOR_HEALTHY
        elif state == "warning":
            win_color = WINDOW_COLOR_WARNING
        elif state == "critical":
            win_color = "#ff4444"
        else:
            win_color = WINDOW_COLOR_OFF

        wy = pos["y"] + 6
        while wy < pos["y"] + pos["h"] - 8:
            wx = pos["x"] + 4
            while wx < pos["x"] + pos["w"] - 6:
                # Some windows randomly off for realism
                is_lit = state not in ("stopped", "unknown")
                if is_lit and self._rng.random() < 0.15:
                    ctx.fillStyle(WINDOW_COLOR_OFF)
                else:
                    ctx.fillStyle(win_color)
                ctx.fillRect(wx, wy, win_w, win_h)
                wx += gap_x
            wy += gap_y

    def _draw_neon_sign(
        self, ctx: Any, entity: dict, pos: dict, color: str, glow: str
    ) -> None:
        """Neon sign above or on building."""
        name = entity.get("name", "")[:12]
        sign_w = min(pos["w"] + 6, len(name) * 7 + 8)
        sign_h = 14
        sign_x = pos["x"] + (pos["w"] - sign_w) / 2
        sign_y = pos["y"] - sign_h - 2

        if sign_y < 0:
            sign_y = pos["y"] + 2

        # Sign background
        ctx.fillStyle(NEON_SIGN_BG)
        ctx.fillRect(sign_x, sign_y, sign_w, sign_h)

        # Neon border
        try:
            ctx.shadowBlur(6)
            ctx.shadowColor(glow)
        except (AttributeError, TypeError):
            pass

        ctx.strokeStyle(color)
        ctx.lineWidth(1)
        ctx.strokeRect(sign_x, sign_y, sign_w, sign_h)

        # Text
        ctx.fillStyle(color)
        ctx.font("bold 9px 'Courier New', monospace")
        ctx.fillText(name, sign_x + 4, sign_y + 10)

        try:
            ctx.shadowBlur(0)
        except (AttributeError, TypeError):
            pass

    def _draw_fire_smoke(self, ctx: Any, pos: dict, now: float) -> None:
        """Fire and smoke particles for critical buildings."""
        # Fire at base
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

    def _draw_roads(self, ctx: Any, w: int, h: int, now: float) -> None:
        """Road strip at bottom with rain-slicked reflections."""
        road_y = h - 40
        road_h = 40

        # Road surface
        ctx.fillStyle(ROAD_COLOR)
        ctx.fillRect(0, road_y, w, road_h)

        # Road lines
        ctx.strokeStyle("#2a2a4a")
        ctx.lineWidth(1)
        line_y = road_y + road_h / 2
        dash_x = 0
        while dash_x < w:
            ctx.fillRect(dash_x, line_y, 20, 1)
            dash_x += 40

        # Rain-slicked reflections (shimmer)
        shimmer_phase = math.sin(now * 1.5)
        try:
            ctx.globalAlpha(0.04 + 0.02 * shimmer_phase)
            ctx.fillStyle("#4488ff")
            ctx.fillRect(0, road_y, w, road_h)
            ctx.globalAlpha(1.0)
        except (AttributeError, TypeError):
            pass

        # Neon reflections on wet road
        reflection_colors = ["#ff00ff", "#00ffff", "#ffff00"]
        for i, rc in enumerate(reflection_colors):
            rx = (w / (len(reflection_colors) + 1)) * (i + 1)
            rw = 40 + 20 * math.sin(now * 2 + i)
            try:
                ctx.globalAlpha(0.06 + 0.03 * math.sin(now * 3 + i * 1.5))
                ctx.fillStyle(rc)
                ctx.fillRect(rx - rw / 2, road_y + 5, rw, road_h - 10)
                ctx.globalAlpha(1.0)
            except (AttributeError, TypeError):
                pass

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
            ],
        }
