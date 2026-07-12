"""Garden metaphor renderer — Cluster→Garden Bed, Node→Planting Row,
Service→Plant/Tree, Container→Branch.

Full visual overhaul following VISUAL_GUIDELINES.md:
- Sky gradient (day: blue → night: dark purple) with time-of-day sun
- Rich soil texture (brown with pebble/grass detail)
- Plants with actual shapes: trees (trunk + canopy), flowers (stem + petals), bushes
- Growth animation: plants grow/shrink with CPU
- Leaf color change: green=healthy, yellow=warning, brown=critical
- Flowers blooming for active services
- Water flow through irrigation channels (animated blue)
- Butterflies/bees for active containers
- Dew drops on idle plants
- Sun position based on time of day
- Fence/border around garden beds
- Pathways between beds
- Fireflies at night
"""
from __future__ import annotations
import math
import time as _time
from typing import Any
from engine.metaphors.base import MetaphorRenderer


# Health → leaf color (VISUAL_GUIDELINES.md garden palette)
HEALTH_COLORS = {
    "healthy": "#4ade80",   # lush bright green
    "running": "#22c55e",   # vibrant green
    "idle": "#86efac",      # pale green
    "warning": "#fbbf24",   # yellowing
    "degraded": "#eab308",  # sickly yellow
    "critical": "#92400e",  # brown/dying
    "stopped": "#78350f",   # dead brown
    "pending": "#a3e635",   # sprouting lime
    "scaling": "#34d399",   # growing green
    "unknown": "#6b7280",   # grey
}

# Sun/light color by cluster health
SUN_COLORS = {
    "healthy": "#fbbf24",
    "running": "#f59e0b",
    "idle": "#fde68a",
    "warning": "#f97316",
    "degraded": "#ef4444",
    "critical": "#991b1b",
    "stopped": "#374151",
    "unknown": "#9ca3af",
}

# Garden palette from VISUAL_GUIDELINES.md
SKY_DAY_TOP = "#87ceeb"       # sky blue
SKY_DAY_BOTTOM = "#b0e0e6"    # light powder blue
SKY_NIGHT_TOP = "#1a0a2e"     # dark purple
SKY_NIGHT_BOTTOM = "#2d1b4e"  # deep violet
SKY_SUNSET_TOP = "#ff7e5f"    # warm orange
SKY_SUNSET_BOTTOM = "#feb47b" # peach

SOIL_DARK = "#3d2817"         # rich brown (VISUAL_GUIDELINES)
SOIL_MID = "#5c3d2e"          # medium brown
SOIL_LIGHT = "#6b4c3b"        # lighter brown
GRASS_GREEN = "#228b22"       # forest green
GRASS_LIGHT = "#32cd32"       # lime green

# Flower colors for active services
FLOWER_COLORS = ["#ff69b4", "#f472b6", "#fb923c", "#a78bfa", "#f87171", "#38bdf8", "#facc15"]

# Butterfly/bee colors
BUTTERFLY_COLORS = ["#c084fc", "#fb7185", "#38bdf8", "#fbbf24", "#f472b6"]
BEE_BODY = "#fbbf24"
BEE_STRIPE = "#1a1a1a"

# Dew drop
DEW_COLOR = "#bae6fd"
DEW_SHINE = "#ffffff"

# Weed color (error processes)
WEED_COLOR = "#4b5563"

# Irrigation water
WATER_COLOR = "#4488ff"       # blue per VISUAL_GUIDELINES
WATER_LIGHT = "#7dd3fc"
WATER_DARK = "#2563eb"

# Fence
FENCE_POST = "#8B6914"        # wooden brown
FENCE_RAIL = "#A0824A"        # lighter wood

# Pathway
PATH_COLOR = "#c4a882"        # sandy dirt
PATH_EDGE = "#a08060"         # darker edge

# Firefly
FIREFLY_COLOR = "#ffd700"     # gold glow

# Sun
SUN_COLOR = "#ffd700"         # gold per VISUAL_GUIDELINES
SUN_GLOW = "#fff3b0"


def _get_time_of_day() -> float:
    """Return current time as 0.0-1.0 (0=midnight, 0.5=noon, 1.0=midnight)."""
    t = _time.time()
    return (t % 86400) / 86400.0


def _is_night(tod: float) -> bool:
    """Return True if time-of-day is nighttime (before 6am or after 8pm)."""
    return tod < 0.25 or tod > 0.833


