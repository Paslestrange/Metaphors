"""Space Station metaphor renderer — Full Visual Overhaul.

Deep space background with parallax star fields, radial station layout with
central hub and orbiting modules, illuminated corridors, animated docking ports,
life support LED indicators, control panel glow, emergency lighting, solar panels,
floating debris particles, power core glow tied to CPU, shuttle traffic, and
hull breach animations for critical states.

Follows VISUAL_GUIDELINES.md: 4+ depth layers, ambient lighting, animated
micro-details, environmental context, architectural detail, 60-30-10 color.
"""
from __future__ import annotations
import math
import random
from typing import Any
from engine.metaphors.base import MetaphorRenderer


# ── Color Palette (from VISUAL_GUIDELINES.md Space Station section) ──────────

BACKGROUND = "#000011"          # Deep space
MODULE_BODY = "#2a2a3e"         # Dark metal
PANEL_LIT = "#44aaff"           # Cool blue
PANEL_WARNING = "#ff8800"       # Orange
PANEL_CRITICAL = "#ff2222"      # Red
CORRIDOR_COLOR = "#1a1a2e"      # Dark interior
DOCKING_GREEN = "#00ff88"       # Available
DOCKING_RED = "#ff2222"         # Occupied
STAR_COLOR = "#ffffff"
SOLAR_PANEL = "#1a3a5c"         # Dark blue panels
SOLAR_GLOW = "#2266aa"          # Panel reflection
DEBRIS_COLOR = "#555566"        # Floating particles
CORE_GLOW = "#4488ff"           # Power core blue
EMERGENCY_RED = "#ff1111"       # Emergency pulse
HUB_RING = "#334466"            # Station ring outline

# State → life support color
STATE_COLORS = {
    "healthy": "#4ade80",
    "running": "#60a5fa",
    "idle": "#94a3b8",
    "warning": "#fbbf24",
    "degraded": "#f97316",
    "critical": "#ef4444",
    "stopped": "#374151",
    "pending": "#a78bfa",
    "scaling": "#06b6d4",
    "unknown": "#6b7280",
}

# Life support status mapping
LIFE_SUPPORT = {
    "healthy": "nominal",
    "running": "nominal",
    "idle": "standby",
    "warning": "caution",
    "degraded": "warning",
    "critical": "emergency",
    "stopped": "offline",
    "pending": "initializing",
    "scaling": "adjusting",
    "unknown": "unknown",
}


