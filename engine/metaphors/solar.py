"""Solar metaphor renderer — Cluster→Solar System, Node→Star/Planet,
Service→Orbit/Satellite, Container→Moon/Asteroid, Process→Comet/Debris.

Visual design following VISUAL_GUIDELINES.md:
- Deep space background (dark gradient with twinkling stars)
- Central sun with corona/flares (animated glow pulsation)
- Planets orbiting the sun (animated rotation based on activity)
- Orbital paths drawn as faint elliptical rings
- Moons orbiting planets (smaller animated circles)
- Solar flares erupting from sun surface (particle effects)
- Nebula clouds in background (soft colored gradients)
- Asteroid belt between orbits (small rotating debris)
- Comet trails for high-activity entities (streaking particles)
- Solar wind particles flowing outward (animated dots)
- Eclipse effects for stopped/critical entities
- Star field parallax background
- Heat shimmer for high CPU entities
- Gravitational lensing effect around massive entities
"""
from __future__ import annotations
import math
import time as _time
import random
from typing import Any
from engine.metaphors.base import MetaphorRenderer


# Health → glow color (solar palette)
HEALTH_COLORS = {
    "healthy": "#22c55e",   # green glow
    "running": "#16a34a",   # active green
    "idle": "#86efac",      # pale green
    "warning": "#eab308",   # caution yellow
    "degraded": "#f97316",  # orange alert
    "critical": "#dc2626",  # danger red
    "stopped": "#7f1d1d",   # dark red (eclipse)
    "pending": "#fbbf24",   # amber
    "scaling": "#f59e0b",   # growing amber
    "unknown": "#6b7280",   # grey
}

# Space background
SPACE_DARK = "#030712"       # near-black
SPACE_MID = "#0f172a"        # dark slate
SPACE_LIGHT = "#1e293b"      # slate

# Star colors
STAR_COLORS = ["#ffffff", "#fef3c7", "#dbeafe", "#fde68a", "#e0e7ff", "#c7d2fe"]

# Sun colors
SUN_CORE = "#fbbf24"         # bright yellow core
SUN_MID = "#f59e0b"          # amber mid
SUN_CORONA = "#f97316"       # orange corona
SUN_FLARE = "#fef3c7"        # pale yellow flare
SUN_PROMINENCE = "#dc2626"   # red prominence

# Planet colors (by orbit distance)
PLANET_COLORS = [
    "#94a3b8",  # grey (mercury-like)
    "#f59e0b",  # orange (venus-like)
    "#3b82f6",  # blue (earth-like)
    "#dc2626",  # red (mars-like)
    "#eab308",  # yellow (jupiter-like)
    "#a78bfa",  # purple (neptune-like)
]

# Orbit ring
ORBIT_COLOR = "rgba(148, 163, 184, 0.15)"  # faint grey-blue
ORBIT_ACTIVE = "rgba(59, 130, 246, 0.25)"  # active orbit highlight

# Moon
MOON_COLOR = "#94a3b8"
MOON_SHADOW = "#475569"

# Nebula
NEBULA_COLORS = [
    "rgba(139, 92, 246, 0.08)",   # purple nebula
    "rgba(59, 130, 246, 0.06)",   # blue nebula
    "rgba(236, 72, 153, 0.05)",   # pink nebula
    "rgba(34, 197, 94, 0.04)",    # green nebula
]

# Comet
COMET_HEAD = "#fef3c7"
COMET_TAIL = "rgba(254, 243, 199, 0.4)"

# Solar wind
SOLAR_WIND_COLOR = "rgba(251, 191, 36, 0.3)"

# Asteroid
ASTEROID_COLOR = "#78716c"
ASTEROID_DARK = "#44403c"

# Eclipse
ECLIPSE_SHADOW = "rgba(0, 0, 0, 0.8)"
ECLIPSE_CORONA = "rgba(251, 191, 36, 0.4)"

# Gravitational lens
LENS_COLOR = "rgba(148, 163, 184, 0.1)"