def _lerp_color(c1: str, c2: str, t: float) -> str:
    """Linearly interpolate between two hex colors."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _sky_colors_for_time(tod: float) -> tuple[str, str]:
    """Return (top, bottom) sky gradient colors for time of day."""
    # Night: 0.0-0.25 and 0.833-1.0
    # Dawn: 0.25-0.33
    # Day: 0.33-0.75
    # Sunset: 0.75-0.833
    if tod < 0.25:
        return SKY_NIGHT_TOP, SKY_NIGHT_BOTTOM
    elif tod < 0.33:
        t = (tod - 0.25) / 0.08
        top = _lerp_color(SKY_NIGHT_TOP, SKY_SUNSET_TOP, t)
        bot = _lerp_color(SKY_NIGHT_BOTTOM, SKY_SUNSET_BOTTOM, t)
        return top, bot
    elif tod < 0.42:
        t = (tod - 0.33) / 0.09
        top = _lerp_color(SKY_SUNSET_TOP, SKY_DAY_TOP, t)
        bot = _lerp_color(SKY_SUNSET_BOTTOM, SKY_DAY_BOTTOM, t)
        return top, bot
    elif tod < 0.75:
        return SKY_DAY_TOP, SKY_DAY_BOTTOM
    elif tod < 0.833:
        t = (tod - 0.75) / 0.083
        top = _lerp_color(SKY_DAY_TOP, SKY_SUNSET_TOP, t)
        bot = _lerp_color(SKY_DAY_BOTTOM, SKY_SUNSET_BOTTOM, t)
        return top, bot
    else:
        t = (tod - 0.833) / 0.167
        top = _lerp_color(SKY_SUNSET_TOP, SKY_NIGHT_TOP, t)
        bot = _lerp_color(SKY_SUNSET_BOTTOM, SKY_NIGHT_BOTTOM, t)
        return top, bot


def _sun_position(tod: float, w: int, h: int) -> tuple[float, float, float]:
    """Return (x, y, radius) of sun based on time of day.
    Sun arcs from left (dawn) to right (dusk), high at noon.
    Returns (-100, -100, 0) if sun is below horizon (night).
    """
    if tod < 0.25 or tod > 0.833:
        return -100, -100, 0  # below horizon
    # Map 0.25-0.833 to 0-PI for arc
    t = (tod - 0.25) / 0.583
    angle = math.pi * t  # 0 to PI
    sky_h = h * 0.35
    x = w * 0.1 + (w * 0.8) * t
    y = sky_h - math.sin(angle) * (sky_h * 0.7) + sky_h * 0.3
    r = 20 + 10 * math.sin(angle)  # bigger at noon
    return x, y, r


class GardenRenderer(MetaphorRenderer):
    """Garden metaphor: infrastructure as a living garden.

    Cluster = Garden Bed (fenced plot with rich soil)
    Node = Planting Row (furrowed strip with pathways)
    Service = Plant/Tree (grows with CPU, leaves colored by health)
    Container = Branch (sub-element of a plant)

    Visual elements:
    - Sky gradient changes with time of day (blue→purple)
    - Sun arcs across sky based on real time
    - Fireflies glow at night
    - Rich soil texture with pebbles and grass tufts
    - Wooden fence around garden beds
    - Dirt pathways between beds
    - Trees with trunk + canopy, flowers with stem + petals, bushes
    - Plants grow/shrink with CPU usage
    - Leaf color reflects health (green→yellow→brown)
    - Flowers bloom on active/healthy services
    - Dew drops on idle plants
    - Butterflies and bees flutter around active containers
    - Irrigation channels with flowing water animation
    - Weeds sprout for error/critical services
    """

    name = "garden"
    description = "Infrastructure as a living garden with organic growth and ambient life"

    def __init__(self):
        self._layout: dict[str, dict[str, float]] = {}
        self._anim_time: float = 0.0

    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, float]]:
        """Compute organic positions for all entities.

        Uses golden-ratio-based spacing for natural feel.
        Returns layout dict keyed by entity id.
        """
        layout: dict[str, dict[str, float]] = {}
        if not entities:
            self._layout = layout
            return layout

        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        # Reserve top 25% for sky/sun, bottom 8% for foreground grass
        sky_h = h * 0.25
        ground_h = h * 0.08
        garden_top = sky_h
        garden_h = h - sky_h - ground_h

        # Garden beds (clusters) spread horizontally with pathway gaps
        n_roots = max(len(roots), 1)
        pathway_w = 16  # wider pathways between beds
        bed_gap = pathway_w + 8
        total_gap = bed_gap * (n_roots + 1)
        bed_w = max(40, (w - total_gap) / n_roots)

        for di, root in enumerate(roots):
            bx = bed_gap + di * (bed_w + bed_gap)
            by = garden_top
            layout[root["id"]] = {"x": bx, "y": by, "w": bed_w, "h": garden_h}

            # Planting rows (nodes) stack vertically inside bed
            children = [by_id[cid] for cid in (root.get("children") or []) if cid in by_id]
            n_children = max(len(children), 1)
            row_gap = 10
            row_h = (garden_h - row_gap * (n_children + 1)) / max(n_children, 1)

            for ri, child in enumerate(children):
                rx = bx + row_gap
                ry = by + row_gap + ri * (row_h + row_gap)
                rw = bed_w - 2 * row_gap
                layout[child["id"]] = {"x": rx, "y": ry, "w": rw, "h": row_h}

                # Plants (services) spread along the row with organic spacing
                grandchildren = [by_id[gcid] for gcid in (child.get("children") or [])
                                 if gcid in by_id]
                if not grandchildren:
                    continue
                n_gc = len(grandchildren)
                plant_gap = 8
                plant_w = max(12, (rw - plant_gap * (n_gc + 1)) / n_gc)

                for gi, gc in enumerate(grandchildren):
                    cpu = (gc.get("metrics") or {}).get("cpu", 30)
                    # Plant height grows with CPU (min 20, max 90% of row)
                    max_ph = row_h - 20
                    ph = max(20, max_ph * (cpu / 100))
                    px = rx + plant_gap + gi * (plant_w + plant_gap)
                    # Plant grows upward from bottom of row
                    py = ry + row_h - ph
                    layout[gc["id"]] = {"x": px, "y": py, "w": plant_w, "h": ph}

                    # Containers (branches) as sub-elements
                    great_grandchildren = [by_id[ggcid] for ggcid in (gc.get("children") or [])
                                           if ggcid in by_id]
                    if not great_grandchildren:
                        continue
                    n_ggc = len(great_grandchildren)
                    branch_h = ph / max(n_ggc, 1)
                    for bi, ggc in enumerate(great_grandchildren):
                        branch_y = py + bi * branch_h
                        layout[ggc["id"]] = {
                            "x": px + plant_w * 0.2,
                            "y": branch_y,
                            "w": plant_w * 0.6,
                            "h": branch_h * 0.8,
                        }

        self._layout = layout
        return layout

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the garden metaphor with full visual overhaul."""
        self._anim_time = _time.time()
        layout = self.compute_layout(entities, w, h)
        tod = _get_time_of_day()
        night = _is_night(tod)

        # === LAYER 0: Sky gradient ===
        self._draw_sky(ctx, w, h, tod)

        # === LAYER 1: Sun ===
        self._draw_sun(entities, ctx, w, h, tod)

        # === LAYER 2: Ground / grass base ===
        self._draw_ground(ctx, w, h)

        # === LAYER 3: Pathways between beds ===
        self._draw_pathways(entities, layout, ctx, w, h)

        # === LAYER 4: Garden beds with fence and rich soil ===
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            etype = entity.get("type", "")
            if etype == "cluster":
                self._draw_garden_bed(entity, pos, ctx)

        # === LAYER 5: Planting rows ===
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            if entity.get("type", "") == "node":
                self._draw_planting_row(entity, pos, ctx)

        # === LAYER 6: Plants (services) ===
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            state = entity.get("state", "unknown")
            if entity.get("type", "") == "service":
                self._draw_plant(entity, pos, ctx, state)

        # === LAYER 7: Branches (containers) ===
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            if entity.get("type", "") == "container":
                self._draw_branch(entity, pos, ctx)

        # === LAYER 8: Irrigation channels (animated water) ===
        self._draw_irrigation(entities, layout, ctx)

        # === LAYER 9: Weeds for errors ===
        self._draw_weeds(entities, layout, ctx)

        # === LAYER 10: Butterflies/bees for active containers ===
        self._draw_butterflies(entities, layout, ctx)

        # === LAYER 11: Fireflies at night ===
        if night:
            self._draw_fireflies(entities, layout, ctx, w, h)

    # ─── Sky ────────────────────────────────────────────────────────────

    def _draw_sky(self, ctx: Any, w: int, h: int, tod: float):
        """Draw sky gradient — day: blue, night: dark purple."""
        sky_top, sky_bottom = _sky_colors_for_time(tod)
        sky_h = h * 0.30

        # Gradient sky (approximated with horizontal bands)
        n_bands = 8
        band_h = sky_h / n_bands
        for i in range(n_bands):
            t = i / max(n_bands - 1, 1)
            color = _lerp_color(sky_top, sky_bottom, t)
            ctx.fillStyle(color)
            ctx.fillRect(0, i * band_h, w, band_h + 1)

        # Stars at night
        if _is_night(tod):
            self._draw_stars(ctx, w, sky_h)

    def _draw_stars(self, ctx: Any, w: int, sky_h: float):
        """Draw twinkling stars in night sky."""
        ctx.save()
        # Deterministic star positions based on canvas width
        import hashlib
        for i in range(30):
            seed = int(hashlib.md5(f"star{i}".encode()).hexdigest()[:8], 16)
            sx = (seed % int(w)) if w > 0 else 0
            sy = (seed >> 8) % int(max(sky_h * 0.8, 1))
            brightness = 0.3 + 0.7 * ((seed >> 16) % 100) / 100
            # Twinkle effect
            twinkle = 0.5 + 0.5 * math.sin(self._anim_time * 2 + i * 0.7)
            alpha = brightness * twinkle
            ctx.globalAlpha(alpha)
            ctx.fillStyle("#ffffff")
            ctx.beginPath()
            ctx.arc(sx, sy, 1.2, 0, 2 * math.pi)
            ctx.fill()
        ctx.restore()

    # ─── Sun ────────────────────────────────────────────────────────────

    def _draw_sun(self, entities: list[dict], ctx: Any, w: int, h: int, tod: float):
        """Draw sun at position based on time of day, color by cluster health."""
        # Determine overall health from root clusters
        roots = [e for e in entities if not e.get("parent") and e.get("type") == "cluster"]
        if not roots:
            return

        health_priority = {"healthy": 0, "running": 0, "idle": 1, "warning": 2,
                          "degraded": 3, "critical": 4, "stopped": 5, "unknown": 3}
        worst = max(roots, key=lambda r: health_priority.get(r.get("state", "unknown"), 3))
        sun_color = SUN_COLORS.get(worst.get("state", "unknown"), SUN_COLORS["unknown"])

        sun_x, sun_y, sun_r = _sun_position(tod, w, h)
        if sun_r <= 0:
            return  # sun below horizon

        # Outer glow
        ctx.save()
        ctx.globalAlpha(0.15)
        ctx.fillStyle(sun_color)
        ctx.beginPath()
        ctx.arc(sun_x, sun_y, sun_r + 20, 0, 2 * math.pi)
        ctx.fill()

        # Mid glow
        ctx.globalAlpha(0.25)
        ctx.beginPath()
        ctx.arc(sun_x, sun_y, sun_r + 10, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # Sun body
        ctx.fillStyle(sun_color)
        ctx.beginPath()
        ctx.arc(sun_x, sun_y, sun_r, 0, 2 * math.pi)
        ctx.fill()

        # Sun rays
        ctx.save()
        ctx.strokeStyle(sun_color)
        ctx.lineWidth(1.5)
        ctx.globalAlpha(0.4)
        n_rays = 12
        for i in range(n_rays):
            angle = (2 * math.pi / n_rays) * i + self._anim_time * 0.1
            inner_r = sun_r + 4
            outer_r = sun_r + 12 + 3 * math.sin(self._anim_time * 1.5 + i)
            x1 = sun_x + math.cos(angle) * inner_r
            y1 = sun_y + math.sin(angle) * inner_r
            x2 = sun_x + math.cos(angle) * outer_r
            y2 = sun_y + math.sin(angle) * outer_r
            ctx.moveTo(x1, y1)
            ctx.lineTo(x2, y2)
        ctx.stroke()
        ctx.restore()

    # ─── Ground ─────────────────────────────────────────────────────────

    def _draw_ground(self, ctx: Any, w: int, h: int):
        """Draw rich soil ground with texture detail."""
        ground_y = h * 0.88
        ground_h = h - ground_y

        # Base soil
        ctx.fillStyle(SOIL_DARK)
        ctx.fillRect(0, ground_y, w, ground_h)

        # Soil texture — darker patches
        ctx.fillStyle(SOIL_MID)
        for i in range(0, int(w), 12):
            patch_w = 8 + (i * 7) % 6
            ctx.fillRect(i, ground_y + 2, patch_w, 3)

        # Grass tufts along the top edge
        ctx.fillStyle(GRASS_GREEN)
        for i in range(0, int(w), 6):
            gh = 3 + (i * 13) % 5
            ctx.fillRect(i, ground_y - gh, 2, gh)
            # Lighter grass
            ctx.fillStyle(GRASS_LIGHT)
            ctx.fillRect(i + 3, ground_y - gh + 1, 1, gh - 1)
            ctx.fillStyle(GRASS_GREEN)

        # Small pebbles
        ctx.fillStyle("#8b7d6b")
        for i in range(0, int(w), 20):
            px = i + (i * 17) % 10
            py = ground_y + 6 + (i * 11) % int(max(ground_h - 8, 1))
            ctx.beginPath()
            ctx.arc(px, py, 1.5, 0, 2 * math.pi)
            ctx.fill()

    # ─── Pathways ───────────────────────────────────────────────────────

    def _draw_pathways(self, entities: list[dict], layout: dict, ctx: Any, w: int, h: int):
        """Draw dirt pathways between garden beds."""
        roots = [e for e in entities if not e.get("parent") and e.get("type") == "cluster"]
        if len(roots) < 2:
            return

        garden_top = h * 0.25
        garden_bottom = h * 0.88

        for i in range(len(roots) - 1):
            pos_a = layout.get(roots[i]["id"])
            pos_b = layout.get(roots[i + 1]["id"])
            if not pos_a or not pos_b:
                continue

            # Pathway between two adjacent beds
            path_left = pos_a["x"] + pos_a["w"]
            path_right = pos_b["x"]
            path_w = path_right - path_left

            if path_w <= 0:
                continue

            # Path fill
            ctx.fillStyle(PATH_COLOR)
            ctx.fillRect(path_left, garden_top, path_w, garden_bottom - garden_top)

            # Path edges (darker lines)
            ctx.strokeStyle(PATH_EDGE)
            ctx.lineWidth(1)
            ctx.moveTo(path_left + 1, garden_top)
            ctx.lineTo(path_left + 1, garden_bottom)
            ctx.stroke()
            ctx.moveTo(path_right - 1, garden_top)
            ctx.lineTo(path_right - 1, garden_bottom)
            ctx.stroke()

            # Footprint texture
            ctx.fillStyle("#b09870")
            for j in range(int(garden_top), int(garden_bottom), 18):
                fx = path_left + path_w * 0.3 + (j * 7) % int(max(path_w * 0.4, 1))
                ctx.beginPath()
                ctx.arc(fx, j, 1.5, 0, 2 * math.pi)
                ctx.fill()

    # ─── Garden Bed ─────────────────────────────────────────────────────

    def _draw_garden_bed(self, entity: dict, pos: dict, ctx: Any):
        """Draw garden bed — rich soil with wooden fence border."""
        x, y, w, h = pos["x"], pos["y"], pos["w"], pos["h"]

        # Rich soil fill with layers
        ctx.fillStyle(SOIL_DARK)
        ctx.fillRect(x, y, w, h)

        # Soil texture — horizontal strata
        ctx.fillStyle(SOIL_MID)
        for i in range(0, int(h), 8):
            ctx.fillRect(x + 2, y + i, w - 4, 2)

        # Soil detail — small dark spots
        ctx.fillStyle(SOIL_LIGHT)
        for i in range(0, int(w), 10):
            for j in range(0, int(h), 12):
                dx = (i * 13 + j * 7) % int(max(w - 8, 1))
                dy = (j * 11 + i * 3) % int(max(h - 8, 1))
                ctx.fillRect(x + 4 + dx, y + 4 + dy, 3, 2)

        # Wooden fence — posts at corners and midpoints
        self._draw_fence(ctx, x, y, w, h)

        # Label on a wooden sign
        self._draw_sign(ctx, entity.get("name", ""), x + 6, y + 4, w)

    def _draw_fence(self, ctx: Any, x: float, y: float, w: float, h: float):
        """Draw wooden fence around garden bed."""
        post_w = 4
        post_h = 10
        rail_h = 2

        # Corner and midpoint posts
        post_positions = [
            x,                    # left
            x + w - post_w,       # right
            x + w / 2 - post_w / 2,  # center
        ]

        for px in post_positions:
            # Post
            ctx.fillStyle(FENCE_POST)
            ctx.fillRect(px, y - post_h + 2, post_w, post_h + 4)
            # Post cap
            ctx.fillStyle(FENCE_RAIL)
            ctx.fillRect(px - 1, y - post_h, post_w + 2, 3)

        # Horizontal rails — top and bottom
        rail_y_top = y - 2
        rail_y_bot = y + 4

        ctx.fillStyle(FENCE_RAIL)
        ctx.fillRect(x, rail_y_top, w, rail_h)
        ctx.fillRect(x, rail_y_bot, w, rail_h)

        # Bottom fence
        fence_bot_y = y + h
        for px in post_positions:
            ctx.fillStyle(FENCE_POST)
            ctx.fillRect(px, fence_bot_y - 2, post_w, post_h)
            ctx.fillStyle(FENCE_RAIL)
            ctx.fillRect(px - 1, fence_bot_y + post_h - 4, post_w + 2, 3)

        ctx.fillStyle(FENCE_RAIL)
        ctx.fillRect(x, fence_bot_y, w, rail_h)
        ctx.fillRect(x, fence_bot_y + 5, w, rail_h)

    def _draw_sign(self, ctx: Any, text: str, x: float, y: float, max_w: float):
        """Draw a wooden sign with text."""
        # Sign board
        sign_w = min(len(text) * 7 + 12, max_w - 20)
        sign_h = 16
        ctx.fillStyle("#a0824a")
        ctx.fillRect(x, y, sign_w, sign_h)
        # Sign border
        ctx.strokeStyle("#6b5030")
        ctx.lineWidth(1)
        ctx.strokeRect(x, y, sign_w, sign_h)
        # Text
        ctx.fillStyle("#3f2010")
        ctx.font("bold 10px Georgia, serif")
        ctx.fillText(text[:int(sign_w / 7)], x + 6, y + 12)

    # ─── Planting Row ───────────────────────────────────────────────────

    def _draw_planting_row(self, entity: dict, pos: dict, ctx: Any):
        """Draw planting row — furrowed soil strip with detail."""
        x, y, w, h = pos["x"], pos["y"], pos["w"], pos["h"]

        # Row soil (slightly lighter than bed)
        ctx.fillStyle("#5c4033")
        ctx.fillRect(x, y, w, h)

        # Furrow lines (horizontal ridges)
        ctx.strokeStyle("#4a3328")
        ctx.lineWidth(1)
        for i in range(4, int(h), 6):
            ctx.moveTo(x + 3, y + i)
            ctx.lineTo(x + w - 3, y + i)
        ctx.stroke()

        # Soil crumbles
        ctx.fillStyle("#6b4c3b")
        for i in range(0, int(w), 8):
            cx = x + 4 + (i * 11) % int(max(w - 8, 1))
            cy = y + h - 5
            ctx.beginPath()
            ctx.arc(cx, cy, 2, 0, 2 * math.pi)
            ctx.fill()

        # Row label
        ctx.fillStyle("#d4c4a8")
        ctx.font("9px Georgia, serif")
        ctx.fillText(entity.get("name", ""), x + 4, y + 11)

    # ─── Plant ──────────────────────────────────────────────────────────

    def _draw_plant(self, entity: dict, pos: dict, ctx: Any, state: str):
        """Draw a plant — tree/flower/bush with actual shapes.

        Plant type is determined by entity name hash:
        - Trees: trunk + canopy (tall plants)
        - Flowers: stem + petals (medium plants)
        - Bushes: rounded shrub (short plants)
        """
        leaf_color = HEALTH_COLORS.get(state, HEALTH_COLORS["unknown"])
        cpu = (entity.get("metrics") or {}).get("cpu", 30)
        x, y, w, h = pos["x"], pos["y"], pos["w"], pos["h"]

        # Determine plant type by hash
        name_hash = hash(entity.get("id", "")) % 3
        plant_type = ["tree", "flower", "bush"][name_hash]

        stem_x = x + w / 2
        stem_bottom = y + h

        if plant_type == "tree":
            self._draw_tree(ctx, stem_x, stem_bottom, w, h, leaf_color, state, cpu)
        elif plant_type == "flower":
            self._draw_flower(ctx, stem_x, stem_bottom, w, h, leaf_color, state, entity)
        else:
            self._draw_bush(ctx, stem_x, stem_bottom, w, h, leaf_color, state, cpu)

        # Dew drops for idle state
        if state == "idle":
            self._draw_dew_drops(ctx, stem_x, y, h)

        # Label below plant
        ctx.fillStyle("#1a3a1a")
        ctx.font("8px Georgia, serif")
        label = entity.get("name", "")[:12]
        ctx.fillText(label, x, y + h + 10)

    def _draw_tree(self, ctx: Any, x: float, bottom: float, w: float, h: float,
                   leaf_color: str, state: str, cpu: float):
        """Draw tree with trunk + canopy."""
        trunk_w = max(3, w * 0.15)
        trunk_h = h * 0.45
        canopy_r = max(6, w * 0.4)

        # Trunk
        ctx.fillStyle("#5c3d2e")
        ctx.fillRect(x - trunk_w / 2, bottom - trunk_h, trunk_w, trunk_h)

        # Trunk texture (bark lines)
        ctx.strokeStyle("#4a2e1f")
        ctx.lineWidth(0.5)
        for i in range(3):
            ty = bottom - trunk_h + 4 + i * (trunk_h / 4)
            ctx.moveTo(x - trunk_w / 2 + 1, ty)
            ctx.lineTo(x + trunk_w / 2 - 1, ty + 2)
        ctx.stroke()

        # Canopy (layered circles for organic shape)
        canopy_y = bottom - trunk_h - canopy_r * 0.3
        # Back canopy (darker)
        darker_leaf = _lerp_color(leaf_color, "#000000", 0.2)
        ctx.fillStyle(darker_leaf)
        ctx.beginPath()
        ctx.arc(x - canopy_r * 0.3, canopy_y + 2, canopy_r * 0.7, 0, 2 * math.pi)
        ctx.fill()
        ctx.beginPath()
        ctx.arc(x + canopy_r * 0.3, canopy_y + 3, canopy_r * 0.65, 0, 2 * math.pi)
        ctx.fill()

        # Front canopy (main color)
        ctx.fillStyle(leaf_color)
        ctx.beginPath()
        ctx.arc(x, canopy_y - 2, canopy_r * 0.8, 0, 2 * math.pi)
        ctx.fill()

        # Highlight
        ctx.save()
        ctx.globalAlpha(0.3)
        ctx.fillStyle("#ffffff")
        ctx.beginPath()
        ctx.arc(x - canopy_r * 0.2, canopy_y - canopy_r * 0.3, canopy_r * 0.25, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # Flowers on tree for active states
        if state in ("healthy", "running", "scaling"):
            flower_c = FLOWER_COLORS[hash(str(x)) % len(FLOWER_COLORS)]
            for i in range(3):
                angle = (2 * math.pi / 3) * i + 0.5
                fx = x + math.cos(angle) * canopy_r * 0.5
                fy = canopy_y + math.sin(angle) * canopy_r * 0.4
                ctx.fillStyle(flower_c)
                ctx.beginPath()
                ctx.arc(fx, fy, 2.5, 0, 2 * math.pi)
                ctx.fill()

    def _draw_flower(self, ctx: Any, x: float, bottom: float, w: float, h: float,
                     leaf_color: str, state: str, entity: dict):
        """Draw flower with stem + petals."""
        stem_h = h * 0.7
        petal_r = max(4, w * 0.25)

        # Stem
        ctx.strokeStyle("#166534")
        ctx.lineWidth(2)
        ctx.moveTo(x, bottom)
        ctx.lineTo(x, bottom - stem_h)
        ctx.stroke()

        # Leaves on stem
        ctx.fillStyle(leaf_color)
        # Left leaf
        ctx.beginPath()
        ctx.arc(x - 5, bottom - stem_h * 0.4, 4, 0, 2 * math.pi)
        ctx.fill()
        # Right leaf
        ctx.beginPath()
        ctx.arc(x + 5, bottom - stem_h * 0.6, 3.5, 0, 2 * math.pi)
        ctx.fill()

        # Flower head — petals
        flower_top = bottom - stem_h
        if state in ("healthy", "running", "scaling"):
            # Blooming flower with petals
            flower_c = FLOWER_COLORS[hash(entity.get("id", "")) % len(FLOWER_COLORS)]
            n_petals = 6
            for i in range(n_petals):
                angle = (2 * math.pi / n_petals) * i
                px = x + math.cos(angle) * petal_r * 0.6
                py = flower_top + math.sin(angle) * petal_r * 0.6
                ctx.fillStyle(flower_c)
                ctx.beginPath()
                ctx.arc(px, py, petal_r * 0.45, 0, 2 * math.pi)
                ctx.fill()
            # Center
            ctx.fillStyle("#facc15")
            ctx.beginPath()
            ctx.arc(x, flower_top, petal_r * 0.3, 0, 2 * math.pi)
            ctx.fill()
        else:
            # Closed/wilting flower
            ctx.fillStyle(leaf_color)
            ctx.beginPath()
            ctx.arc(x, flower_top, petal_r * 0.4, 0, 2 * math.pi)
            ctx.fill()

    def _draw_bush(self, ctx: Any, x: float, bottom: float, w: float, h: float,
                   leaf_color: str, state: str, cpu: float):
        """Draw bush — rounded shrub shape."""
        bush_w = max(8, w * 0.7)
        bush_h = max(6, h * 0.5)
        bush_y = bottom - bush_h

        # Bush body — overlapping circles
        darker = _lerp_color(leaf_color, "#000000", 0.15)
        ctx.fillStyle(darker)
        ctx.beginPath()
        ctx.arc(x - bush_w * 0.25, bush_y + bush_h * 0.3, bush_w * 0.35, 0, 2 * math.pi)
        ctx.fill()
        ctx.beginPath()
        ctx.arc(x + bush_w * 0.25, bush_y + bush_h * 0.3, bush_w * 0.35, 0, 2 * math.pi)
        ctx.fill()

        # Main body
        ctx.fillStyle(leaf_color)
        ctx.beginPath()
        ctx.arc(x, bush_y + bush_h * 0.2, bush_w * 0.4, 0, 2 * math.pi)
        ctx.fill()

        # Top
        ctx.beginPath()
        ctx.arc(x, bush_y, bush_w * 0.3, 0, 2 * math.pi)
        ctx.fill()

        # Highlight
        ctx.save()
        ctx.globalAlpha(0.2)
        ctx.fillStyle("#ffffff")
        ctx.beginPath()
        ctx.arc(x - bush_w * 0.1, bush_y - bush_w * 0.1, bush_w * 0.15, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # Small flowers on bush for active states
        if state in ("healthy", "running"):
            flower_c = FLOWER_COLORS[hash(str(x + bottom)) % len(FLOWER_COLORS)]
            for i in range(2):
                fx = x + (i - 0.5) * bush_w * 0.4
                fy = bush_y + bush_h * 0.1
                ctx.fillStyle(flower_c)
                ctx.beginPath()
                ctx.arc(fx, fy, 2, 0, 2 * math.pi)
                ctx.fill()

    def _draw_dew_drops(self, ctx: Any, x: float, y: float, h: float):
        """Draw dew drops on idle plants."""
        ctx.save()
        drops = [(x - 4, y + h * 0.3, 2.5), (x + 5, y + h * 0.5, 2), (x - 2, y + h * 0.7, 1.8)]
        for dx, dy, dr in drops:
            # Drop body
            ctx.globalAlpha(0.6)
            ctx.fillStyle(DEW_COLOR)
            ctx.beginPath()
            ctx.arc(dx, dy, dr, 0, 2 * math.pi)
            ctx.fill()
            # Shine
            ctx.globalAlpha(0.8)
            ctx.fillStyle(DEW_SHINE)
            ctx.beginPath()
            ctx.arc(dx - dr * 0.3, dy - dr * 0.3, dr * 0.3, 0, 2 * math.pi)
            ctx.fill()
        ctx.restore()

    # ─── Branch ─────────────────────────────────────────────────────────

    def _draw_branch(self, entity: dict, pos: dict, ctx: Any):
        """Draw a branch — organic sub-element of a plant."""
        x, y, w, h = pos["x"], pos["y"], pos["w"], pos["h"]

        # Branch line
        ctx.strokeStyle("#15803d")
        ctx.lineWidth(2)
        ctx.moveTo(x, y + h)
        ctx.lineTo(x + w / 2, y)
        ctx.stroke()

        # Small leaves on branch
        ctx.fillStyle("#22c55e")
        ctx.beginPath()
        ctx.arc(x + w * 0.3, y + h * 0.3, 3, 0, 2 * math.pi)
        ctx.fill()
        ctx.beginPath()
        ctx.arc(x + w * 0.6, y + h * 0.6, 2.5, 0, 2 * math.pi)
        ctx.fill()

    # ─── Irrigation ─────────────────────────────────────────────────────

    def _draw_irrigation(self, entities: list[dict], layout: dict, ctx: Any):
        """Draw irrigation channels with animated water flow."""
        nodes = [e for e in entities if e.get("type") == "node"]
        if len(nodes) < 2:
            return

        for i in range(len(nodes) - 1):
            pos_a = layout.get(nodes[i]["id"])
            pos_b = layout.get(nodes[i + 1]["id"])
            if not pos_a or not pos_b:
                continue

            # Water channel between rows
            y = pos_a["y"] + pos_a["h"] + 2
            x_start = min(pos_a["x"], pos_b["x"]) + 10
            x_end = max(pos_a["x"] + pos_a["w"], pos_b["x"] + pos_b["w"]) - 10

            if x_end <= x_start:
                continue

            # Channel bed
            ctx.fillStyle("#2563eb")
            ctx.fillRect(x_start, y - 1, x_end - x_start, 3)

            # Animated water flow — moving highlights
            ctx.save()
            ctx.globalAlpha(0.6)
            flow_offset = (self._anim_time * 30) % 12
            ctx.fillStyle(WATER_LIGHT)
            for wx in range(int(x_start), int(x_end), 12):
                wx_anim = wx + flow_offset
                if wx_anim < x_end:
                    ctx.fillRect(wx_anim, y, 6, 1.5)
            ctx.restore()

            # Water sparkles
            ctx.save()
            ctx.globalAlpha(0.4)
            ctx.fillStyle("#ffffff")
            sparkle_offset = (self._anim_time * 20) % 18
            for wx in range(int(x_start), int(x_end), 18):
                sx = wx + sparkle_offset
                if sx < x_end:
                    ctx.beginPath()
                    ctx.arc(sx, y + 0.5, 1, 0, 2 * math.pi)
                    ctx.fill()
            ctx.restore()

    # ─── Weeds ──────────────────────────────────────────────────────────

    def _draw_weeds(self, entities: list[dict], layout: dict, ctx: Any):
        """Draw weeds for error/critical services."""
        for entity in entities:
            if entity.get("type") != "service":
                continue
            state = entity.get("state", "")
            if state not in ("critical", "degraded"):
                continue
            pos = layout.get(entity["id"])
            if not pos:
                continue

            # Weeds: jagged spiky lines next to the plant
            ctx.strokeStyle(WEED_COLOR)
            ctx.lineWidth(1.5)
            wx = pos["x"] + pos["w"] + 4
            wy = pos["y"] + pos["h"]

            # Multiple weed stalks
            for j in range(3):
                ox = j * 3
                ctx.moveTo(wx + ox, wy)
                ctx.lineTo(wx + ox + 2, wy - 8 - j * 3)
                ctx.lineTo(wx + ox - 1, wy - 12 - j * 2)
                ctx.lineTo(wx + ox + 3, wy - 18 - j * 2)
            ctx.stroke()

            # Weed leaves
            ctx.fillStyle("#6b7280")
            ctx.beginPath()
            ctx.arc(wx + 2, wy - 14, 2.5, 0, 2 * math.pi)
            ctx.fill()

    # ─── Butterflies / Bees ─────────────────────────────────────────────

    def _draw_butterflies(self, entities: list[dict], layout: dict, ctx: Any):
        """Draw butterflies and bees for active containers."""
        containers = [e for e in entities if e.get("type") == "container"
                      and e.get("state") in ("running", "healthy", "active")]
        for i, container in enumerate(containers):
            parent_id = container.get("parent")
            parent_pos = layout.get(str(parent_id)) if parent_id else None
            if not parent_pos:
                continue

            # Alternate between butterfly and bee
            if i % 2 == 0:
                self._draw_butterfly(ctx, parent_pos, i)
            else:
                self._draw_bee(ctx, parent_pos, i)

    def _draw_butterfly(self, ctx: Any, parent_pos: dict, idx: int):
        """Draw a butterfly with animated wings."""
        bfly_color = BUTTERFLY_COLORS[idx % len(BUTTERFLY_COLORS)]
        # Flutter animation
        flutter = math.sin(self._anim_time * 4 + idx * 2) * 3
        bx = parent_pos["x"] + parent_pos["w"] + 10 + (idx % 3) * 6
        by = parent_pos["y"] - 8 - (idx % 2) * 10 + flutter

        # Left wing
        ctx.fillStyle(bfly_color)
        ctx.beginPath()
        ctx.moveTo(bx, by)
        ctx.arc(bx - 3, by - 1, 4, 0, 2 * math.pi)
        ctx.fill()
        # Right wing
        ctx.beginPath()
        ctx.moveTo(bx, by)
        ctx.arc(bx + 3, by - 1, 4, 0, 2 * math.pi)
        ctx.fill()
        # Body
        ctx.fillStyle("#1a1a1a")
        ctx.fillRect(bx - 0.5, by - 2, 1, 5)
        # Antennae
        ctx.strokeStyle("#1a1a1a")
        ctx.lineWidth(0.5)
        ctx.moveTo(bx, by - 2)
        ctx.lineTo(bx - 2, by - 5)
        ctx.moveTo(bx, by - 2)
        ctx.lineTo(bx + 2, by - 5)
        ctx.stroke()

    def _draw_bee(self, ctx: Any, parent_pos: dict, idx: int):
        """Draw a bee with stripes and wings."""
        buzz = math.sin(self._anim_time * 8 + idx * 3) * 2
        bx = parent_pos["x"] + parent_pos["w"] + 12 + (idx % 3) * 5
        by = parent_pos["y"] - 5 - (idx % 2) * 8 + buzz

        # Body
        ctx.fillStyle(BEE_BODY)
        ctx.beginPath()
        ctx.arc(bx, by, 3, 0, 2 * math.pi)
        ctx.fill()

        # Stripes
        ctx.fillStyle(BEE_STRIPE)
        ctx.fillRect(bx - 2, by - 1, 4, 1)
        ctx.fillRect(bx - 2, by + 1, 4, 1)

        # Wings (translucent)
        ctx.save()
        ctx.globalAlpha(0.4)
        ctx.fillStyle("#e0f2fe")
        # Left wing
        ctx.beginPath()
        ctx.arc(bx - 2, by - 3, 2.5, 0, 2 * math.pi)
        ctx.fill()
        # Right wing
        ctx.beginPath()
        ctx.arc(bx + 2, by - 3, 2.5, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

    # ─── Fireflies ──────────────────────────────────────────────────────

    def _draw_fireflies(self, entities: list[dict], layout: dict, ctx: Any, w: int, h: int):
        """Draw glowing fireflies at night."""
        ctx.save()
        import hashlib
        n_fireflies = 15
        for i in range(n_fireflies):
            seed = int(hashlib.md5(f"firefly{i}".encode()).hexdigest()[:8], 16)
            fx = seed % int(max(w, 1))
            fy = h * 0.25 + (seed >> 8) % int(max(h * 0.6, 1))

            # Pulsing glow
            pulse = 0.3 + 0.7 * max(0, math.sin(self._anim_time * 1.5 + i * 1.3))
            if pulse < 0.4:
                continue  # some fireflies are "off"

            # Glow halo
            ctx.globalAlpha(pulse * 0.3)
            ctx.fillStyle(FIREFLY_COLOR)
            ctx.beginPath()
            ctx.arc(fx, fy, 6, 0, 2 * math.pi)
            ctx.fill()

            # Core
            ctx.globalAlpha(pulse * 0.8)
            ctx.beginPath()
            ctx.arc(fx, fy, 1.5, 0, 2 * math.pi)
            ctx.fill()

        ctx.restore()

    # ─── Tooltip / Hit Test / Config ────────────────────────────────────

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Generate tooltip text for an entity."""
        etype = entity.get("type", "?")
        type_names = {
            "cluster": "Garden Bed",
            "node": "Planting Row",
            "service": "Plant",
            "container": "Branch",
        }
        lines = [
            f"{entity.get('name', '?')} ({type_names.get(etype, etype)})",
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
        return "\n".join(lines)

    def hit_test(self, entity: dict[str, Any], x: int, y: int) -> bool:
        """Check if (x,y) falls within this entity's layout bounds."""
        pos = self._layout.get(entity.get("id"))
        if not pos:
            return False
        return (pos["x"] <= x <= pos["x"] + pos["w"] and
                pos["y"] <= y <= pos["y"] + pos["h"])

    def config(self) -> dict[str, Any]:
        """Return metaphor configuration metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "state_colors": HEALTH_COLORS,
            "sun_colors": SUN_COLORS,
            "mappings": {
                "cluster": "garden bed",
                "node": "planting row",
                "service": "plant",
                "container": "branch",
            },
            "visual_elements": {
                "sky": "day/night gradient with sun arc",
                "sun": "cluster health, time-based position",
                "soil": "rich brown texture with pebbles",
                "fence": "wooden border around beds",
                "pathways": "dirt paths between beds",
                "trees": "trunk + canopy, CPU-scaled height",
                "flowers": "stem + petals, bloom for active",
                "bushes": "rounded shrub shape",
                "leaf_color": "green=healthy, yellow=warning, brown=critical",
                "flowers_bloom": "active services",
                "dew_drops": "idle plants",
                "butterflies": "active containers",
                "bees": "active containers",
                "irrigation": "animated water flow",
                "weeds": "error/critical processes",
                "fireflies": "night ambient glow",
                "stars": "night sky",
            },
        }
