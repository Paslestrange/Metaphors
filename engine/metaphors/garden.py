"""Garden metaphor renderer — Cluster→Garden Bed, Node→Planting Row,
Service→Plant/Tree, Container→Branch.

Watercolor aesthetic: soft edges, natural colors. Plants grow/shrink with CPU.
Leaves change color with health. Flowers bloom for active services.
Irrigation for request flow. Weeds for errors. Butterflies for containers.
Dew drops for idle. Sun for cluster health.
"""
from __future__ import annotations
import math
from typing import Any
from engine.metaphors.base import MetaphorRenderer


# Health → leaf color (watercolor natural tones)
HEALTH_COLORS = {
    "healthy": "#4ade80",   # lush green
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

# Sun color by cluster health
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

# Watercolor background
BG_COLOR = "#f0fdf4"       # soft mint
SOIL_COLOR = "#7c6f54"     # earthy brown
ROW_COLOR = "#a3898a"      # muted row soil
SKY_TOP = "#e0f2fe"        # pale sky blue
SKY_BOTTOM = "#f0fdf4"     # mint horizon

# Flower colors for active services
FLOWER_COLORS = ["#f472b6", "#fb923c", "#a78bfa", "#f87171", "#38bdf8", "#facc15"]

# Butterfly colors
BUTTERFLY_COLORS = ["#c084fc", "#fb7185", "#38bdf8", "#fbbf24"]

# Dew drop color
DEW_COLOR = "#bae6fd"

# Weed color (error processes)
WEED_COLOR = "#4b5563"

# Irrigation water color
WATER_COLOR = "#7dd3fc"


class GardenRenderer(MetaphorRenderer):
    """Garden metaphor: infrastructure as a living garden.

    Cluster = Garden Bed (bordered plot with soil)
    Node = Planting Row (furrowed strip)
    Service = Plant/Tree (grows with CPU, leaves colored by health)
    Container = Branch (sub-element of a plant)

    Visual elements:
    - Sun in sky reflects overall cluster health
    - Flowers bloom on active/healthy services
    - Dew drops appear on idle plants
    - Butterflies flutter around active containers
    - Weeds sprout for error processes
    - Irrigation channels show request flow between rows
    """

    name = "garden"
    description = "Infrastructure as a living garden with organic growth"

    def __init__(self):
        self._layout: dict[str, dict[str, float]] = {}

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

        # Reserve top 15% for sky/sun
        sky_h = h * 0.15
        garden_h = h - sky_h

        # Garden beds (clusters) spread horizontally with organic gaps
        n_roots = max(len(roots), 1)
        gap = 12  # organic gap between beds
        total_gap = gap * (n_roots + 1)
        bed_w = (w - total_gap) / n_roots

        for di, root in enumerate(roots):
            bx = gap + di * (bed_w + gap)
            by = sky_h
            layout[root["id"]] = {"x": bx, "y": by, "w": bed_w, "h": garden_h}

            # Planting rows (nodes) stack vertically inside bed
            children = [by_id[cid] for cid in (root.get("children") or []) if cid in by_id]
            n_children = max(len(children), 1)
            row_gap = 8
            row_h = (garden_h - row_gap * (n_children + 1)) / n_children

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
                plant_gap = 6
                plant_w = (rw - plant_gap * (n_gc + 1)) / n_gc

                for gi, gc in enumerate(grandchildren):
                    cpu = (gc.get("metrics") or {}).get("cpu", 30)
                    # Plant height grows with CPU (min 15, max 90% of row)
                    max_ph = row_h - 16
                    ph = max(15, max_ph * (cpu / 100))
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
        """Render the garden metaphor with watercolor aesthetic."""
        layout = self.compute_layout(entities, w, h)

        # Sky gradient (simplified as two rects)
        ctx.fillStyle(SKY_TOP)
        ctx.fillRect(0, 0, w, h * 0.15)
        ctx.fillStyle(SKY_BOTTOM)
        ctx.fillRect(0, h * 0.15, w, h * 0.85)

        # Ground / soil base
        ctx.fillStyle(SOIL_COLOR)
        ctx.fillRect(0, h * 0.85, w, h * 0.15)

        # Sun — reflects overall cluster health
        self._draw_sun(entities, ctx, w, h)

        # Render each entity by type
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            etype = entity.get("type", "")
            state = entity.get("state", "unknown")

            if etype == "cluster":
                self._draw_garden_bed(entity, pos, ctx)
            elif etype == "node":
                self._draw_planting_row(entity, pos, ctx)
            elif etype == "service":
                self._draw_plant(entity, pos, ctx, state)
            elif etype == "container":
                self._draw_branch(entity, pos, ctx)

        # Draw irrigation channels between rows
        self._draw_irrigation(entities, layout, ctx)

        # Draw weeds for error/critical services
        self._draw_weeds(entities, layout, ctx)

        # Draw butterflies for active containers
        self._draw_butterflies(entities, layout, ctx)

    def _draw_sun(self, entities: list[dict], ctx: Any, w: int, h: int):
        """Draw sun representing cluster health."""
        # Determine overall health from root clusters
        roots = [e for e in entities if not e.get("parent") and e.get("type") == "cluster"]
        if not roots:
            return

        # Average health → sun color
        health_priority = {"healthy": 0, "running": 0, "idle": 1, "warning": 2,
                          "degraded": 3, "critical": 4, "stopped": 5, "unknown": 3}
        worst = max(roots, key=lambda r: health_priority.get(r.get("state", "unknown"), 3))
        sun_color = SUN_COLORS.get(worst.get("state", "unknown"), SUN_COLORS["unknown"])

        # Sun position: top-right corner
        sun_x = w - 50
        sun_y = 40
        sun_r = 25

        # Glow
        ctx.save()
        ctx.globalAlpha(0.3)
        ctx.fillStyle(sun_color)
        ctx.beginPath()
        ctx.arc(sun_x, sun_y, sun_r + 10, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # Sun body
        ctx.fillStyle(sun_color)
        ctx.beginPath()
        ctx.arc(sun_x, sun_y, sun_r, 0, 2 * math.pi)
        ctx.fill()

    def _draw_garden_bed(self, entity: dict, pos: dict, ctx: Any):
        """Draw garden bed — soft-bordered plot with soil fill."""
        # Soil fill
        ctx.fillStyle("#8B7355")
        ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])

        # Soft border (watercolor edge)
        ctx.strokeStyle("#6b5b45")
        ctx.lineWidth(2)
        ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

        # Label
        ctx.fillStyle("#3f3024")
        ctx.font("bold 13px system-ui, sans-serif")
        ctx.fillText(entity.get("name", ""), pos["x"] + 6, pos["y"] + 16)

    def _draw_planting_row(self, entity: dict, pos: dict, ctx: Any):
        """Draw planting row — furrowed soil strip."""
        ctx.fillStyle(ROW_COLOR)
        ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])

        # Furrow lines
        ctx.strokeStyle("#8a7070")
        ctx.lineWidth(1)
        fy = pos["y"] + pos["h"] - 4
        ctx.moveTo(pos["x"] + 4, fy)
        ctx.lineTo(pos["x"] + pos["w"] - 4, fy)
        ctx.stroke()

        # Row label
        ctx.fillStyle("#5c4a4a")
        ctx.font("10px system-ui, sans-serif")
        ctx.fillText(entity.get("name", ""), pos["x"] + 4, pos["y"] + 12)

    def _draw_plant(self, entity: dict, pos: dict, ctx: Any, state: str):
        """Draw a plant — stem grows with CPU, leaves colored by health."""
        leaf_color = HEALTH_COLORS.get(state, HEALTH_COLORS["unknown"])
        cpu = (entity.get("metrics") or {}).get("cpu", 30)

        # Stem
        stem_x = pos["x"] + pos["w"] / 2
        stem_bottom = pos["y"] + pos["h"]
        ctx.strokeStyle("#166534")  # dark green stem
        ctx.lineWidth(2)
        ctx.moveTo(stem_x, stem_bottom)
        ctx.lineTo(stem_x, pos["y"] + 4)
        ctx.stroke()

        # Leaves — size and color based on health and CPU
        leaf_size = max(4, pos["w"] * 0.35)
        # Left leaf
        ctx.fillStyle(leaf_color)
        ctx.beginPath()
        ctx.arc(stem_x - leaf_size * 0.6, pos["y"] + pos["h"] * 0.4, leaf_size * 0.5, 0, 2 * math.pi)
        ctx.fill()
        # Right leaf
        ctx.beginPath()
        ctx.arc(stem_x + leaf_size * 0.6, pos["y"] + pos["h"] * 0.5, leaf_size * 0.45, 0, 2 * math.pi)
        ctx.fill()

        # Flower bloom for active/healthy services
        if state in ("healthy", "running", "scaling"):
            flower_color = FLOWER_COLORS[hash(entity.get("id", "")) % len(FLOWER_COLORS)]
            ctx.fillStyle(flower_color)
            ctx.beginPath()
            ctx.arc(stem_x, pos["y"] + 2, leaf_size * 0.35, 0, 2 * math.pi)
            ctx.fill()

        # Dew drops for idle state
        if state == "idle":
            ctx.fillStyle(DEW_COLOR)
            ctx.globalAlpha(0.7)
            ctx.beginPath()
            ctx.arc(stem_x - 3, pos["y"] + pos["h"] * 0.3, 2, 0, 2 * math.pi)
            ctx.fill()
            ctx.beginPath()
            ctx.arc(stem_x + 4, pos["y"] + pos["h"] * 0.6, 1.5, 0, 2 * math.pi)
            ctx.fill()
            ctx.globalAlpha(1.0)

        # Label below plant
        ctx.fillStyle("#1a3a1a")
        ctx.font("9px system-ui, sans-serif")
        label = entity.get("name", "")[:14]
        ctx.fillText(label, pos["x"], pos["y"] + pos["h"] + 11)

    def _draw_branch(self, entity: dict, pos: dict, ctx: Any):
        """Draw a branch — sub-element of a plant."""
        ctx.fillStyle("#15803d")
        ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
        ctx.strokeStyle("#14532d")
        ctx.lineWidth(1)
        ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

    def _draw_irrigation(self, entities: list[dict], layout: dict, ctx: Any):
        """Draw irrigation channels — water flow for request flow."""
        nodes = [e for e in entities if e.get("type") == "node"]
        if len(nodes) < 2:
            return

        ctx.strokeStyle(WATER_COLOR)
        ctx.lineWidth(1.5)
        ctx.globalAlpha(0.5)

        for i in range(len(nodes) - 1):
            pos_a = layout.get(nodes[i]["id"])
            pos_b = layout.get(nodes[i + 1]["id"])
            if not pos_a or not pos_b:
                continue
            # Water channel between rows
            y = pos_a["y"] + pos_a["h"] + 2
            x_start = pos_a["x"] + pos_a["w"] * 0.3
            x_end = pos_b["x"] + pos_b["w"] * 0.3
            ctx.moveTo(x_start, y)
            ctx.lineTo(x_end, y)
            ctx.stroke()

        ctx.globalAlpha(1.0)

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

            # Weeds: jagged lines next to the plant
            ctx.strokeStyle(WEED_COLOR)
            ctx.lineWidth(1)
            wx = pos["x"] + pos["w"] + 3
            wy = pos["y"] + pos["h"]
            ctx.moveTo(wx, wy)
            ctx.lineTo(wx + 2, wy - 8)
            ctx.lineTo(wx - 1, wy - 12)
            ctx.lineTo(wx + 3, wy - 16)
            ctx.stroke()

    def _draw_butterflies(self, entities: list[dict], layout: dict, ctx: Any):
        """Draw butterflies for active containers."""
        containers = [e for e in entities if e.get("type") == "container"
                      and e.get("state") in ("running", "healthy", "active")]
        for i, container in enumerate(containers):
            # Find parent service position for butterfly placement
            parent_id = container.get("parent")
            parent_pos = layout.get(str(parent_id)) if parent_id else None
            if not parent_pos:
                continue

            bfly_color = BUTTERFLY_COLORS[i % len(BUTTERFLY_COLORS)]
            bx = parent_pos["x"] + parent_pos["w"] + 8 + (i % 3) * 5
            by = parent_pos["y"] - 5 - (i % 2) * 8

            # Simple butterfly: two small triangles
            ctx.fillStyle(bfly_color)
            ctx.beginPath()
            ctx.moveTo(bx, by)
            ctx.lineTo(bx - 4, by - 3)
            ctx.lineTo(bx - 3, by + 2)
            ctx.closePath()
            ctx.fill()
            ctx.beginPath()
            ctx.moveTo(bx, by)
            ctx.lineTo(bx + 4, by - 3)
            ctx.lineTo(bx + 3, by + 2)
            ctx.closePath()
            ctx.fill()

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Generate tooltip text for an entity."""
        etype = entity.get("type", "?")
        # Map to garden terms
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
                "sun": "overall cluster health",
                "flowers": "active services",
                "dew_drops": "idle state",
                "butterflies": "active containers",
                "weeds": "error processes",
                "irrigation": "request flow",
            },
        }