class SolarRenderer(MetaphorRenderer):
    """Renders entities as a solar system with sun, planets, orbits, and space effects."""

    def __init__(self):
        self._time_offset = 0.0
        self._planet_angles = {}     # entity_id -> angle
        self._moon_angles = {}       # entity_id -> angle
        self._star_positions = []    # background star field
        self._solar_flare_particles = []
        self._comet_trails = {}      # entity_id -> [(x, y, alpha)]
        self._nebula_offsets = []    # nebula cloud positions
        self._asteroid_angles = {}   # entity_id -> angle
        self._last_update = _time.time()
        self._stars_initialized = False

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render solar system with sun, planets, orbits, and space effects."""
        now = _time.time()
        dt = now - self._last_update
        self._last_update = now
        self._time_offset += dt

        # Initialize star field once
        if not self._stars_initialized:
            self._init_star_field(w, h)
            self._init_nebulae(w, h)
            self._stars_initialized = True

        # Organize entities by type
        clusters = [e for e in entities if e.get("type") == "cluster"]
        nodes = [e for e in entities if e.get("type") == "node"]
        services = [e for e in entities if e.get("type") == "service"]
        containers = [e for e in entities if e.get("type") == "container"]
        processes = [e for e in entities if e.get("type") == "process"]

        # Background: deep space
        self._draw_space(ctx, w, h)

        # Star field (twinkling)
        self._draw_stars(ctx, w, h)

        # Nebula clouds
        self._draw_nebulae(ctx, w, h)

        # Solar wind particles
        self._draw_solar_wind(ctx, entities, w, h)

        # Draw solar systems (clusters) — each is a sun with orbiting planets
        for i, cluster in enumerate(clusters):
            cx = (w / (len(clusters) + 1)) * (i + 1)
            cy = h * 0.35
            self._draw_solar_system(ctx, cluster, cx, cy, w * 0.2, h * 0.35)

        # Draw stars/planets (nodes)
        for i, node in enumerate(nodes):
            x = (w / (len(nodes) + 1)) * (i + 1)
            y = h * 0.55
            self._draw_planet(ctx, node, x, y, min(w * 0.04, h * 0.08))

        # Draw orbits/satellites (services) — orbital rings
        for i, service in enumerate(services):
            x = (w / (len(services) + 1)) * (i + 1)
            y = h * 0.55
            self._draw_orbit(ctx, service, x, y, w * 0.06, h * 0.12)

        # Draw moons/asteroids (containers)
        for i, container in enumerate(containers):
            x = (w / (len(containers) + 1)) * (i + 1)
            y = h * 0.75
            self._draw_moon(ctx, container, x, y, h * 0.03)

        # Draw comets/debris (processes)
        for i, process in enumerate(processes):
            x = (w / (len(processes) + 1)) * (i + 1)
            y = h * 0.9
            self._draw_comet(ctx, process, x, y, h * 0.02)

        # Asteroid belt
        self._draw_asteroid_belt(ctx, entities, w, h)

        # Solar flares from sun
        self._draw_solar_flares(ctx, entities, w, h)

        # Comet trails for high activity
        self._draw_comet_trails(ctx, entities, w, h)

        # Eclipse effects for stopped/critical
        self._draw_eclipses(ctx, entities, w, h)

    def _init_star_field(self, w: int, h: int) -> None:
        """Initialize background star positions."""
        self._star_positions = []
        for _ in range(200):
            self._star_positions.append({
                "x": random.uniform(0, w),
                "y": random.uniform(0, h),
                "size": random.uniform(0.5, 2.5),
                "color": random.choice(STAR_COLORS),
                "twinkle_speed": random.uniform(1.0, 4.0),
                "twinkle_offset": random.uniform(0, math.pi * 2),
            })

    def _init_nebulae(self, w: int, h: int) -> None:
        """Initialize nebula cloud positions."""
        self._nebula_offsets = []
        for _ in range(5):
            self._nebula_offsets.append({
                "x": random.uniform(w * 0.1, w * 0.9),
                "y": random.uniform(h * 0.1, h * 0.6),
                "radius": random.uniform(60, 150),
                "color": random.choice(NEBULA_COLORS),
            })

    def _draw_space(self, ctx: Any, w: int, h: int) -> None:
        """Draw deep space background gradient."""
        for y in range(h):
            t = y / h
            r1, g1, b1 = self._hex_to_rgb(SPACE_DARK)
            r2, g2, b2 = self._hex_to_rgb(SPACE_MID)
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            ctx.fillStyle = f"rgb({r},{g},{b})"
            ctx.fillRect(0, y, w, 1)

    def _draw_stars(self, ctx: Any, w: int, h: int) -> None:
        """Draw twinkling background stars."""
        for star in self._star_positions:
            twinkle = 0.4 + 0.6 * abs(math.sin(
                self._time_offset * star["twinkle_speed"] + star["twinkle_offset"]
            ))
            ctx.globalAlpha = twinkle
            ctx.fillStyle = star["color"]
            ctx.beginPath()
            ctx.arc(star["x"], star["y"], star["size"], 0, math.pi * 2)
            ctx.fill()
        ctx.globalAlpha = 1.0

    def _draw_nebulae(self, ctx: Any, w: int, h: int) -> None:
        """Draw soft nebula clouds in background."""
        for nebula in self._nebula_offsets:
            # Soft radial gradient
            steps = 20
            for s in range(steps, 0, -1):
                t = s / steps
                radius = nebula["radius"] * t
                alpha = (1 - t) * 0.3
                ctx.globalAlpha = alpha
                ctx.fillStyle = nebula["color"]
                ctx.beginPath()
                ctx.arc(
                    nebula["x"] + math.sin(self._time_offset * 0.1) * 5,
                    nebula["y"] + math.cos(self._time_offset * 0.08) * 3,
                    radius, 0, math.pi * 2
                )
                ctx.fill()
        ctx.globalAlpha = 1.0

    def _draw_solar_system(self, ctx: Any, cluster: dict, cx: float, cy: float,
                           sys_w: float, sys_h: float) -> None:
        """Draw a solar system: central sun with orbiting planets."""
        state = cluster.get("state", "unknown")
        color = HEALTH_COLORS.get(state, HEALTH_COLORS["unknown"])
        entity_id = cluster.get("id", "")

        # Orbital rings (faint)
        for orbit_r in [0.3, 0.5, 0.7, 0.9]:
            rx = sys_w * orbit_r
            ry = sys_h * orbit_r * 0.4  # elliptical
            ctx.strokeStyle = ORBIT_COLOR
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.ellipse(cx, cy, rx, ry, 0, 0, math.pi * 2)
            ctx.stroke()

        # Central sun
        sun_radius = sys_w * 0.12

        # Corona glow (pulsating)
        pulse = 1.0 + 0.15 * math.sin(self._time_offset * 2)
        for ring in range(4, 0, -1):
            glow_r = sun_radius * (1 + ring * 0.4) * pulse
            ctx.globalAlpha = 0.15 / ring
            ctx.fillStyle = SUN_CORONA
            ctx.beginPath()
            ctx.arc(cx, cy, glow_r, 0, math.pi * 2)
            ctx.fill()
        ctx.globalAlpha = 1.0

        # Sun core gradient
        for s in range(10, 0, -1):
            t = s / 10
            r = sun_radius * t
            if t > 0.6:
                c = SUN_CORONA
            elif t > 0.3:
                c = SUN_MID
            else:
                c = SUN_CORE
            ctx.fillStyle = c
            ctx.beginPath()
            ctx.arc(cx, cy, r, 0, math.pi * 2)
            ctx.fill()

        # Sun surface detail (granulation)
        for i in range(6):
            angle = (math.pi * 2 / 6) * i + self._time_offset * 0.3
            gx = cx + math.cos(angle) * sun_radius * 0.5
            gy = cy + math.sin(angle) * sun_radius * 0.5
            ctx.globalAlpha = 0.3
            ctx.fillStyle = SUN_FLARE
            ctx.beginPath()
            ctx.arc(gx, gy, sun_radius * 0.15, 0, math.pi * 2)
            ctx.fill()
        ctx.globalAlpha = 1.0

        # Orbiting mini-planets for this cluster
        for p in range(3):
            if entity_id not in self._planet_angles:
                self._planet_angles[entity_id] = {}
            orbit_r = sys_w * (0.3 + p * 0.2)
            speed = 0.5 - p * 0.1
            angle = self._time_offset * speed + p * 2.1
            px = cx + math.cos(angle) * orbit_r
            py = cy + math.sin(angle) * orbit_r * 0.4  # elliptical
            planet_r = 3 + p
            ctx.fillStyle = PLANET_COLORS[p % len(PLANET_COLORS)]
            ctx.beginPath()
            ctx.arc(px, py, planet_r, 0, math.pi * 2)
            ctx.fill()

        # Label
        ctx.fillStyle = color
        ctx.font = "bold 13px monospace"
        ctx.textAlign = "center"
        ctx.fillText(cluster.get("name", "System"), cx, cy - sys_h * 0.5 - 10)

    def _draw_planet(self, ctx: Any, node: dict, x: float, y: float,
                     radius: float) -> None:
        """Draw a planet with atmosphere and health-based coloring."""
        state = node.get("state", "unknown")
        color = HEALTH_COLORS.get(state, HEALTH_COLORS["unknown"])
        cpu = node.get("metrics", {}).get("cpu", 0)
        entity_id = node.get("id", "")
        node_idx = hash(entity_id) % len(PLANET_COLORS)

        # Planet body
        base_color = PLANET_COLORS[node_idx]
        ctx.fillStyle = base_color
        ctx.beginPath()
        ctx.arc(x, y, radius, 0, math.pi * 2)
        ctx.fill()

        # Atmosphere glow (based on health)
        ctx.globalAlpha = 0.3
        ctx.fillStyle = color
        ctx.beginPath()
        ctx.arc(x, y, radius * 1.3, 0, math.pi * 2)
        ctx.fill()
        ctx.globalAlpha = 1.0

        # Surface detail (bands for gas giants, craters for rocky)
        if radius > 10:
            # Atmospheric bands
            for b in range(3):
                band_y = y - radius * 0.5 + b * radius * 0.4
                ctx.globalAlpha = 0.2
                ctx.fillStyle = "#ffffff" if b % 2 == 0 else "#000000"
                ctx.beginPath()
                ctx.ellipse(x, band_y, radius * 0.9, radius * 0.1, 0, 0, math.pi * 2)
                ctx.fill()
            ctx.globalAlpha = 1.0

        # Heat shimmer for high CPU
        if cpu > 0.7:
            shimmer = math.sin(self._time_offset * 5 + hash(entity_id)) * 2
            ctx.globalAlpha = 0.2
            ctx.fillStyle = "#f97316"
            ctx.beginPath()
            ctx.arc(x + shimmer, y - radius * 0.3, radius * 0.4, 0, math.pi * 2)
            ctx.fill()
            ctx.globalAlpha = 1.0

        # Shadow (terminator line)
        ctx.fillStyle = "rgba(0, 0, 0, 0.3)"
        ctx.beginPath()
        ctx.arc(x + radius * 0.2, y, radius, -math.pi * 0.5, math.pi * 0.5)
        ctx.fill()

        # Label
        ctx.fillStyle = "#e2e8f0"
        ctx.font = "11px monospace"
        ctx.textAlign = "center"
        ctx.fillText(node.get("name", ""), x, y + radius + 14)

    def _draw_orbit(self, ctx: Any, service: dict, x: float, y: float,
                    orbit_w: float, orbit_h: float) -> None:
        """Draw an orbital ring with a satellite."""
        state = service.get("state", "unknown")
        color = HEALTH_COLORS.get(state, HEALTH_COLORS["unknown"])
        entity_id = service.get("id", "")

        # Animate satellite position
        if entity_id not in self._planet_angles:
            self._planet_angles[entity_id] = random.uniform(0, math.pi * 2)
        activity = service.get("metrics", {}).get("cpu", 0.3)
        speed = 0.5 + activity * 2
        self._planet_angles[entity_id] += speed * 0.02
        angle = self._planet_angles[entity_id]

        # Orbit ring
        ring_color = ORBIT_ACTIVE if state in ["running", "healthy"] else ORBIT_COLOR
        ctx.strokeStyle = ring_color
        ctx.lineWidth = 1.5
        ctx.beginPath()
        ctx.ellipse(x, y, orbit_w, orbit_h, 0, 0, math.pi * 2)
        ctx.stroke()

        # Satellite
        sat_x = x + math.cos(angle) * orbit_w
        sat_y = y + math.sin(angle) * orbit_h
        sat_r = 4

        # Satellite body
        ctx.fillStyle = color
        ctx.beginPath()
        ctx.arc(sat_x, sat_y, sat_r, 0, math.pi * 2)
        ctx.fill()

        # Satellite solar panels
        panel_w = 8
        panel_h = 3
        ctx.fillStyle = "#3b82f6"
        ctx.fillRect(sat_x - panel_w - sat_r, sat_y - panel_h / 2, panel_w, panel_h)
        ctx.fillRect(sat_x + sat_r, sat_y - panel_h / 2, panel_w, panel_h)

        # Panel grid lines
        ctx.strokeStyle = "#1d4ed8"
        ctx.lineWidth = 0.5
        for px in range(3):
            lx = sat_x - panel_w - sat_r + (panel_w / 3) * px
            ctx.beginPath()
            ctx.moveTo(lx, sat_y - panel_h / 2)
            ctx.lineTo(lx, sat_y + panel_h / 2)
            ctx.stroke()
            lx2 = sat_x + sat_r + (panel_w / 3) * px
            ctx.beginPath()
            ctx.moveTo(lx2, sat_y - panel_h / 2)
            ctx.lineTo(lx2, sat_y + panel_h / 2)
            ctx.stroke()

        # Label
        ctx.fillStyle = "#94a3b8"
        ctx.font = "10px monospace"
        ctx.textAlign = "center"
        ctx.fillText(service.get("name", ""), x, y + orbit_h + 12)

    def _draw_moon(self, ctx: Any, container: dict, x: float, y: float,
                   radius: float) -> None:
        """Draw a moon orbiting near its position."""
        state = container.get("state", "unknown")
        color = HEALTH_COLORS.get(state, HEALTH_COLORS["unknown"])
        entity_id = container.get("id", "")

        # Animate moon orbit
        if entity_id not in self._moon_angles:
            self._moon_angles[entity_id] = random.uniform(0, math.pi * 2)
        self._moon_angles[entity_id] += 0.03
        angle = self._moon_angles[entity_id]

        orbit_r = radius * 3
        mx = x + math.cos(angle) * orbit_r
        my = y + math.sin(angle) * orbit_r * 0.5

        # Moon body
        ctx.fillStyle = MOON_COLOR
        ctx.beginPath()
        ctx.arc(mx, my, radius, 0, math.pi * 2)
        ctx.fill()

        # Craters
        ctx.fillStyle = MOON_SHADOW
        for c in range(3):
            cx_off = math.cos(c * 2.1) * radius * 0.4
            cy_off = math.sin(c * 2.1) * radius * 0.4
            ctx.beginPath()
            ctx.arc(mx + cx_off, my + cy_off, radius * 0.2, 0, math.pi * 2)
            ctx.fill()

        # Shadow
        ctx.fillStyle = "rgba(0, 0, 0, 0.25)"
        ctx.beginPath()
        ctx.arc(mx + radius * 0.3, my, radius, -math.pi * 0.5, math.pi * 0.5)
        ctx.fill()

        # Health glow
        ctx.globalAlpha = 0.3
        ctx.fillStyle = color
        ctx.beginPath()
        ctx.arc(mx, my, radius * 1.4, 0, math.pi * 2)
        ctx.fill()
        ctx.globalAlpha = 1.0

        # Label
        ctx.fillStyle = "#94a3b8"
        ctx.font = "9px monospace"
        ctx.textAlign = "center"
        ctx.fillText(container.get("name", ""), mx, my + radius + 10)

    def _draw_comet(self, ctx: Any, process: dict, x: float, y: float,
                    size: float) -> None:
        """Draw a comet with trailing tail."""
        state = process.get("state", "unknown")
        color = HEALTH_COLORS.get(state, HEALTH_COLORS["unknown"])
        entity_id = process.get("id", "")

        # Animate comet movement
        if entity_id not in self._comet_trails:
            self._comet_trails[entity_id] = []

        # Move comet
        speed = 0.5 + (process.get("metrics", {}).get("cpu", 0.3)) * 2
        comet_x = x + math.sin(self._time_offset * speed) * 20
        comet_y = y + math.cos(self._time_offset * speed * 0.7) * 10

        # Comet tail (trail of fading particles)
        trail = self._comet_trails[entity_id]
        trail.append((comet_x, comet_y, 1.0))
        if len(trail) > 15:
            trail.pop(0)

        for i, (tx, ty, alpha) in enumerate(trail):
            fade = (i + 1) / len(trail)
            ctx.globalAlpha = fade * 0.5
            ctx.fillStyle = COMET_TAIL
            ctx.beginPath()
            ctx.arc(tx, ty, size * fade, 0, math.pi * 2)
            ctx.fill()
        ctx.globalAlpha = 1.0

        # Comet head
        ctx.fillStyle = COMET_HEAD
        ctx.beginPath()
        ctx.arc(comet_x, comet_y, size, 0, math.pi * 2)
        ctx.fill()

        # Health glow
        ctx.globalAlpha = 0.4
        ctx.fillStyle = color
        ctx.beginPath()
        ctx.arc(comet_x, comet_y, size * 2, 0, math.pi * 2)
        ctx.fill()
        ctx.globalAlpha = 1.0

        # Label
        ctx.fillStyle = "#64748b"
        ctx.font = "8px monospace"
        ctx.textAlign = "center"
        label = process.get("name", "")[:8]
        ctx.fillText(label, comet_x, comet_y + size + 8)

    def _draw_asteroid_belt(self, ctx: Any, entities: list[dict], w: int, h: int) -> None:
        """Draw asteroid belt between layers."""
        belt_y = h * 0.65
        belt_h = 20

        for i in range(30):
            angle = (math.pi * 2 / 30) * i + self._time_offset * 0.05
            ax = (w / 30) * i + math.sin(angle) * 5
            ay = belt_y + math.cos(angle * 1.3 + i) * belt_h * 0.5
            a_size = 1.5 + (i % 3)

            ctx.fillStyle = ASTEROID_COLOR if i % 2 == 0 else ASTEROID_DARK
            ctx.beginPath()
            ctx.arc(ax, ay, a_size, 0, math.pi * 2)
            ctx.fill()

    def _draw_solar_flares(self, ctx: Any, entities: list[dict], w: int, h: int) -> None:
        """Draw solar flare particles erupting from active clusters."""
        clusters = [e for e in entities
                    if e.get("type") == "cluster"
                    and e.get("state") in ["running", "healthy"]]

        for i, cluster in enumerate(clusters[:3]):
            cx = (w / (len(clusters) + 1)) * (i + 1)
            cy = h * 0.35

            # Flare particles
            for f in range(4):
                flare_angle = self._time_offset * 1.5 + f * (math.pi / 2)
                flare_dist = 20 + math.sin(self._time_offset * 3 + f) * 15
                fx = cx + math.cos(flare_angle) * flare_dist
                fy = cy + math.sin(flare_angle) * flare_dist * 0.6

                ctx.globalAlpha = 0.6
                ctx.fillStyle = SUN_FLARE
                ctx.beginPath()
                ctx.arc(fx, fy, 3, 0, math.pi * 2)
                ctx.fill()
            ctx.globalAlpha = 1.0

    def _draw_solar_wind(self, ctx: Any, entities: list[dict], w: int, h: int) -> None:
        """Draw solar wind particles flowing outward."""
        clusters = [e for e in entities if e.get("type") == "cluster"]

        for i, cluster in enumerate(clusters[:2]):
            cx = (w / (len(clusters) + 1)) * (i + 1)
            cy = h * 0.35

            for p in range(8):
                age = (self._time_offset * 30 + p * 20) % 120
                angle = (math.pi * 2 / 8) * p + i * 0.5
                dist = age
                px = cx + math.cos(angle) * dist
                py = cy + math.sin(angle) * dist * 0.4

                alpha = max(0, 1 - age / 120) * 0.4
                ctx.globalAlpha = alpha
                ctx.fillStyle = SOLAR_WIND_COLOR
                ctx.beginPath()
                ctx.arc(px, py, 1.5, 0, math.pi * 2)
                ctx.fill()
        ctx.globalAlpha = 1.0

    def _draw_comet_trails(self, ctx: Any, entities: list[dict], w: int, h: int) -> None:
        """Draw comet trails for high-CPU entities."""
        # Trails are drawn inline in _draw_comet
        pass

    def _draw_eclipses(self, ctx: Any, entities: list[dict], w: int, h: int) -> None:
        """Draw eclipse effects for stopped/critical entities."""
        eclipsed = [e for e in entities
                    if e.get("state") in ["stopped", "critical"]]

        for i, entity in enumerate(eclipsed[:3]):
            etype = entity.get("type", "node")
            if etype == "node":
                ex = (w / (len([e for e in entities if e.get("type") == "node"]) + 1)) * (i + 1)
                ey = h * 0.55
                er = min(w * 0.04, h * 0.08)
            else:
                continue

            # Dark disc (eclipse body)
            ctx.fillStyle = ECLIPSE_SHADOW
            ctx.beginPath()
            ctx.arc(ex, ey, er * 1.1, 0, math.pi * 2)
            ctx.fill()

            # Corona ring
            ctx.strokeStyle = ECLIPSE_CORONA
            ctx.lineWidth = 2
            ctx.beginPath()
            ctx.arc(ex, ey, er * 1.3, 0, math.pi * 2)
            ctx.stroke()

            # Prominences
            for p in range(4):
                p_angle = (math.pi * 2 / 4) * p + self._time_offset * 0.2
                px = ex + math.cos(p_angle) * er * 1.4
                py = ey + math.sin(p_angle) * er * 1.4
                ctx.globalAlpha = 0.5
                ctx.fillStyle = SUN_PROMINENCE
                ctx.beginPath()
                ctx.arc(px, py, 3, 0, math.pi * 2)
                ctx.fill()
            ctx.globalAlpha = 1.0

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Get tooltip for entity."""
        name = entity.get("name", "Unknown")
        etype = entity.get("type", "unknown")
        state = entity.get("state", "unknown")
        cpu = entity.get("metrics", {}).get("cpu", 0)
        mem = entity.get("metrics", {}).get("mem", 0)

        type_map = {
            "cluster": "Solar System",
            "node": "Planet",
            "service": "Orbit/Satellite",
            "container": "Moon",
            "process": "Comet",
        }
        metaphor_type = type_map.get(etype, etype)

        return f"{name}\n{metaphor_type}\nState: {state}\nCPU: {cpu:.1%}\nMem: {mem:.1%}"

    def hit_test(self, entity: dict[str, Any], x: int, y: int) -> bool:
        """Test if coordinates hit entity."""
        return False

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b)