class SpaceStationRenderer(MetaphorRenderer):
    """Space Station metaphor with full visual overhaul.

    Clusters → Station Rings (central hub with power core).
    Nodes → Modules (orbiting habitats with solar panels, life support LEDs).
    Services → Pods (docking ports with shuttle traffic, animated rings).
    Containers → Compartments (internal bays with status indicators).

    Visual layers (per VISUAL_GUIDELINES.md):
      Layer 0: Deep space background gradient + nebula wisps
      Layer 1: Parallax star field (3 depth layers)
      Layer 2: Floating debris / particles in vacuum
      Layer 3: Station structure (corridors, modules, solar panels)
      Layer 4: Entity details (docking ports, life support LEDs, control panels)
      Layer 5: Effects (breach sparks, emergency pulses, shuttle traffic)
      Layer 6: HUD overlay (labels, tooltips)
    """

    name = "space"
    description = "Infrastructure as an orbital space station"

    def __init__(self):
        self._layout: dict[str, dict[str, Any]] = {}
        self._star_layers: list[list[tuple[float, float, float, float]]] = [[], [], []]
        self._debris: list[tuple[float, float, float, float]] = []
        self._w: int = 0
        self._h: int = 0

    # ── Background Generation ────────────────────────────────────────────────

    def _generate_star_field(self, w: int, h: int) -> None:
        """Generate 3-layer parallax star field with varying sizes and brightness.

        Layer 0: distant stars (tiny, dim, many)
        Layer 1: mid-range stars (medium, moderate brightness)
        Layer 2: close stars (larger, brighter, fewer)
        """
        rng = random.Random(42)  # deterministic seed for consistency

        # Layer 0: distant — 200 tiny dim stars
        self._star_layers[0] = [
            (rng.uniform(0, w), rng.uniform(0, h),
             rng.uniform(0.15, 0.35), rng.uniform(0.5, 1.0))
            for _ in range(200)
        ]
        # Layer 1: mid-range — 80 medium stars
        self._star_layers[1] = [
            (rng.uniform(0, w), rng.uniform(0, h),
             rng.uniform(0.35, 0.65), rng.uniform(1.0, 2.0))
            for _ in range(80)
        ]
        # Layer 2: close — 25 bright stars
        self._star_layers[2] = [
            (rng.uniform(0, w), rng.uniform(0, h),
             rng.uniform(0.65, 1.0), rng.uniform(1.5, 3.0))
            for _ in range(25)
        ]

    def _generate_debris(self, w: int, h: int, count: int = 30) -> None:
        """Generate floating debris particles drifting in vacuum."""
        rng = random.Random(99)
        self._debris = [
            (rng.uniform(0, w), rng.uniform(0, h),
             rng.uniform(0.5, 2.5),  # size
             rng.uniform(0.1, 0.4))  # opacity
            for _ in range(count)
        ]

    # ── Layout Computation ───────────────────────────────────────────────────

    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, Any]]:
        """Compute radial layout for space station arrangement.

        Cluster (Station Ring) sits at center with power core.
        Nodes (Modules) orbit radially around it, connected by corridors.
        Services (Pods) dock at module ports with animated rings.
        Containers (Compartments) nest inside pods.
        """
        if not entities:
            self._layout = {}
            return {}

        self._w, self._h = w, h
        self._generate_star_field(w, h)
        self._generate_debris(w, h)

        layout: dict[str, dict[str, Any]] = {}
        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        cx, cy = w / 2, h / 2
        base_radius = min(w, h) * 0.35

        for ri, root in enumerate(roots):
            metrics = root.get("metrics") or {}
            cpu = metrics.get("cpu", 50)
            mem = metrics.get("mem", 50)
            etype = root.get("type", "cluster")

            if etype != "cluster":
                continue

            # Power core radius scales with CPU usage
            core_radius = 20 + (base_radius * 0.3) * (cpu / 100)

            layout[root["id"]] = {
                "x": cx - core_radius, "y": cy - core_radius,
                "w": core_radius * 2, "h": core_radius * 2,
                "cx": cx, "cy": cy,
                "core_radius": core_radius,
                "ring_radius": base_radius,
                "power_glow": cpu / 100,
                "breach": root.get("state") == "critical",
                "state": root.get("state", "unknown"),
            }

            # Children (Modules) arranged radially
            children = [by_id[cid] for cid in (root.get("children") or []) if cid in by_id]
            n_modules = max(len(children), 1)

            for mi, child in enumerate(children):
                angle = (2 * math.pi * mi) / n_modules - math.pi / 2
                mod_x = cx + base_radius * math.cos(angle)
                mod_y = cy + base_radius * math.sin(angle)
                mod_size = 30

                child_metrics = child.get("metrics") or {}
                child_cpu = child_metrics.get("cpu", 50)
                child_mem = child_metrics.get("mem", 50)
                child_state = child.get("state", "unknown")

                layout[child["id"]] = {
                    "x": mod_x - mod_size, "y": mod_y - mod_size,
                    "w": mod_size * 2, "h": mod_size * 2,
                    "cx": mod_x, "cy": mod_y,
                    "angle": angle,
                    "orbit_radius": base_radius,
                    "mod_size": mod_size,
                    "life_support": LIFE_SUPPORT.get(child_state, "unknown"),
                    "life_support_color": STATE_COLORS.get(child_state, STATE_COLORS["unknown"]),
                    "breach": child_state == "critical",
                    "state": child_state,
                    "cpu": child_cpu,
                    "mem": child_mem,
                    # Solar panel geometry
                    "solar_angle": angle,
                    "solar_length": mod_size * 1.2,
                    "solar_width": 8,
                    # LED indicators (3 dots: power, data, env)
                    "led_power": child_cpu > 10,
                    "led_data": child_metrics.get("req_per_sec", 0) > 0,
                    "led_env": child_state not in ("critical", "stopped"),
                }

                # Grandchildren (Pods) at module docking ports
                grandchildren = [by_id[gcid] for gcid in (child.get("children") or []) if gcid in by_id]
                for pi, pod in enumerate(grandchildren):
                    pod_metrics = pod.get("metrics") or {}
                    req = pod_metrics.get("req_per_sec", 0)
                    pod_mem = pod_metrics.get("mem", 0)
                    pod_cpu = pod_metrics.get("cpu", 0)
                    pod_state = pod.get("state", "unknown")

                    # Pod offset from module
                    pod_angle = angle + (pi - len(grandchildren) / 2) * 0.4
                    pod_dist = mod_size + 25
                    pod_x = mod_x + pod_dist * math.cos(pod_angle)
                    pod_y = mod_y + pod_dist * math.sin(pod_angle)
                    pod_size = 15

                    # Storage fill from memory
                    storage_fill = pod_mem / 100
                    # Docking glow from request rate
                    docking_glow = min(req / 50, 1.0) if req else 0.0
                    # Docking ring color: green if available, red if busy
                    docking_available = req < 10
                    docking_color = DOCKING_GREEN if docking_available else DOCKING_RED

                    layout[pod["id"]] = {
                        "x": pod_x - pod_size, "y": pod_y - pod_size,
                        "w": pod_size * 2, "h": pod_size * 2,
                        "cx": pod_x, "cy": pod_y,
                        "storage_fill": storage_fill,
                        "docking_glow": docking_glow,
                        "docking_color": docking_color,
                        "docking_available": docking_available,
                        "breach": pod_state == "critical",
                        "state": pod_state,
                        "shuttle_count": max(1, int(req / 10)) if req > 0 else 0,
                    }

                    # Great-grandchildren (Compartments) inside pods
                    compartments = [by_id[ccid] for ccid in (pod.get("children") or []) if ccid in by_id]
                    for ci, comp in enumerate(compartments):
                        comp_size = 8
                        comp_x = pod_x + (ci - len(compartments) / 2) * (comp_size + 2)
                        comp_y = pod_y
                        comp_state = comp.get("state", "unknown")

                        layout[comp["id"]] = {
                            "x": comp_x - comp_size, "y": comp_y - comp_size,
                            "w": comp_size * 2, "h": comp_size * 2,
                            "cx": comp_x, "cy": comp_y,
                            "breach": comp_state == "critical",
                            "state": comp_state,
                        }

        # Handle entities not yet placed (standalone or orphaned)
        for e in entities:
            if e["id"] in layout:
                continue
            etype = e.get("type", "")
            metrics = e.get("metrics") or {}
            e_state = e.get("state", "unknown")
            if etype == "service":
                req = metrics.get("req_per_sec", 0)
                docking_glow = min(req / 50, 1.0) if req else 0.0
                layout[e["id"]] = {
                    "x": cx - 15, "y": cy - 15, "w": 30, "h": 30,
                    "cx": cx, "cy": cy,
                    "storage_fill": metrics.get("mem", 0) / 100,
                    "docking_glow": docking_glow,
                    "docking_color": DOCKING_GREEN if req < 10 else DOCKING_RED,
                    "docking_available": req < 10,
                    "breach": e_state == "critical",
                    "state": e_state,
                    "shuttle_count": max(1, int(req / 10)) if req > 0 else 0,
                }
            elif etype == "container":
                layout[e["id"]] = {
                    "x": cx - 8, "y": cy - 8, "w": 16, "h": 16,
                    "cx": cx, "cy": cy,
                    "breach": e_state == "critical",
                    "state": e_state,
                }
            else:
                layout[e["id"]] = {
                    "x": cx - 10, "y": cy - 10, "w": 20, "h": 20,
                    "cx": cx, "cy": cy,
                    "breach": e_state == "critical",
                    "state": e_state,
                }

        self._layout = layout
        return layout

    # ── Rendering ────────────────────────────────────────────────────────────

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the full space station scene with all visual layers."""
        layout = self.compute_layout(entities, w, h)
        by_id = {e["id"]: e for e in entities}

        # ── Layer 0: Deep space background with gradient ──
        self._render_background(ctx, w, h)

        # ── Layer 1: Parallax star field ──
        self._render_stars(ctx)

        # ── Layer 2: Floating debris / particles ──
        self._render_debris(ctx)

        # ── Layer 3: Station structure — corridors first (behind modules) ──
        self._render_corridors(entities, layout, ctx)

        # ── Layer 3b: Solar panels (behind modules) ──
        self._render_solar_panels(entities, layout, ctx)

        # ── Layer 4: Station entities ──
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            etype = entity.get("type", "")
            color = STATE_COLORS.get(entity.get("state", "unknown"), STATE_COLORS["unknown"])

            if etype == "cluster":
                self._render_station_hub(entity, pos, ctx, w, h)
            elif etype == "node":
                self._render_module(entity, pos, ctx)
            elif etype == "service":
                self._render_docking_port(entity, pos, ctx)
            elif etype == "container":
                self._render_compartment(entity, pos, ctx)

        # ── Layer 5: Effects (shuttle traffic, emergency pulses) ──
        self._render_shuttle_traffic(entities, layout, ctx)
        self._render_emergency_lighting(entities, layout, ctx)

        # ── Layer 6: Labels ──
        self._render_labels(entities, layout, ctx)

    # ── Layer 0: Background ──────────────────────────────────────────────────

    def _render_background(self, ctx: Any, w: int, h: int) -> None:
        """Deep space background with subtle gradient and nebula wisps."""
        # Base deep space fill
        ctx.fillStyle(BACKGROUND)
        ctx.fillRect(0, 0, w, h)

        # Subtle radial gradient for depth (dark center, slightly lighter edges)
        ctx.save()
        ctx.globalAlpha(0.08)
        ctx.fillStyle("#0a0a2a")
        # Top-left nebula wisp
        ctx.beginPath()
        ctx.arc(w * 0.2, h * 0.15, w * 0.25, 0, 2 * math.pi)
        ctx.fill()
        # Bottom-right nebula wisp
        ctx.fillStyle("#1a0520")
        ctx.beginPath()
        ctx.arc(w * 0.8, h * 0.85, w * 0.2, 0, 2 * math.pi)
        ctx.fill()
        ctx.globalAlpha(1.0)
        ctx.restore()

    # ── Layer 1: Parallax Stars ──────────────────────────────────────────────

    def _render_stars(self, ctx: Any) -> None:
        """Render 3-layer parallax star field with varying sizes."""
        for layer_idx, layer in enumerate(self._star_layers):
            for sx, sy, brightness, size in layer:
                ctx.globalAlpha(brightness)
                ctx.fillStyle(STAR_COLOR)
                ctx.fillRect(sx, sy, size, size)
                # Brighter stars get a subtle cross-shaped twinkle
                if brightness > 0.7 and size > 2:
                    ctx.globalAlpha(brightness * 0.4)
                    ctx.fillRect(sx - 1, sy + size / 2 - 0.25, size + 2, 0.5)
                    ctx.fillRect(sx + size / 2 - 0.25, sy - 1, 0.5, size + 2)
        ctx.globalAlpha(1.0)

    # ── Layer 2: Debris ──────────────────────────────────────────────────────

    def _render_debris(self, ctx: Any) -> None:
        """Floating debris particles drifting in vacuum."""
        for dx, dy, dsize, dopacity in self._debris:
            ctx.globalAlpha(dopacity)
            ctx.fillStyle(DEBRIS_COLOR)
            ctx.beginPath()
            ctx.arc(dx, dy, dsize, 0, 2 * math.pi)
            ctx.fill()
        ctx.globalAlpha(1.0)

    # ── Layer 3: Corridors ───────────────────────────────────────────────────

    def _render_corridors(self, entities: list[dict], layout: dict, ctx: Any) -> None:
        """Illuminated corridors connecting modules to central hub.

        Corridors have a dark interior with lit edge strips (like a hallway
        viewed from above with emergency floor lighting).
        """
        for entity in entities:
            if entity.get("type") != "node":
                continue
            pos = layout.get(entity["id"])
            parent_id = entity.get("parent")
            parent_pos = layout.get(parent_id) if parent_id else None
            if not pos or not parent_pos:
                continue

            is_critical = entity.get("state") == "critical"

            # Corridor outer shell (dark metal)
            ctx.strokeStyle(CORRIDOR_COLOR)
            ctx.lineWidth(6)
            ctx.beginPath()
            ctx.moveTo(parent_pos["cx"], parent_pos["cy"])
            ctx.lineTo(pos["cx"], pos["cy"])
            ctx.stroke()

            # Corridor inner (illuminated floor strip)
            corridor_color = PANEL_CRITICAL if is_critical else PANEL_LIT
            ctx.strokeStyle(corridor_color)
            ctx.lineWidth(2)
            ctx.globalAlpha(0.5)
            ctx.beginPath()
            ctx.moveTo(parent_pos["cx"], parent_pos["cy"])
            ctx.lineTo(pos["cx"], pos["cy"])
            ctx.stroke()
            ctx.globalAlpha(1.0)

            # Corridor edge lights (two parallel lines)
            angle = math.atan2(
                pos["cy"] - parent_pos["cy"],
                pos["cx"] - parent_pos["cx"]
            )
            perp_x = -math.sin(angle) * 3
            perp_y = math.cos(angle) * 3

            ctx.strokeStyle(corridor_color)
            ctx.lineWidth(0.5)
            ctx.globalAlpha(0.3)
            # Left edge
            ctx.beginPath()
            ctx.moveTo(parent_pos["cx"] + perp_x, parent_pos["cy"] + perp_y)
            ctx.lineTo(pos["cx"] + perp_x, pos["cy"] + perp_y)
            ctx.stroke()
            # Right edge
            ctx.beginPath()
            ctx.moveTo(parent_pos["cx"] - perp_x, parent_pos["cy"] - perp_y)
            ctx.lineTo(pos["cx"] - perp_x, pos["cy"] - perp_y)
            ctx.stroke()
            ctx.globalAlpha(1.0)

    # ── Layer 3b: Solar Panels ───────────────────────────────────────────────

    def _render_solar_panels(self, entities: list[dict], layout: dict, ctx: Any) -> None:
        """Solar panels extending from modules perpendicular to orbit direction."""
        for entity in entities:
            if entity.get("type") != "node":
                continue
            pos = layout.get(entity["id"])
            if not pos:
                continue

            angle = pos.get("solar_angle", 0)
            # Panels extend perpendicular to the radial direction
            perp_angle = angle + math.pi / 2
            panel_len = pos.get("solar_length", 30)
            panel_w = pos.get("solar_width", 8)
            mcx, mcy = pos["cx"], pos["cy"]

            # Two panels, one on each side
            for direction in (1, -1):
                # Panel center offset from module
                offset = (pos.get("mod_size", 30) + panel_len / 2 + 5)
                pcx = mcx + direction * panel_len / 2 * math.cos(perp_angle)
                pcy = mcy + direction * panel_len / 2 * math.sin(perp_angle)

                ctx.save()
                ctx.translate(pcx, pcy)
                ctx.rotate(perp_angle)

                # Panel body (dark blue)
                ctx.fillStyle(SOLAR_PANEL)
                ctx.fillRect(-panel_len / 2, -panel_w / 2, panel_len, panel_w)

                # Panel grid lines (cell divisions)
                ctx.strokeStyle(SOLAR_GLOW)
                ctx.lineWidth(0.5)
                ctx.globalAlpha(0.6)
                n_cells = 4
                for i in range(1, n_cells):
                    lx = -panel_len / 2 + (panel_len / n_cells) * i
                    ctx.beginPath()
                    ctx.moveTo(lx, -panel_w / 2)
                    ctx.lineTo(lx, panel_w / 2)
                    ctx.stroke()
                # Center line
                ctx.beginPath()
                ctx.moveTo(-panel_len / 2, 0)
                ctx.lineTo(panel_len / 2, 0)
                ctx.stroke()
                ctx.globalAlpha(1.0)

                # Panel border
                ctx.strokeStyle("#2a4a6a")
                ctx.lineWidth(1)
                ctx.strokeRect(-panel_len / 2, -panel_w / 2, panel_len, panel_w)

                # Strut connecting to module
                ctx.strokeStyle("#3a3a4e")
                ctx.lineWidth(2)
                ctx.beginPath()
                ctx.moveTo(-direction * (panel_len / 2 + 5), 0)
                ctx.lineTo(-direction * 5, 0)
                ctx.stroke()

                ctx.restore()

    # ── Layer 4a: Station Hub (Cluster) ──────────────────────────────────────

    def _render_station_hub(self, entity: dict, pos: dict, ctx: Any, w: int, h: int) -> None:
        """Central station hub with power core glow, ring, and control panels."""
        cx, cy = pos["cx"], pos["cy"]
        core_r = pos["core_radius"]
        ring_r = pos["ring_radius"]
        power = pos.get("power_glow", 0.5)
        is_critical = pos.get("breach", False)
        color = STATE_COLORS.get(pos.get("state", "unknown"), STATE_COLORS["unknown"])

        # Station ring (outer orbit track)
        ctx.strokeStyle(HUB_RING)
        ctx.lineWidth(1)
        ctx.globalAlpha(0.4)
        ctx.setLineDash([4, 8]) if hasattr(ctx, 'setLineDash') else None
        ctx.beginPath()
        ctx.arc(cx, cy, ring_r, 0, 2 * math.pi)
        ctx.stroke()
        ctx.globalAlpha(1.0)
        if hasattr(ctx, 'setLineDash'):
            ctx.setLineDash([])

        # Power core outer glow (CPU intensity)
        glow_r = core_r * 2.5
        ctx.globalAlpha(0.08 + 0.15 * power)
        ctx.fillStyle(CORE_GLOW)
        ctx.beginPath()
        ctx.arc(cx, cy, glow_r, 0, 2 * math.pi)
        ctx.fill()

        # Power core mid glow
        ctx.globalAlpha(0.15 + 0.35 * power)
        ctx.fillStyle(CORE_GLOW)
        ctx.beginPath()
        ctx.arc(cx, cy, core_r * 1.5, 0, 2 * math.pi)
        ctx.fill()

        # Power core inner (bright center)
        ctx.globalAlpha(0.3 + 0.5 * power)
        core_color = PANEL_CRITICAL if is_critical else CORE_GLOW
        ctx.fillStyle(core_color)
        ctx.beginPath()
        ctx.arc(cx, cy, core_r, 0, 2 * math.pi)
        ctx.fill()
        ctx.globalAlpha(1.0)

        # Core outline ring
        ctx.strokeStyle(color)
        ctx.lineWidth(2)
        ctx.beginPath()
        ctx.arc(cx, cy, core_r, 0, 2 * math.pi)
        ctx.stroke()

        # Control panel glow (blue screens around core)
        n_panels = 4
        for i in range(n_panels):
            panel_angle = (2 * math.pi * i) / n_panels + math.pi / 4
            px = cx + (core_r + 8) * math.cos(panel_angle)
            py = cy + (core_r + 8) * math.sin(panel_angle)
            pw, ph = 10, 6

            ctx.save()
            ctx.translate(px, py)
            ctx.rotate(panel_angle)

            # Screen background
            ctx.fillStyle("#0a0a1a")
            ctx.fillRect(-pw / 2, -ph / 2, pw, ph)

            # Screen glow (blue)
            screen_color = PANEL_CRITICAL if is_critical else PANEL_LIT
            ctx.globalAlpha(0.6 + 0.3 * math.sin(i))  # slight variation
            ctx.fillStyle(screen_color)
            ctx.fillRect(-pw / 2 + 1, -ph / 2 + 1, pw - 2, ph - 2)
            ctx.globalAlpha(1.0)

            # Screen border
            ctx.strokeStyle("#334466")
            ctx.lineWidth(0.5)
            ctx.strokeRect(-pw / 2, -ph / 2, pw, ph)

            ctx.restore()

        # Breach animation for critical hub
        if is_critical:
            self._render_breach_effect(ctx, cx, cy, core_r * 1.2)

    # ── Layer 4b: Module (Node) ──────────────────────────────────────────────

    def _render_module(self, entity: dict, pos: dict, ctx: Any) -> None:
        """Orbiting module with architectural detail, life support LEDs, and status."""
        cx, cy = pos["cx"], pos["cy"]
        r = pos["w"] / 2
        color = pos.get("life_support_color", STATE_COLORS["unknown"])
        is_critical = pos.get("breach", False)

        # Module body (dark metal cylinder)
        ctx.fillStyle("#0d0d1a" if not is_critical else "#1a0505")
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.fill()

        # Module hull (metallic ring)
        ctx.strokeStyle(MODULE_BODY)
        ctx.lineWidth(2)
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.stroke()

        # Life support indicator ring (colored arc)
        ctx.strokeStyle(color)
        ctx.lineWidth(3)
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.stroke()

        # Inner detail ring
        ctx.strokeStyle("#1a1a2e")
        ctx.lineWidth(1)
        ctx.beginPath()
        ctx.arc(cx, cy, r * 0.7, 0, 2 * math.pi)
        ctx.stroke()

        # Life support LED indicators (3 dots: power, data, env)
        led_y = cy - r * 0.3
        led_spacing = 6
        led_r = 2
        leds = [
            pos.get("led_power", True),
            pos.get("led_data", False),
            pos.get("led_env", True),
        ]
        led_colors = ["#44ff44", "#44aaff", "#ffaa44"]
        for li, (active, lcolor) in enumerate(zip(leds, led_colors)):
            lx = cx + (li - 1) * led_spacing
            if active:
                # LED glow
                ctx.globalAlpha(0.3)
                ctx.fillStyle(lcolor)
                ctx.beginPath()
                ctx.arc(lx, led_y, led_r + 1.5, 0, 2 * math.pi)
                ctx.fill()
                # LED core
                ctx.globalAlpha(1.0)
                ctx.fillStyle(lcolor)
                ctx.beginPath()
                ctx.arc(lx, led_y, led_r, 0, 2 * math.pi)
                ctx.fill()
            else:
                # Inactive LED (dim)
                ctx.globalAlpha(0.3)
                ctx.fillStyle("#333344")
                ctx.beginPath()
                ctx.arc(lx, led_y, led_r, 0, 2 * math.pi)
                ctx.fill()
                ctx.globalAlpha(1.0)

        # Control panel (small blue screen on module)
        panel_w, panel_h = 12, 5
        panel_x = cx - panel_w / 2
        panel_y = cy + r * 0.1
        ctx.fillStyle("#0a0a1a")
        ctx.fillRect(panel_x, panel_y, panel_w, panel_h)
        screen_color = PANEL_CRITICAL if is_critical else PANEL_LIT
        ctx.globalAlpha(0.5)
        ctx.fillStyle(screen_color)
        ctx.fillRect(panel_x + 1, panel_y + 1, panel_w - 2, panel_h - 2)
        ctx.globalAlpha(1.0)
        ctx.strokeStyle("#334466")
        ctx.lineWidth(0.5)
        ctx.strokeRect(panel_x, panel_y, panel_w, panel_h)

        # Breach animation for critical modules
        if is_critical:
            self._render_breach_effect(ctx, cx, cy, r)

    # ── Layer 4c: Docking Port (Service/Pod) ─────────────────────────────────

    def _render_docking_port(self, entity: dict, pos: dict, ctx: Any) -> None:
        """Docking port with animated ring, shuttle traffic glow, storage fill."""
        cx, cy = pos["cx"], pos["cy"]
        r = pos["w"] / 2
        glow = pos.get("docking_glow", 0)
        dock_color = pos.get("docking_color", DOCKING_GREEN)
        is_critical = pos.get("breach", False)
        color = STATE_COLORS.get(pos.get("state", "unknown"), STATE_COLORS["unknown"])

        # Docking glow halo (request traffic intensity)
        if glow > 0:
            ctx.globalAlpha(glow * 0.3)
            ctx.fillStyle("#38bdf8")
            ctx.beginPath()
            ctx.arc(cx, cy, r + 8, 0, 2 * math.pi)
            ctx.fill()
            ctx.globalAlpha(1.0)

        # Docking ring (animated — green=available, red=occupied)
        ctx.strokeStyle(dock_color)
        ctx.lineWidth(2)
        ctx.beginPath()
        ctx.arc(cx, cy, r + 3, 0, 2 * math.pi)
        ctx.stroke()

        # Inner docking ring
        ctx.strokeStyle(dock_color)
        ctx.lineWidth(1)
        ctx.globalAlpha(0.5)
        ctx.beginPath()
        ctx.arc(cx, cy, r + 1, 0, 2 * math.pi)
        ctx.stroke()
        ctx.globalAlpha(1.0)

        # Pod body
        ctx.fillStyle(color)
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.fill()

        # Storage bay fill (memory — bottom-up fill)
        fill_h = pos["h"] * pos.get("storage_fill", 0)
        if fill_h > 0:
            ctx.save()
            ctx.beginPath()
            ctx.arc(cx, cy, r, 0, 2 * math.pi)
            ctx.clip()
            ctx.globalAlpha(0.4)
            ctx.fillStyle("#60a5fa")
            ctx.fillRect(pos["x"], pos["y"] + pos["h"] - fill_h, pos["w"], fill_h)
            ctx.globalAlpha(1.0)
            ctx.restore()

        # Docking port markers (4 cardinal direction nubs)
        for angle_offset in [0, math.pi / 2, math.pi, 3 * math.pi / 2]:
            nx = cx + (r + 5) * math.cos(angle_offset)
            ny = cy + (r + 5) * math.sin(angle_offset)
            ctx.fillStyle(dock_color)
            ctx.globalAlpha(0.7)
            ctx.fillRect(nx - 1.5, ny - 1.5, 3, 3)
            ctx.globalAlpha(1.0)

        # Breach sparks
        if is_critical:
            self._render_breach_effect(ctx, cx, cy, r)

    # ── Layer 4d: Compartment (Container) ────────────────────────────────────

    def _render_compartment(self, entity: dict, pos: dict, ctx: Any) -> None:
        """Internal compartment bay with status indicator."""
        x, y, bw, bh = pos["x"], pos["y"], pos["w"], pos["h"]
        is_critical = pos.get("breach", False)
        color = STATE_COLORS.get(pos.get("state", "unknown"), STATE_COLORS["unknown"])

        # Compartment body
        ctx.fillStyle(color)
        ctx.fillRect(x, y, bw, bh)

        # Compartment frame (metal edges)
        ctx.strokeStyle("#1a1a2e")
        ctx.lineWidth(1)
        ctx.strokeRect(x, y, bw, bh)

        # Inner detail line
        ctx.strokeStyle("#0a0a15")
        ctx.lineWidth(0.5)
        ctx.beginPath()
        ctx.moveTo(x + 2, y + bh / 2)
        ctx.lineTo(x + bw - 2, y + bh / 2)
        ctx.stroke()

        # Breach flash (red alert overlay)
        if is_critical:
            ctx.globalAlpha(0.6)
            ctx.fillStyle(PANEL_CRITICAL)
            ctx.fillRect(x - 2, y - 2, bw + 4, bh + 4)
            ctx.globalAlpha(1.0)

    # ── Layer 5: Shuttle Traffic ─────────────────────────────────────────────

    def _render_shuttle_traffic(self, entities: list[dict], layout: dict, ctx: Any) -> None:
        """Shuttle traffic dots approaching docking ports."""
        for entity in entities:
            if entity.get("type") != "service":
                continue
            pos = layout.get(entity["id"])
            if not pos:
                continue
            shuttle_count = pos.get("shuttle_count", 0)
            if shuttle_count <= 0:
                continue

            cx, cy = pos["cx"], pos["cy"]
            r = pos["w"] / 2

            # Shuttles approach from random angles (deterministic per entity)
            rng = random.Random(hash(entity["id"]) & 0xFFFF)
            for si in range(shuttle_count):
                approach_angle = rng.uniform(0, 2 * math.pi)
                approach_dist = r + 12 + si * 6
                sx = cx + approach_dist * math.cos(approach_angle)
                sy = cy + approach_dist * math.sin(approach_angle)

                # Shuttle body (small triangle pointing toward port)
                ctx.fillStyle("#88ccff")
                ctx.globalAlpha(0.7)
                ctx.beginPath()
                ctx.arc(sx, sy, 2, 0, 2 * math.pi)
                ctx.fill()

                # Engine trail
                trail_angle = approach_angle + math.pi  # opposite direction
                trail_len = 4
                tx = sx + trail_len * math.cos(trail_angle)
                ty = sy + trail_len * math.sin(trail_angle)
                ctx.strokeStyle("#44aaff")
                ctx.lineWidth(1)
                ctx.globalAlpha(0.4)
                ctx.beginPath()
                ctx.moveTo(sx, sy)
                ctx.lineTo(tx, ty)
                ctx.stroke()
                ctx.globalAlpha(1.0)

    # ── Layer 5b: Emergency Lighting ─────────────────────────────────────────

    def _render_emergency_lighting(self, entities: list[dict], layout: dict, ctx: Any) -> None:
        """Red pulsing emergency lights for critical entities."""
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos or not pos.get("breach"):
                continue

            cx, cy = pos["cx"], pos["cy"]
            r = pos.get("w", 20) / 2

            # Emergency pulse ring (expanding red ring)
            ctx.strokeStyle(EMERGENCY_RED)
            ctx.lineWidth(1.5)
            ctx.globalAlpha(0.4)
            ctx.beginPath()
            ctx.arc(cx, cy, r + 8, 0, 2 * math.pi)
            ctx.stroke()

            # Second pulse ring (larger, dimmer)
            ctx.globalAlpha(0.2)
            ctx.beginPath()
            ctx.arc(cx, cy, r + 14, 0, 2 * math.pi)
            ctx.stroke()
            ctx.globalAlpha(1.0)

    # ── Breach Effect ────────────────────────────────────────────────────────

    def _render_breach_effect(self, ctx: Any, cx: float, cy: float, r: float) -> None:
        """Hull breach animation: sparks radiating outward + red alert flash."""
        # Sparks
        ctx.strokeStyle(PANEL_CRITICAL)
        ctx.lineWidth(1)
        rng = random.Random(int(cx * 100 + cy))
        for _ in range(8):
            spark_angle = rng.uniform(0, 2 * math.pi)
            spark_start = r * 0.8
            spark_len = rng.uniform(4, 14)
            sx = cx + spark_start * math.cos(spark_angle)
            sy = cy + spark_start * math.sin(spark_angle)
            ex = cx + (spark_start + spark_len) * math.cos(spark_angle)
            ey = cy + (spark_start + spark_len) * math.sin(spark_angle)
            ctx.beginPath()
            ctx.moveTo(sx, sy)
            ctx.lineTo(ex, ey)
            ctx.stroke()

        # Red alert inner flash
        ctx.globalAlpha(0.15)
        ctx.fillStyle(PANEL_CRITICAL)
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.fill()
        ctx.globalAlpha(1.0)

    # ── Layer 6: Labels ──────────────────────────────────────────────────────

    def _render_labels(self, entities: list[dict], layout: dict, ctx: Any) -> None:
        """HUD overlay labels with glow for readability."""
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            etype = entity.get("type", "")
            name = entity.get("name", "")
            cx, cy = pos["cx"], pos["cy"]

            if etype == "cluster":
                # Large label centered on hub
                ctx.fillStyle("#e2e8f0")
                ctx.font("bold 13px system-ui, sans-serif")
                ctx.fillText(name, cx - 30, cy + 4)
            elif etype == "node":
                # Label below module
                r = pos["w"] / 2
                ctx.fillStyle("#d1d5db")
                ctx.font("10px system-ui, sans-serif")
                ctx.fillText(name[:14], cx - 20, cy + r + 14)
            elif etype == "service":
                # Small label below pod
                r = pos["w"] / 2
                ctx.fillStyle("#fff")
                ctx.font("8px system-ui, sans-serif")
                ctx.fillText(name[:10], cx - 12, cy + r + 10)

    # ── Tooltip ──────────────────────────────────────────────────────────────

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Generate tooltip with space station terminology."""
        etype = entity.get("type", "?")
        mapping = {
            "cluster": "Station Ring",
            "node": "Module",
            "service": "Pod",
            "container": "Compartment",
        }
        label = mapping.get(etype, etype)

        lines = [
            f"{entity.get('name', '?')} ({label})",
            f"Life Support: {LIFE_SUPPORT.get(str(entity.get('state', 'unknown')), 'unknown')}",
        ]
        m = entity.get("metrics") or {}
        if "cpu" in m:
            lines.append(f"Power Core: {m['cpu']}%")
        if "mem" in m:
            lines.append(f"Storage Bay: {m['mem']}%")
        if "cpu_pct" in m:
            lines.append(f"Power Core: {m['cpu_pct']}%")
        if "mem_pct" in m:
            lines.append(f"Storage Bay: {m['mem_pct']}%")
        if "req_per_sec" in m:
            lines.append(f"Shuttle Traffic: {m['req_per_sec']} req/s")
        if "error_rate" in m:
            lines.append(f"Hull Breach Rate: {m['error_rate'] * 100:.1f}%")
        if "count" in m:
            lines.append(f"Crew: {m['count']}")
        if "uptime_hrs" in m:
            lines.append(f"Mission Time: {m['uptime_hrs']}h")
        return "\n".join(lines)

    # ── Hit Test ─────────────────────────────────────────────────────────────

    def hit_test(self, entity: dict[str, Any], x: int, y: int) -> bool:
        """Check if (x,y) falls within this entity's layout bounds."""
        pos = self._layout.get(entity.get("id"))
        if not pos:
            return False
        return (pos["x"] <= x <= pos["x"] + pos["w"] and
                pos["y"] <= y <= pos["y"] + pos["h"])

    # ── Config ───────────────────────────────────────────────────────────────

    def config(self) -> dict[str, Any]:
        """Return metaphor configuration metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "state_colors": STATE_COLORS,
            "mappings": {
                "cluster": "station ring",
                "node": "module",
                "service": "pod",
                "container": "compartment",
            },
        }
