"""Solar System metaphor renderer — Cluster=Galaxy, Node=Star System, Service=Planet, Container=Moon.

Deep space aesthetic with orbital mechanics, nebula colors, star fields,
asteroid traffic, solar flares, aurora effects, and gravity lines.
"""
from __future__ import annotations
import math
import random
from typing import Any
from engine.metaphors.base import MetaphorRenderer


# Deep space state colors (nebula palette)
STATE_COLORS = {
    "healthy": "#4ade80",    # Green nebula
    "running": "#60a5fa",    # Blue giant
    "idle": "#94a3b8",       # Dim dwarf
    "warning": "#fbbf24",    # Amber dwarf
    "degraded": "#f97316",   # Orange giant
    "critical": "#ef4444",   # Red supergiant
    "stopped": "#374151",    # Dead star
    "pending": "#a78bfa",    # Purple nebula
    "scaling": "#06b6d4",    # Cyan giant
    "unknown": "#6b7280",    # Grey dwarf
}

# Nebula background gradient colors
NEBULA_COLORS = ["#0a0a1a", "#0d0d2b", "#1a0a2e", "#0a1a2e"]

# Star field seed for deterministic randomness
STARFIELD_SEED = 42


class SolarRenderer(MetaphorRenderer):
    """Solar System metaphor: clusters are galaxies, nodes are star systems,
    services are planets, containers are moons.

    Planet size = memory usage, glow intensity = CPU usage.
    Orbital paths rendered as glowing lines. Asteroid traffic for requests.
    Solar flares for errors. Aurora effects for healthy services.
    Planet collision warning for critical state. Gravity lines for dependencies.
    """

    name = "solar"
    description = "Infrastructure as a solar system with orbital visualization"

    def __init__(self):
        self._layout: dict[str, dict[str, Any]] = {}
        self._starfield: list[tuple[float, float, float]] | None = None

    def _generate_starfield(self, w: int, h: int, count: int = 200) -> list[tuple[float, float, float]]:
        """Generate deterministic star positions (x, y, brightness)."""
        if self._starfield is not None:
            return self._starfield
        rng = random.Random(STARFIELD_SEED)
        stars = []
        for _ in range(count):
            x = rng.uniform(0, w)
            y = rng.uniform(0, h)
            brightness = rng.uniform(0.2, 1.0)
            stars.append((x, y, brightness))
        self._starfield = stars
        return stars

    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, Any]]:
        """Compute orbital positions for all entities using orbital mechanics.

        Galaxies (clusters) divide the canvas. Star systems (nodes) are centered
        in their galaxy. Planets (services) orbit their star. Moons (containers)
        orbit their planet.
        """
        if not entities:
            self._layout = {}
            return {}

        layout: dict[str, dict[str, Any]] = {}
        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        # Reset starfield for new canvas size
        self._starfield = None

        # Galaxy layout — divide canvas horizontally
        galaxy_w = w / max(len(roots), 1)
        for gi, root in enumerate(roots):
            gx = gi * galaxy_w + galaxy_w / 2  # center x
            gy = h / 2  # center y
            layout[root["id"]] = {
                "x": gx, "y": gy,
                "w": galaxy_w, "h": h,
                "type": "galaxy",
            }

            # Star systems (nodes) — positioned within galaxy
            stars = [by_id[cid] for cid in (root.get("children") or []) if cid in by_id]
            star_spacing = min(galaxy_w, h) * 0.3
            for si, star in enumerate(stars):
                angle = (2 * math.pi * si) / max(len(stars), 1)
                sx = gx + math.cos(angle) * star_spacing * 0.2
                sy = gy + math.sin(angle) * star_spacing * 0.2
                layout[star["id"]] = {
                    "x": sx, "y": sy,
                    "radius": 12,
                    "type": "star",
                }

                # Planets (services) — orbit the star
                planets = [by_id[pid] for pid in (star.get("children") or []) if pid in by_id]
                min_orbit = 30
                orbit_spacing = max(25, (min(galaxy_w, h) * 0.4) / max(len(planets), 1))

                for pi, planet in enumerate(planets):
                    metrics = planet.get("metrics") or {}
                    mem = metrics.get("mem", 50)
                    cpu = metrics.get("cpu", 50)

                    # Planet radius scales with memory (10-90 → 6-22 px)
                    planet_radius = 6 + (mem / 100) * 16
                    # Glow intensity scales with CPU (0-100 → 0-1)
                    glow = cpu / 100
                    # Orbital radius increases per planet index
                    orbit = min_orbit + pi * orbit_spacing

                    # Position planet on orbit (spread evenly)
                    planet_angle = (2 * math.pi * pi) / max(len(planets), 1)
                    px = sx + math.cos(planet_angle) * orbit
                    py = sy + math.sin(planet_angle) * orbit

                    planet_layout: dict[str, Any] = {
                        "x": px, "y": py,
                        "radius": planet_radius,
                        "glow": glow,
                        "orbit": orbit,
                        "orbit_center_x": sx,
                        "orbit_center_y": sy,
                        "orbit_angle": planet_angle,
                        "type": "planet",
                    }

                    # Asteroid traffic — services with req_per_sec
                    rps = metrics.get("req_per_sec", 0)
                    if rps > 0:
                        num_asteroids = min(int(rps / 10) + 1, 8)
                        asteroids = []
                        for ai in range(num_asteroids):
                            a_angle = planet_angle + (2 * math.pi * ai) / num_asteroids
                            a_dist = orbit + random.uniform(-8, 8)
                            ax = sx + math.cos(a_angle) * a_dist
                            ay = sy + math.sin(a_angle) * a_dist
                            asteroids.append({"x": ax, "y": ay, "angle": a_angle})
                        planet_layout["asteroids"] = asteroids

                    # Solar flare for errors
                    error_rate = metrics.get("error_rate", 0)
                    if error_rate > 0.05 or planet.get("state") == "critical":
                        planet_layout["flare"] = True

                    # Aurora for healthy services
                    if planet.get("state") in ("healthy", "running"):
                        planet_layout["aurora"] = True

                    # Collision warning for critical
                    if planet.get("state") == "critical":
                        planet_layout["collision_warning"] = True

                    # Gravity lines for dependencies
                    deps = (planet.get("labels") or {}).get("depends_on", "")
                    if deps:
                        gravity_lines = {}
                        for dep_id in deps.split(","):
                            dep_id = dep_id.strip()
                            if dep_id in by_id:
                                gravity_lines[dep_id] = True
                        if gravity_lines:
                            planet_layout["gravity_lines"] = gravity_lines

                    layout[planet["id"]] = planet_layout

                    # Moons (containers) — orbit the planet
                    moons = [by_id[mid] for mid in (planet.get("children") or []) if mid in by_id]
                    moon_orbit_base = planet_radius + 10
                    for mi, moon in enumerate(moons):
                        moon_angle = (2 * math.pi * mi) / max(len(moons), 1)
                        moon_dist = moon_orbit_base + mi * 8
                        mx = px + math.cos(moon_angle) * moon_dist
                        my = py + math.sin(moon_angle) * moon_dist
                        layout[moon["id"]] = {
                            "x": mx, "y": my,
                            "radius": 3,
                            "orbit": moon_dist,
                            "orbit_parent": planet["id"],
                            "orbit_center_x": px,
                            "orbit_center_y": py,
                            "type": "moon",
                        }

        self._layout = layout
        return layout

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the solar system metaphor with deep space aesthetic."""
        layout = self.compute_layout(entities, w, h)

        # Deep space background
        ctx.fillStyle(NEBULA_COLORS[0])
        ctx.fillRect(0, 0, w, h)

        # Star field
        stars = self._generate_starfield(w, h)
        for sx, sy, brightness in stars:
            alpha = brightness
            ctx.fillStyle(f"rgba(255, 255, 255, {alpha:.2f})")
            ctx.fillRect(sx, sy, 1, 1)

        # Render each entity
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            etype = entity.get("type", "")
            color = STATE_COLORS.get(entity.get("state", "unknown"), STATE_COLORS["unknown"])

            if etype == "cluster":
                # Galaxy — large nebula glow
                self._render_galaxy(ctx, pos, entity, color)
            elif etype == "node":
                # Star system — bright central star
                self._render_star(ctx, pos, entity, color)
            elif etype == "service":
                # Planet with orbital path
                self._render_planet(ctx, pos, entity, color, layout)
            elif etype == "container":
                # Moon
                self._render_moon(ctx, pos, entity, color)

        # Render gravity lines (dependencies) on top
        self._render_gravity_lines(ctx, layout)

    def _render_galaxy(self, ctx: Any, pos: dict, entity: dict, color: str) -> None:
        """Render galaxy as a nebula border with label."""
        # Nebula border
        ctx.strokeStyle(color)
        ctx.lineWidth(1)
        ctx.setLineDash([5, 5])
        ctx.strokeRect(
            pos["x"] - pos["w"] / 2 + 4,
            pos["y"] - pos["h"] / 2 + 4,
            pos["w"] - 8,
            pos["h"] - 8,
        )
        ctx.setLineDash([])

        # Galaxy label
        ctx.fillStyle(color)
        ctx.font("bold 14px system-ui, sans-serif")
        ctx.fillText(entity.get("name", ""), pos["x"] - pos["w"] / 2 + 12, pos["y"] - pos["h"] / 2 + 20)

    def _render_star(self, ctx: Any, pos: dict, entity: dict, color: str) -> None:
        """Render star system as a glowing central star."""
        r = pos.get("radius", 12)

        # Star glow
        ctx.save()
        gradient = ctx.createRadialGradient(pos["x"], pos["y"], 0, pos["x"], pos["y"], r * 3)
        gradient.addColorStop(0, color)
        gradient.addColorStop(1, "transparent")
        ctx.fillStyle(gradient)
        ctx.beginPath()
        ctx.arc(pos["x"], pos["y"], r * 3, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # Star core
        ctx.fillStyle("#fff")
        ctx.beginPath()
        ctx.arc(pos["x"], pos["y"], r * 0.6, 0, 2 * math.pi)
        ctx.fill()

        # Star label
        ctx.fillStyle("#ccc")
        ctx.font("10px system-ui, sans-serif")
        ctx.fillText(entity.get("name", ""), pos["x"] + r + 4, pos["y"] + 4)

    def _render_planet(self, ctx: Any, pos: dict, entity: dict, color: str, layout: dict) -> None:
        """Render planet with orbital path, glow, and effects."""
        r = pos.get("radius", 10)
        cx = pos.get("orbit_center_x", pos["x"])
        cy = pos.get("orbit_center_y", pos["y"])
        orbit = pos.get("orbit", 50)

        # Orbital path — glowing line
        ctx.strokeStyle(f"rgba(100, 150, 255, 0.3)")
        ctx.lineWidth(1)
        ctx.beginPath()
        ctx.arc(cx, cy, orbit, 0, 2 * math.pi)
        ctx.stroke()

        # Planet glow (CPU-based)
        glow = pos.get("glow", 0.5)
        if glow > 0.1:
            ctx.save()
            gradient = ctx.createRadialGradient(pos["x"], pos["y"], r * 0.5, pos["x"], pos["y"], r * 2.5)
            gradient.addColorStop(0, f"rgba(255, 200, 50, {glow * 0.5:.2f})")
            gradient.addColorStop(1, "transparent")
            ctx.fillStyle(gradient)
            ctx.beginPath()
            ctx.arc(pos["x"], pos["y"], r * 2.5, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        # Planet body
        ctx.fillStyle(color)
        ctx.beginPath()
        ctx.arc(pos["x"], pos["y"], r, 0, 2 * math.pi)
        ctx.fill()

        # Planet border
        ctx.strokeStyle("rgba(255,255,255,0.3)")
        ctx.lineWidth(1)
        ctx.beginPath()
        ctx.arc(pos["x"], pos["y"], r, 0, 2 * math.pi)
        ctx.stroke()

        # Aurora effect (healthy services)
        if pos.get("aurora"):
            ctx.strokeStyle(f"rgba(100, 255, 150, 0.4)")
            ctx.lineWidth(2)
            ctx.beginPath()
            ctx.arc(pos["x"], pos["y"], r + 4, -0.5, 1.0)
            ctx.stroke()
            ctx.beginPath()
            ctx.arc(pos["x"], pos["y"], r + 6, 1.5, 3.0)
            ctx.stroke()

        # Solar flare (errors)
        if pos.get("flare"):
            ctx.strokeStyle("rgba(255, 100, 50, 0.7)")
            ctx.lineWidth(2)
            for i in range(3):
                flare_angle = pos.get("orbit_angle", 0) + i * 1.2
                fx = pos["x"] + math.cos(flare_angle) * (r + 8)
                fy = pos["y"] + math.sin(flare_angle) * (r + 8)
                ctx.beginPath()
                ctx.moveTo(pos["x"] + math.cos(flare_angle) * r, pos["y"] + math.sin(flare_angle) * r)
                ctx.lineTo(fx, fy)
                ctx.stroke()

        # Collision warning (critical)
        if pos.get("collision_warning"):
            ctx.strokeStyle("rgba(255, 50, 50, 0.8)")
            ctx.lineWidth(2)
            ctx.setLineDash([3, 3])
            ctx.beginPath()
            ctx.arc(pos["x"], pos["y"], r + 10, 0, 2 * math.pi)
            ctx.stroke()
            ctx.setLineDash([])

        # Asteroid traffic
        asteroids = pos.get("asteroids", [])
        for asteroid in asteroids:
            ctx.fillStyle("rgba(180, 180, 200, 0.7)")
            ctx.beginPath()
            ctx.arc(asteroid["x"], asteroid["y"], 2, 0, 2 * math.pi)
            ctx.fill()

        # Planet label
        ctx.fillStyle("#ddd")
        ctx.font("9px system-ui, sans-serif")
        ctx.fillText(entity.get("name", "")[:14], pos["x"] - r, pos["y"] + r + 14)

    def _render_moon(self, ctx: Any, pos: dict, entity: dict, color: str) -> None:
        """Render moon orbiting its planet."""
        r = pos.get("radius", 3)

        # Moon body
        ctx.fillStyle(color)
        ctx.beginPath()
        ctx.arc(pos["x"], pos["y"], r, 0, 2 * math.pi)
        ctx.fill()

        # Moon label
        ctx.fillStyle("#999")
        ctx.font("8px system-ui, sans-serif")
        ctx.fillText(entity.get("name", "")[:10], pos["x"] + r + 2, pos["y"] + 3)

    def _render_gravity_lines(self, ctx: Any, layout: dict) -> None:
        """Render gravity lines between dependent entities."""
        for eid, pos in layout.items():
            gravity_lines = pos.get("gravity_lines", {})
            for dep_id in gravity_lines:
                dep_pos = layout.get(dep_id)
                if dep_pos:
                    ctx.strokeStyle("rgba(160, 120, 255, 0.4)")
                    ctx.lineWidth(1)
                    ctx.setLineDash([4, 4])
                    ctx.beginPath()
                    ctx.moveTo(pos["x"], pos["y"])
                    ctx.lineTo(dep_pos["x"], dep_pos["y"])
                    ctx.stroke()
                    ctx.setLineDash([])

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Generate tooltip text for an entity with solar mapping names."""
        type_mapping = {
            "cluster": "Galaxy",
            "node": "Star System",
            "service": "Planet",
            "container": "Moon",
        }
        mapped_type = type_mapping.get(entity.get("type", ""), entity.get("type", "?"))
        lines = [
            f"{entity.get('name', '?')} — {mapped_type}",
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
            lines.append(f"Asteroids (RPS): {m['req_per_sec']}")
        if "error_rate" in m:
            lines.append(f"Solar Flares: {m['error_rate'] * 100:.1f}%")
        if "count" in m:
            lines.append(f"Count: {m['count']}")
        if "uptime_hrs" in m:
            lines.append(f"Uptime: {m['uptime_hrs']}h")
        return "\n".join(lines)

    def hit_test(self, entity: dict[str, Any], x: int, y: int) -> bool:
        """Check if (x,y) falls within this entity's rendered area (circular bounds)."""
        eid = entity.get("id")
        if eid is None:
            return False
        pos = self._layout.get(eid)
        if not pos:
            return False
        r = pos.get("radius", 10)
        dx = x - pos["x"]
        dy = y - pos["y"]
        return (dx * dx + dy * dy) <= (r * r)

    def config(self) -> dict[str, Any]:
        """Return metaphor configuration metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "state_colors": STATE_COLORS,
            "mappings": {
                "cluster": "galaxy",
                "node": "star_system",
                "service": "planet",
                "container": "moon",
            },
        }
