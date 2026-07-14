"""Solar System metaphor renderer — Cluster=Galaxy, Node=Star System, Service=Planet, Container=Moon.

Deep space aesthetic with orbital mechanics, nebula colors, multi-layer starfields,
asteroid traffic, solar corona + flares, planet surface detail, glowing orbital paths,
Saturn-like rings for clusters, and animated micro-details.
"""
from __future__ import annotations
import math
import random
import time
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
NEBULA_COLORS = ["#000011", "#0d0d2b", "#1a0a2e", "#0a1a2e"]

# Planet surface color palettes (base, accent, shadow)
PLANET_PALETTES = [
    ("#4488cc", "#336699", "#224466"),  # Ocean blue
    ("#66aa44", "#558833", "#336622"),  # Forest green
    ("#cc8844", "#aa6633", "#884422"),  # Mars red
    ("#8888aa", "#666688", "#444466"),  # Grey rocky
    ("#ddaa66", "#cc9944", "#aa7733"),  # Sandy desert
    ("#6688cc", "#5577aa", "#334488"),  # Ice blue
]

# Star field seed for deterministic randomness
STARFIELD_SEED = 42
NEBULA_SEED = 99


class SolarRenderer(MetaphorRenderer):
    """Solar System metaphor: clusters are galaxies, nodes are star systems,
    services are planets, containers are moons.

    Planet size = memory usage, glow intensity = CPU usage.
    Orbital paths rendered as glowing energy lines. Asteroid traffic for requests.
    Solar corona + flares for errors. Aurora effects for healthy services.
    Planet collision warning for critical state. Gravity lines for dependencies.
    Saturn-like rings for cluster entities.
    """

    name = "solar"
    description = "Infrastructure as a solar system with orbital visualization"

    def __init__(self):
        self._layout: dict[str, dict[str, Any]] = {}
        self._starfield_layers: list[list[tuple[float, float, float, float]]] | None = None
        self._nebula_patches: list[tuple[float, float, float, str, float]] | None = None
        self._planet_palette_idx = 0

    def _generate_starfield(self, w: int, h: int) -> list[list[tuple[float, float, float, float]]]:
        """Generate 3-layer parallax starfield: (x, y, size, brightness)."""
        if self._starfield_layers is not None:
            return self._starfield_layers
        layers = []
        configs = [
            (300, 0.5, 1.0),   # Layer 0: many tiny distant stars
            (150, 1.0, 1.5),   # Layer 1: medium stars
            (50, 1.5, 2.5),    # Layer 2: few bright close stars
        ]
        for li, (count, min_size, max_size) in enumerate(configs):
            rng = random.Random(STARFIELD_SEED + li * 1000)
            layer = []
            for _ in range(count):
                x = rng.uniform(0, w)
                y = rng.uniform(0, h)
                size = rng.uniform(min_size, max_size)
                brightness = rng.uniform(0.15, 1.0)
                layer.append((x, y, size, brightness))
            layers.append(layer)
        self._starfield_layers = layers
        return layers

    def _generate_nebula_patches(self, w: int, h: int) -> list[tuple[float, float, float, str, float]]:
        """Generate nebula wisps: (x, y, radius, color_hex, opacity)."""
        if self._nebula_patches is not None:
            return self._nebula_patches
        rng = random.Random(NEBULA_SEED)
        colors = ["#2a0a4a", "#0a2a5a", "#3a1a4a", "#0a1a4a", "#1a0a3a", "#0a3a6a"]
        patches = []
        for _ in range(8):
            x = rng.uniform(0, w)
            y = rng.uniform(0, h)
            r = rng.uniform(w * 0.15, w * 0.4)
            color = rng.choice(colors)
            opacity = rng.uniform(0.08, 0.2)
            patches.append((x, y, r, color, opacity))
        self._nebula_patches = patches
        return patches

    def _get_planet_palette(self, entity_id: str) -> tuple[str, str, str]:
        """Deterministic planet color palette based on entity id hash."""
        idx = hash(entity_id) % len(PLANET_PALETTES)
        return PLANET_PALETTES[idx]

    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, Any]]:
        """Compute orbital positions for all entities using orbital mechanics."""
        if not entities:
            self._layout = {}
            return {}

        layout: dict[str, dict[str, Any]] = {}
        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        # Reset visual caches for new canvas size
        self._starfield_layers = None
        self._nebula_patches = None

        # Galaxy layout — divide canvas horizontally
        galaxy_w = w / max(len(roots), 1)
        for gi, root in enumerate(roots):
            gx = gi * galaxy_w + galaxy_w / 2
            gy = h / 2
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
                min_orbit = 35
                orbit_spacing = max(28, (min(galaxy_w, h) * 0.4) / max(len(planets), 1))

                for pi, planet in enumerate(planets):
                    metrics = planet.get("metrics") or {}
                    mem = metrics.get("mem", 50)
                    cpu = metrics.get("cpu", 50)

                    planet_radius = 6 + (mem / 100) * 16
                    glow = cpu / 100
                    orbit = min_orbit + pi * orbit_spacing

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

                    # Asteroid traffic
                    rps = metrics.get("req_per_sec", 0)
                    if rps > 0:
                        num_asteroids = min(int(rps / 10) + 1, 8)
                        asteroids = []
                        for ai in range(num_asteroids):
                            a_angle = planet_angle + (2 * math.pi * ai) / num_asteroids
                            a_dist = orbit + random.uniform(-8, 8)
                            ax = sx + math.cos(a_angle) * a_dist
                            ay = sy + math.sin(a_angle) * a_dist
                            asteroids.append({
                                "x": ax, "y": ay, "angle": a_angle,
                                "orbit": a_dist, "speed": random.uniform(0.001, 0.005),
                            })
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
        """Render the solar system metaphor with full visual overhaul."""
        layout = self.compute_layout(entities, w, h)

        # === LAYER 0: Deep space background ===
        self._render_background(ctx, w, h)

        # === LAYER 1: Nebula wisps ===
        self._render_nebula(ctx, w, h)

        # === LAYER 2: Multi-layer starfield ===
        self._render_starfield(ctx, w, h)

        # === LAYER 3: Orbital paths (behind celestial bodies) ===
        self._render_orbital_paths(ctx, layout, entities)

        # === LAYER 4: Celestial bodies ===
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            etype = entity.get("type", "")
            color = STATE_COLORS.get(entity.get("state", "unknown"), STATE_COLORS["unknown"])

            if etype == "cluster":
                self._render_galaxy(ctx, pos, entity, color)
            elif etype == "node":
                self._render_star(ctx, pos, entity, color)
            elif etype == "service":
                self._render_planet(ctx, pos, entity, color, layout)
            elif etype == "container":
                self._render_moon(ctx, pos, entity, color)

        # === LAYER 5: Asteroid traffic ===
        self._render_asteroid_traffic(ctx, layout)

        # === LAYER 6: Gravity lines (dependencies) ===
        self._render_gravity_lines(ctx, layout)

        # === LAYER 7: Ambient particles / micro-details ===
        self._render_micro_details(ctx, layout, w, h)

    # ──────────────────────────────────────────────────────────────────
    # BACKGROUND & ATMOSPHERE
    # ──────────────────────────────────────────────────────────────────

    def _render_background(self, ctx: Any, w: int, h: int) -> None:
        """Deep space background: #000011 base with subtle vertical gradient."""
        # Base deep space
        ctx.fillStyle("#000011")
        ctx.fillRect(0, 0, w, h)

        # Vertical gradient: slightly lighter at center (galactic plane)
        gradient = ctx.createLinearGradient(0, 0, 0, h)
        gradient.addColorStop(0, "rgba(5, 5, 20, 1)")
        gradient.addColorStop(0.3, "rgba(8, 8, 30, 1)")
        gradient.addColorStop(0.5, "rgba(10, 10, 35, 1)")
        gradient.addColorStop(0.7, "rgba(8, 8, 30, 1)")
        gradient.addColorStop(1, "rgba(5, 5, 20, 1)")
        ctx.fillStyle(gradient)
        ctx.fillRect(0, 0, w, h)

    def _render_nebula(self, ctx: Any, w: int, h: int) -> None:
        """Nebula wisps: large soft radial gradients in purple/blue."""
        patches = self._generate_nebula_patches(w, h)
        for x, y, r, color, opacity in patches:
            gradient = ctx.createRadialGradient(x, y, 0, x, y, r)
            gradient.addColorStop(0, self._color_with_alpha(color, opacity))
            gradient.addColorStop(0.5, self._color_with_alpha(color, opacity * 0.4))
            gradient.addColorStop(1, "transparent")
            ctx.fillStyle(gradient)
            ctx.beginPath()
            ctx.arc(x, y, r, 0, 2 * math.pi)
            ctx.fill()

    def _render_starfield(self, ctx: Any, w: int, h: int) -> None:
        """Multi-layer parallax starfield: 3 layers with different sizes and brightness."""
        layers = self._generate_starfield(w, h)
        t = time.time()
        for li, layer in enumerate(layers):
            for x, y, size, brightness in layer:
                # Subtle twinkling for brighter stars
                twinkle = 1.0
                if size > 1.0:
                    twinkle = 0.7 + 0.3 * math.sin(t * (1.5 + li * 0.5) + x * 0.01 + y * 0.01)
                alpha = brightness * twinkle
                ctx.fillStyle(f"rgba(255, 255, 255, {alpha:.2f})")
                ctx.beginPath()
                ctx.arc(x, y, size * 0.5, 0, 2 * math.pi)
                ctx.fill()
                # Cross-shaped glint for brightest stars
                if size > 2.0 and brightness > 0.7:
                    ctx.strokeStyle(f"rgba(200, 220, 255, {alpha * 0.3:.2f})")
                    ctx.lineWidth(0.5)
                    glint_len = size * 2
                    ctx.beginPath()
                    ctx.moveTo(x - glint_len, y)
                    ctx.lineTo(x + glint_len, y)
                    ctx.moveTo(x, y - glint_len)
                    ctx.lineTo(x, y + glint_len)
                    ctx.stroke()

    # ──────────────────────────────────────────────────────────────────
    # ORBITAL PATHS — Glowing energy lines
    # ──────────────────────────────────────────────────────────────────

    def _render_orbital_paths(self, ctx: Any, layout: dict, entities: list) -> None:
        """Render orbital paths as glowing multi-layer energy lines."""
        rendered_orbits = set()
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos or pos.get("type") != "planet":
                continue
            cx = pos.get("orbit_center_x", pos["x"])
            cy = pos.get("orbit_center_y", pos["y"])
            orbit = pos.get("orbit", 50)
            orbit_key = (cx, cy, orbit)
            if orbit_key in rendered_orbits:
                continue
            rendered_orbits.add(orbit_key)

            # Multi-layer glow: outer glow → mid glow → core line
            layers = [
                (4.0, "rgba(80, 130, 255, 0.08)"),
                (2.5, "rgba(90, 140, 255, 0.12)"),
                (1.5, "rgba(100, 150, 255, 0.2)"),
                (0.8, "rgba(120, 170, 255, 0.35)"),
            ]
            for lw, color in layers:
                ctx.strokeStyle(color)
                ctx.lineWidth(lw)
                ctx.beginPath()
                ctx.arc(cx, cy, orbit, 0, 2 * math.pi)
                ctx.stroke()

        # Moon orbits (thinner, subtler)
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos or pos.get("type") != "moon":
                continue
            cx = pos.get("orbit_center_x", pos["x"])
            cy = pos.get("orbit_center_y", pos["y"])
            orbit = pos.get("orbit", 10)
            ctx.strokeStyle("rgba(150, 180, 255, 0.15)")
            ctx.lineWidth(0.5)
            ctx.beginPath()
            ctx.arc(cx, cy, orbit, 0, 2 * math.pi)
            ctx.stroke()

    # ──────────────────────────────────────────────────────────────────
    # GALAXY — Saturn-like rings
    # ──────────────────────────────────────────────────────────────────

    def _render_galaxy(self, ctx: Any, pos: dict, entity: dict, color: str) -> None:
        """Render galaxy as nebula region with Saturn-like rings and label."""
        cx, cy = pos["x"], pos["y"]
        gw, gh = pos["w"], pos["h"]

        # Ambient nebula glow around galaxy center
        gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, min(gw, gh) * 0.4)
        gradient.addColorStop(0, self._color_with_alpha(color, 0.15))
        gradient.addColorStop(0.5, self._color_with_alpha(color, 0.06))
        gradient.addColorStop(1, "transparent")
        ctx.fillStyle(gradient)
        ctx.beginPath()
        ctx.arc(cx, cy, min(gw, gh) * 0.4, 0, 2 * math.pi)
        ctx.fill()

        # Saturn-like ring system (elliptical)
        ring_radius_x = min(gw, gh) * 0.35
        ring_radius_y = ring_radius_x * 0.25  # Tilted perspective
        ring_layers = [
            (ring_radius_x + 12, ring_radius_y + 3, "rgba(160, 140, 200, 0.08)", 3),
            (ring_radius_x + 6, ring_radius_y + 1.5, "rgba(180, 160, 220, 0.12)", 2),
            (ring_radius_x, ring_radius_y, self._color_with_alpha(color, 0.2), 1.5),
            (ring_radius_x - 6, ring_radius_y - 1.5, "rgba(180, 160, 220, 0.1)", 1),
            (ring_radius_x - 12, ring_radius_y - 3, "rgba(160, 140, 200, 0.06)", 0.8),
        ]
        for rx, ry, col, lw in ring_layers:
            ctx.strokeStyle(col)
            ctx.lineWidth(lw)
            ctx.beginPath()
            ctx.ellipse(cx, cy, rx, ry, 0, 0, 2 * math.pi)
            ctx.stroke()

        # Galaxy border (dashed, subtle)
        ctx.strokeStyle(self._color_with_alpha(color, 0.3))
        ctx.lineWidth(1)
        ctx.setLineDash([5, 5])
        ctx.strokeRect(
            pos["x"] - pos["w"] / 2 + 4,
            pos["y"] - pos["h"] / 2 + 4,
            pos["w"] - 8,
            pos["h"] - 8,
        )
        ctx.setLineDash([])

        # Galaxy label with glow
        ctx.save()
        ctx.shadowColor(color)
        ctx.shadowBlur(8)
        ctx.fillStyle(color)
        ctx.font("bold 14px system-ui, sans-serif")
        ctx.fillText(entity.get("name", ""), pos["x"] - pos["w"] / 2 + 12, pos["y"] - pos["h"] / 2 + 20)
        ctx.restore()

    # ──────────────────────────────────────────────────────────────────
    # STAR — Corona glow + solar flares
    # ──────────────────────────────────────────────────────────────────

    def _render_star(self, ctx: Any, pos: dict, entity: dict, color: str) -> None:
        """Render star system with corona glow, solar flares, and pulsing core."""
        r = pos.get("radius", 12)
        t = time.time()

        # Outer corona — large soft glow
        corona_r = r * 5
        gradient = ctx.createRadialGradient(pos["x"], pos["y"], r * 0.5, pos["x"], pos["y"], corona_r)
        gradient.addColorStop(0, "#ffd700")
        gradient.addColorStop(0.15, "rgba(255, 215, 0, 0.4)")
        gradient.addColorStop(0.3, "rgba(255, 140, 0, 0.15)")
        gradient.addColorStop(0.6, "rgba(255, 100, 0, 0.05)")
        gradient.addColorStop(1, "transparent")
        ctx.fillStyle(gradient)
        ctx.beginPath()
        ctx.arc(pos["x"], pos["y"], corona_r, 0, 2 * math.pi)
        ctx.fill()

        # Corona spikes (animated rotating)
        num_spikes = 8
        spike_len = r * 2.5
        ctx.save()
        ctx.translate(pos["x"], pos["y"])
        ctx.rotate(t * 0.2)  # slow rotation
        for i in range(num_spikes):
            angle = (2 * math.pi * i) / num_spikes
            pulse = 0.8 + 0.2 * math.sin(t * 3 + i)
            sx = math.cos(angle) * r * 0.8
            sy = math.sin(angle) * r * 0.8
            ex = math.cos(angle) * spike_len * pulse
            ey = math.sin(angle) * spike_len * pulse
            grad = ctx.createLinearGradient(sx, sy, ex, ey)
            grad.addColorStop(0, "rgba(255, 200, 50, 0.6)")
            grad.addColorStop(1, "rgba(255, 140, 0, 0)")
            ctx.strokeStyle(grad)
            ctx.lineWidth(1.5)
            ctx.beginPath()
            ctx.moveTo(sx, sy)
            ctx.lineTo(ex, ey)
            ctx.stroke()
        ctx.restore()

        # Inner glow ring
        gradient2 = ctx.createRadialGradient(pos["x"], pos["y"], r * 0.3, pos["x"], pos["y"], r * 1.5)
        gradient2.addColorStop(0, "rgba(255, 255, 220, 0.9)")
        gradient2.addColorStop(0.4, "rgba(255, 215, 0, 0.7)")
        gradient2.addColorStop(0.7, "rgba(255, 140, 0, 0.3)")
        gradient2.addColorStop(1, "transparent")
        ctx.fillStyle(gradient2)
        ctx.beginPath()
        ctx.arc(pos["x"], pos["y"], r * 1.5, 0, 2 * math.pi)
        ctx.fill()

        # Star core — white-hot center with pulsing
        pulse = 1.0 + 0.05 * math.sin(t * 2)
        core_r = r * 0.6 * pulse
        ctx.fillStyle("#fff8e0")
        ctx.beginPath()
        ctx.arc(pos["x"], pos["y"], core_r, 0, 2 * math.pi)
        ctx.fill()

        # Hot spot
        ctx.fillStyle("#ffffff")
        ctx.beginPath()
        ctx.arc(pos["x"] - core_r * 0.2, pos["y"] - core_r * 0.2, core_r * 0.3, 0, 2 * math.pi)
        ctx.fill()

        # Star label
        ctx.save()
        ctx.shadowColor("#ffd700")
        ctx.shadowBlur(4)
        ctx.fillStyle("#ffeedd")
        ctx.font("10px system-ui, sans-serif")
        ctx.fillText(entity.get("name", ""), pos["x"] + r * 1.5 + 4, pos["y"] + 4)
        ctx.restore()

    # ──────────────────────────────────────────────────────────────────
    # PLANET — Surface detail, craters, bands, shading
    # ──────────────────────────────────────────────────────────────────

    def _render_planet(self, ctx: Any, pos: dict, entity: dict, color: str, layout: dict) -> None:
        """Render planet with surface detail, craters, bands, 3D shading, and effects."""
        r = pos.get("radius", 10)
        cx = pos.get("orbit_center_x", pos["x"])
        cy = pos.get("orbit_center_y", pos["y"])
        px, py = pos["x"], pos["y"]
        palette = self._get_planet_palette(entity.get("id", ""))
        base_color, accent_color, shadow_color = palette
        state = entity.get("state", "unknown")

        # Ambient glow around planet (state-colored)
        glow_r = r * 2.5
        gradient = ctx.createRadialGradient(px, py, r * 0.8, px, py, glow_r)
        gradient.addColorStop(0, self._color_with_alpha(color, 0.25))
        gradient.addColorStop(0.5, self._color_with_alpha(color, 0.08))
        gradient.addColorStop(1, "transparent")
        ctx.fillStyle(gradient)
        ctx.beginPath()
        ctx.arc(px, py, glow_r, 0, 2 * math.pi)
        ctx.fill()

        # Planet body — base color
        ctx.save()
        ctx.beginPath()
        ctx.arc(px, py, r, 0, 2 * math.pi)
        ctx.clip()

        # Base fill
        ctx.fillStyle(base_color)
        ctx.fillRect(px - r, py - r, r * 2, r * 2)

        # Surface bands (horizontal stripes like Jupiter/Saturn)
        rng = random.Random(hash(entity.get("id", "")))
        num_bands = max(3, int(r / 3))
        for bi in range(num_bands):
            band_y = py - r + (2 * r * bi) / num_bands
            band_h = (2 * r) / num_bands * (0.3 + rng.uniform(0, 0.5))
            band_alpha = rng.uniform(0.1, 0.3)
            ctx.fillStyle(self._color_with_alpha(accent_color, band_alpha))
            ctx.fillRect(px - r, band_y, r * 2, band_h)

        # Craters (small darker circles)
        num_craters = max(2, int(r / 2))
        for ci in range(num_craters):
            cr_x = px + rng.uniform(-r * 0.7, r * 0.7)
            cr_y = py + rng.uniform(-r * 0.7, r * 0.7)
            cr_r = rng.uniform(r * 0.05, r * 0.15)
            ctx.fillStyle(self._color_with_alpha(shadow_color, 0.5))
            ctx.beginPath()
            ctx.arc(cr_x, cr_y, cr_r, 0, 2 * math.pi)
            ctx.fill()
            # Crater rim highlight
            ctx.strokeStyle(self._color_with_alpha(base_color, 0.3))
            ctx.lineWidth(0.5)
            ctx.beginPath()
            ctx.arc(cr_x - cr_r * 0.2, cr_y - cr_r * 0.2, cr_r * 0.8, 0, 2 * math.pi)
            ctx.stroke()

        # 3D shading — shadow on bottom-right, highlight on top-left
        shade = ctx.createRadialGradient(px - r * 0.3, py - r * 0.3, 0, px, py, r)
        shade.addColorStop(0, "rgba(255, 255, 255, 0.25)")
        shade.addColorStop(0.5, "transparent")
        shade.addColorStop(1, "rgba(0, 0, 0, 0.4)")
        ctx.fillStyle(shade)
        ctx.fillRect(px - r, py - r, r * 2, r * 2)

        # State-colored atmosphere tint
        ctx.fillStyle(self._color_with_alpha(color, 0.15))
        ctx.fillRect(px - r, py - r, r * 2, r * 2)

        ctx.restore()

        # Planet border — subtle atmosphere edge
        ctx.strokeStyle("rgba(200, 220, 255, 0.3)")
        ctx.lineWidth(1)
        ctx.beginPath()
        ctx.arc(px, py, r, 0, 2 * math.pi)
        ctx.stroke()

        # === EFFECTS ===

        # Aurora effect (healthy services) — animated shimmering arcs
        if pos.get("aurora"):
            t = time.time()
            for ai in range(3):
                arc_offset = math.sin(t * 1.5 + ai) * 0.3
                ctx.strokeStyle(f"rgba(100, 255, 150, {0.3 - ai * 0.08:.2f})")
                ctx.lineWidth(1.5 - ai * 0.3)
                ctx.beginPath()
                ctx.arc(px, py, r + 4 + ai * 2, -0.5 + arc_offset, 1.0 + arc_offset)
                ctx.stroke()
                ctx.beginPath()
                ctx.arc(px, py, r + 5 + ai * 2, 1.5 + arc_offset, 3.0 + arc_offset)
                ctx.stroke()

        # Solar flare (errors) — animated energy bursts
        if pos.get("flare"):
            t = time.time()
            for i in range(4):
                flare_angle = pos.get("orbit_angle", 0) + i * 0.9 + t * 0.5
                pulse = 0.5 + 0.5 * math.sin(t * 5 + i * 2)
                fx = px + math.cos(flare_angle) * (r + 6 + pulse * 8)
                fy = py + math.sin(flare_angle) * (r + 6 + pulse * 8)
                grad = ctx.createLinearGradient(
                    px + math.cos(flare_angle) * r,
                    py + math.sin(flare_angle) * r,
                    fx, fy,
                )
                grad.addColorStop(0, "rgba(255, 100, 50, 0.8)")
                grad.addColorStop(1, "rgba(255, 50, 20, 0)")
                ctx.strokeStyle(grad)
                ctx.lineWidth(2)
                ctx.beginPath()
                ctx.moveTo(px + math.cos(flare_angle) * r, py + math.sin(flare_angle) * r)
                ctx.lineTo(fx, fy)
                ctx.stroke()

        # Collision warning (critical) — pulsing red ring
        if pos.get("collision_warning"):
            t = time.time()
            pulse = 0.5 + 0.5 * math.sin(t * 4)
            ctx.strokeStyle(f"rgba(255, 50, 50, {0.5 + pulse * 0.3:.2f})")
            ctx.lineWidth(2)
            ctx.setLineDash([3, 3])
            ctx.beginPath()
            ctx.arc(px, py, r + 10 + pulse * 3, 0, 2 * math.pi)
            ctx.stroke()
            ctx.setLineDash([])

        # Planet label with glow
        ctx.save()
        ctx.shadowColor(color)
        ctx.shadowBlur(4)
        ctx.fillStyle("#ddd")
        ctx.font("9px system-ui, sans-serif")
        ctx.fillText(entity.get("name", "")[:14], px - r, py + r + 14)
        ctx.restore()

    # ──────────────────────────────────────────────────────────────────
    # MOON — Small body with subtle detail
    # ──────────────────────────────────────────────────────────────────

    def _render_moon(self, ctx: Any, pos: dict, entity: dict, color: str) -> None:
        """Render moon with subtle surface detail and ambient glow."""
        r = pos.get("radius", 3)
        px, py = pos["x"], pos["y"]

        # Ambient glow
        gradient = ctx.createRadialGradient(px, py, r * 0.5, px, py, r * 2)
        gradient.addColorStop(0, self._color_with_alpha(color, 0.3))
        gradient.addColorStop(1, "transparent")
        ctx.fillStyle(gradient)
        ctx.beginPath()
        ctx.arc(px, py, r * 2, 0, 2 * math.pi)
        ctx.fill()

        # Moon body with shading
        ctx.fillStyle(color)
        ctx.beginPath()
        ctx.arc(px, py, r, 0, 2 * math.pi)
        ctx.fill()

        # 3D shading
        shade = ctx.createRadialGradient(px - r * 0.3, py - r * 0.3, 0, px, py, r)
        shade.addColorStop(0, "rgba(255, 255, 255, 0.2)")
        shade.addColorStop(0.5, "transparent")
        shade.addColorStop(1, "rgba(0, 0, 0, 0.3)")
        ctx.fillStyle(shade)
        ctx.beginPath()
        ctx.arc(px, py, r, 0, 2 * math.pi)
        ctx.fill()

        # Moon label
        ctx.fillStyle("#999")
        ctx.font("8px system-ui, sans-serif")
        ctx.fillText(entity.get("name", "")[:10], px + r + 2, py + 3)

    # ──────────────────────────────────────────────────────────────────
    # ASTEROID TRAFFIC
    # ──────────────────────────────────────────────────────────────────

    def _render_asteroid_traffic(self, ctx: Any, layout: dict) -> None:
        """Render asteroid particles moving along orbital paths."""
        t = time.time()
        for eid, pos in layout.items():
            asteroids = pos.get("asteroids", [])
            cx = pos.get("orbit_center_x", pos["x"])
            cy = pos.get("orbit_center_y", pos["y"])
            for asteroid in asteroids:
                # Animate angle based on time
                angle = asteroid["angle"] + t * asteroid.get("speed", 0.003)
                orbit = asteroid.get("orbit", pos.get("orbit", 50))
                ax = cx + math.cos(angle) * orbit
                ay = cy + math.sin(angle) * orbit

                # Asteroid body with trail
                # Trail
                trail_len = 3
                for ti in range(trail_len):
                    trail_angle = angle - ti * 0.05
                    tx = cx + math.cos(trail_angle) * orbit
                    ty = cy + math.sin(trail_angle) * orbit
                    trail_alpha = 0.5 * (1 - ti / trail_len)
                    ctx.fillStyle(f"rgba(180, 180, 200, {trail_alpha:.2f})")
                    ctx.beginPath()
                    ctx.arc(tx, ty, 1.5 - ti * 0.3, 0, 2 * math.pi)
                    ctx.fill()

                # Main asteroid body
                ctx.fillStyle("rgba(200, 200, 220, 0.8)")
                ctx.beginPath()
                ctx.arc(ax, ay, 2, 0, 2 * math.pi)
                ctx.fill()

                # Bright leading edge
                ctx.fillStyle("rgba(255, 255, 255, 0.6)")
                ctx.beginPath()
                ctx.arc(ax + math.cos(angle) * 1, ay + math.sin(angle) * 1, 1, 0, 2 * math.pi)
                ctx.fill()

    # ──────────────────────────────────────────────────────────────────
    # GRAVITY LINES
    # ──────────────────────────────────────────────────────────────────

    def _render_gravity_lines(self, ctx: Any, layout: dict) -> None:
        """Render gravity lines between dependent entities as pulsing energy beams."""
        t = time.time()
        for eid, pos in layout.items():
            gravity_lines = pos.get("gravity_lines", {})
            for dep_id in gravity_lines:
                dep_pos = layout.get(dep_id)
                if dep_pos:
                    pulse = 0.3 + 0.15 * math.sin(t * 2 + hash(eid + dep_id) * 0.01)
                    # Outer glow
                    ctx.strokeStyle(f"rgba(160, 120, 255, {pulse * 0.3:.2f})")
                    ctx.lineWidth(3)
                    ctx.setLineDash([6, 6])
                    ctx.beginPath()
                    ctx.moveTo(pos["x"], pos["y"])
                    ctx.lineTo(dep_pos["x"], dep_pos["y"])
                    ctx.stroke()
                    # Core line
                    ctx.strokeStyle(f"rgba(180, 150, 255, {pulse:.2f})")
                    ctx.lineWidth(1)
                    ctx.beginPath()
                    ctx.moveTo(pos["x"], pos["y"])
                    ctx.lineTo(dep_pos["x"], dep_pos["y"])
                    ctx.stroke()
                    ctx.setLineDash([])

    # ──────────────────────────────────────────────────────────────────
    # MICRO-DETAILS — Blinking lights, floating debris
    # ──────────────────────────────────────────────────────────────────

    def _render_micro_details(self, ctx: Any, layout: dict, w: int, h: int) -> None:
        """Render ambient floating debris and blinking navigation lights."""
        t = time.time()
        rng = random.Random(STARFIELD_SEED + 7777)

        # Floating space debris (tiny dots drifting slowly)
        for _ in range(30):
            base_x = rng.uniform(0, w)
            base_y = rng.uniform(0, h)
            # Slow drift
            drift_x = math.sin(t * 0.1 + base_x * 0.01) * 3
            drift_y = math.cos(t * 0.08 + base_y * 0.01) * 2
            dx = base_x + drift_x
            dy = base_y + drift_y
            alpha = 0.1 + 0.1 * math.sin(t + base_x)
            ctx.fillStyle(f"rgba(150, 150, 170, {alpha:.2f})")
            ctx.beginPath()
            ctx.arc(dx, dy, 0.5, 0, 2 * math.pi)
            ctx.fill()

        # Navigation beacon lights on planets/moons (blinking)
        for eid, pos in layout.items():
            if pos.get("type") in ("planet", "moon"):
                r = pos.get("radius", 3)
                beacon_angle = t * 1.5 + hash(eid) * 0.1
                blink = max(0, math.sin(beacon_angle))
                if blink > 0.7:
                    bx = pos["x"] + math.cos(beacon_angle * 0.5) * r * 0.6
                    by = pos["y"] + math.sin(beacon_angle * 0.5) * r * 0.6
                    ctx.fillStyle(f"rgba(255, 100, 100, {(blink - 0.7) * 3:.2f})")
                    ctx.beginPath()
                    ctx.arc(bx, by, 1, 0, 2 * math.pi)
                    ctx.fill()

    # ──────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _color_with_alpha(hex_color: str, alpha: float) -> str:
        """Convert hex color to rgba string with given alpha."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        else:
            r, g, b = 100, 100, 100
        return f"rgba({r}, {g}, {b}, {alpha:.3f})"

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
