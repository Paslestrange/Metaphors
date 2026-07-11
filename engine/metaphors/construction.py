"""Construction Site metaphor renderer — Cluster→Building Project, Node→Floor, Service→Room, Container→Wall Section.

Blueprint aesthetic: blue background, white/cyan lines, technical drawing style.
Visual elements: cranes, scaffolding, workers, delivery trucks, safety signs, demolition.
"""
from __future__ import annotations
from typing import Any
from engine.metaphors.base import MetaphorRenderer


# Blueprint color palette
BLUEPRINT_BG = "#1e3a5f"          # Deep blueprint blue
BLUEPRINT_LINE = "#a8d8ea"        # Light cyan lines
BLUEPRINT_GRID = "#2d5a80"        # Grid lines
BLUEPRINT_ACCENT = "#ffffff"      # White accent lines
BLUEPRINT_TEXT = "#e0f0ff"        # Light blue text

# State → color map (safety/construction themed)
STATE_COLORS = {
    "healthy": "#4ade80",         # Green — all clear
    "running": "#60a5fa",         # Blue — active work
    "idle": "#94a3b8",            # Gray — no activity
    "warning": "#fbbf24",         # Yellow — safety caution
    "degraded": "#f97316",        # Orange — structural concern
    "critical": "#ef4444",        # Red — collapse risk
    "stopped": "#374151",         # Dark — abandoned
    "pending": "#a78bfa",         # Purple — planned
    "scaling": "#06b6d4",         # Cyan — expanding
    "unknown": "#6b7280",         # Gray
}


class ConstructionRenderer(MetaphorRenderer):
    """Construction Site metaphor: clusters are building projects, nodes are floors,
    services are rooms, containers are wall sections.

    Blueprint aesthetic with vertical building layout.
    Floors stack upward. Room completion scales with CPU usage.
    """

    name = "construction"
    description = "Infrastructure as a construction site with blueprint visualization"

    def __init__(self):
        self._layout: dict[str, dict[str, float]] = {}

    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, float]]:
        """Compute positions for all entities. Vertical building layout.
        
        Clusters (projects) side by side, nodes (floors) stack bottom-up,
        services (rooms) fill each floor, containers (walls) subdivide rooms.
        """
        layout: dict[str, dict[str, float]] = {}
        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        # Each project gets a vertical column
        project_w = w / max(len(roots), 1)
        for pi, root in enumerate(roots):
            px = pi * project_w
            layout[root["id"]] = {"x": px, "y": 0, "w": project_w, "h": h}

            children = [by_id[cid] for cid in (root.get("children") or []) if cid in by_id]
            if not children:
                continue

            # Floors stack bottom-up (first floor at bottom)
            floor_h = (h - 60) / max(len(children), 1)  # Reserve 60px for ground/crane area
            for fi, child in enumerate(children):
                # Floor from bottom: fi=0 is ground floor (highest y)
                fy = h - 60 - (fi + 1) * floor_h
                layout[child["id"]] = {
                    "x": px + 10, "y": fy,
                    "w": project_w - 20, "h": floor_h - 4,
                }

                # Rooms (services) fill each floor horizontally
                grandchildren = [by_id[gcid] for gcid in (child.get("children") or []) if gcid in by_id]
                if not grandchildren:
                    continue
                room_w = (project_w - 40) / max(len(grandchildren), 1)
                for ri, gc in enumerate(grandchildren):
                    rx = px + 20 + ri * room_w
                    cpu = (gc.get("metrics") or {}).get("cpu", 50)
                    # Room completion scales with CPU — under construction rooms are shorter
                    max_room_h = floor_h - 20
                    room_h = max(15, max_room_h * (cpu / 100))
                    layout[gc["id"]] = {
                        "x": rx, "y": fy + (floor_h - 4 - room_h),
                        "w": room_w - 8, "h": room_h,
                    }

                    # Wall sections (containers) subdivide rooms
                    great_grandchildren = [by_id[ggcid] for ggcid in (gc.get("children") or []) if ggcid in by_id]
                    if not great_grandchildren:
                        continue
                    wall_w = (room_w - 16) / max(len(great_grandchildren), 1)
                    for wi, ggc in enumerate(great_grandchildren):
                        wx = rx + 4 + wi * wall_w
                        layout[ggc["id"]] = {
                            "x": wx, "y": fy + (floor_h - 4 - room_h) + 4,
                            "w": wall_w - 4, "h": room_h - 8,
                        }

        self._layout = layout
        return layout

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the construction site metaphor with blueprint aesthetic."""
        layout = self.compute_layout(entities, w, h)

        # Blueprint background
        ctx.fillStyle(BLUEPRINT_BG)
        ctx.fillRect(0, 0, w, h)

        # Blueprint grid lines
        ctx.strokeStyle(BLUEPRINT_GRID)
        ctx.lineWidth(0.5)
        grid_spacing = 20
        gx = 0
        while gx < w:
            ctx.beginPath()
            ctx.moveTo(gx, 0)
            ctx.lineTo(gx, h)
            ctx.stroke()
            gx += grid_spacing
        gy = 0
        while gy < h:
            ctx.beginPath()
            ctx.moveTo(0, gy)
            ctx.lineTo(w, gy)
            ctx.stroke()
            gy += grid_spacing

        # Ground level
        ctx.fillStyle("#2d1f0e")
        ctx.fillRect(0, h - 30, w, 30)
        ctx.strokeStyle("#8b6914")
        ctx.lineWidth(2)
        ctx.beginPath()
        ctx.moveTo(0, h - 30)
        ctx.lineTo(w, h - 30)
        ctx.stroke()

        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            color = STATE_COLORS.get(entity.get("state", "unknown"), STATE_COLORS["unknown"])
            etype = entity.get("type", "")

            if etype == "cluster":
                # Building project outline — blueprint style
                ctx.strokeStyle(BLUEPRINT_ACCENT)
                ctx.lineWidth(2)
                ctx.strokeRect(pos["x"] + 2, pos["y"] + 2, pos["w"] - 4, pos["h"] - 4)

                # Project label (blueprint title block style)
                ctx.fillStyle(BLUEPRINT_TEXT)
                ctx.font("bold 14px monospace")
                ctx.fillText(entity.get("name", ""), pos["x"] + 8, pos["y"] + 20)

                # Crane at top of project
                self._draw_crane(ctx, pos["x"] + pos["w"] - 30, pos["y"] + 10, color)

            elif etype == "node":
                # Floor — horizontal slab with scaffolding
                ctx.strokeStyle(BLUEPRINT_LINE)
                ctx.lineWidth(1.5)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

                # Floor slab fill (concrete gray)
                ctx.fillStyle("#3a3a3a")
                ctx.fillRect(pos["x"] + 1, pos["y"] + pos["h"] - 4, pos["w"] - 2, 3)

                # Floor label
                ctx.fillStyle(BLUEPRINT_TEXT)
                ctx.font("11px monospace")
                ctx.fillText(entity.get("name", ""), pos["x"] + 6, pos["y"] + 14)

                # Scaffolding on sides
                self._draw_scaffolding(ctx, pos["x"], pos["y"], pos["w"], pos["h"])

                # Warning sign for warning state
                if entity.get("state") == "warning":
                    self._draw_safety_sign(ctx, pos["x"] + pos["w"] - 20, pos["y"] + 4, "#fbbf24")
                elif entity.get("state") == "critical":
                    self._draw_safety_sign(ctx, pos["x"] + pos["w"] - 20, pos["y"] + 4, "#ef4444")

            elif etype == "service":
                # Room — filled based on completion (CPU)
                ctx.fillStyle(color)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle(BLUEPRINT_LINE)
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

                # Progress indicator — floor being built
                if pos["h"] > 20 and pos["w"] > 20:
                    # Brick pattern for completed portion
                    brick_y = pos["y"] + pos["h"] - 8
                    while brick_y < pos["y"] + pos["h"] - 2:
                        brick_x = pos["x"] + 2
                        while brick_x < pos["x"] + pos["w"] - 4:
                            ctx.strokeStyle("#ffffff30")
                            ctx.lineWidth(0.5)
                            ctx.strokeRect(brick_x, brick_y, 8, 4)
                            brick_x += 10
                        brick_y += 5

                # Room label
                if pos["w"] > 25:
                    ctx.fillStyle(BLUEPRINT_ACCENT)
                    ctx.font("9px monospace")
                    ctx.fillText(entity.get("name", "")[:10], pos["x"] + 2, pos["y"] + pos["h"] + 10)

                # Delivery truck for incoming requests (high CPU = busy delivery)
                cpu = (entity.get("metrics") or {}).get("cpu", 0)
                if cpu > 70:
                    self._draw_delivery_truck(ctx, pos["x"] + pos["w"] - 12, pos["y"] - 8)

            elif etype == "container":
                # Wall section
                ctx.fillStyle(color + "80")  # Semi-transparent
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle(BLUEPRINT_LINE)
                ctx.lineWidth(0.5)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

                # Brick pattern
                if pos["h"] > 10 and pos["w"] > 10:
                    ctx.strokeStyle("#ffffff20")
                    ctx.lineWidth(0.3)
                    by = pos["y"] + 2
                    while by < pos["y"] + pos["h"] - 2:
                        bx = pos["x"] + 2
                        while bx < pos["x"] + pos["w"] - 2:
                            ctx.strokeRect(bx, by, 6, 3)
                            bx += 7
                        by += 4

        # Demolition/rubble for stopped/critical entities
        for entity in entities:
            if entity.get("state") in ("stopped", "critical"):
                pos = layout.get(entity["id"])
                if pos and entity.get("type") == "service":
                    self._draw_rubble(ctx, pos["x"], pos["y"] + pos["h"], pos["w"])

    def _draw_crane(self, ctx: Any, x: float, y: float, color: str) -> None:
        """Draw a construction crane."""
        ctx.strokeStyle(color)
        ctx.lineWidth(2)
        # Vertical mast
        ctx.beginPath()
        ctx.moveTo(x, y)
        ctx.lineTo(x, y + 40)
        ctx.stroke()
        # Horizontal jib
        ctx.beginPath()
        ctx.moveTo(x - 15, y)
        ctx.lineTo(x + 25, y)
        ctx.stroke()
        # Cable
        ctx.lineWidth(0.5)
        ctx.beginPath()
        ctx.moveTo(x + 20, y)
        ctx.lineTo(x + 20, y + 15)
        ctx.stroke()
        # Hook
        ctx.beginPath()
        ctx.arc(x + 20, y + 17, 2, 0, 3.14)
        ctx.stroke()

    def _draw_scaffolding(self, ctx: Any, x: float, y: float, w: float, h: float) -> None:
        """Draw scaffolding on floor edges."""
        ctx.strokeStyle("#8b8b8b")
        ctx.lineWidth(0.5)
        # Left scaffolding
        sx = x - 3
        sy = y + 5
        while sy < y + h - 5:
            ctx.beginPath()
            ctx.moveTo(sx, sy)
            ctx.lineTo(sx + 3, sy)
            ctx.stroke()
            sy += 8
        # Right scaffolding
        sx = x + w
        sy = y + 5
        while sy < y + h - 5:
            ctx.beginPath()
            ctx.moveTo(sx, sy)
            ctx.lineTo(sx + 3, sy)
            ctx.stroke()
            sy += 8

    def _draw_safety_sign(self, ctx: Any, x: float, y: float, color: str) -> None:
        """Draw a safety violation/caution sign."""
        # Triangle warning sign
        ctx.fillStyle(color)
        ctx.beginPath()
        ctx.moveTo(x, y + 12)
        ctx.lineTo(x + 6, y)
        ctx.lineTo(x + 12, y + 12)
        ctx.closePath()
        ctx.fill()
        # Exclamation mark
        ctx.fillStyle("#000")
        ctx.font("bold 8px monospace")
        ctx.fillText("!", x + 4, y + 10)

    def _draw_delivery_truck(self, ctx: Any, x: float, y: float) -> None:
        """Draw a material delivery truck (indicates high request volume)."""
        ctx.fillStyle("#f59e0b")
        ctx.fillRect(x, y, 10, 6)  # Truck body
        ctx.fillStyle("#78716c")
        ctx.fillRect(x + 10, y + 1, 4, 5)  # Cab
        # Wheels
        ctx.fillStyle("#1f2937")
        ctx.beginPath()
        ctx.arc(x + 3, y + 7, 1.5, 0, 6.28)
        ctx.fill()
        ctx.beginPath()
        ctx.arc(x + 11, y + 7, 1.5, 0, 6.28)
        ctx.fill()

    def _draw_rubble(self, ctx: Any, x: float, y: float, w: float) -> None:
        """Draw rubble/demolition debris."""
        ctx.fillStyle("#6b728080")
        # Scattered debris blocks
        dx = x + 2
        while dx < x + w - 4:
            ctx.fillRect(dx, y + 1, 4, 3)
            ctx.fillRect(dx + 5, y + 3, 3, 2)
            dx += 8

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Generate tooltip text for an entity with construction theme."""
        type_labels = {
            "cluster": "Building Project",
            "node": "Floor",
            "service": "Room",
            "container": "Wall Section",
        }
        type_label = type_labels.get(entity.get("type", ""), entity.get("type", "?"))
        lines = [
            f"{entity.get('name', '?')} ({type_label})",
            f"Status: {entity.get('state', 'unknown')}",
        ]
        m = entity.get("metrics") or {}
        if "cpu" in m:
            lines.append(f"Completion: {m['cpu']}%")
        if "mem" in m:
            lines.append(f"Materials: {m['mem']}%")
        if "cpu_pct" in m:
            lines.append(f"Completion: {m['cpu_pct']}%")
        if "mem_pct" in m:
            lines.append(f"Materials: {m['mem_pct']}%")
        if "req_per_sec" in m:
            lines.append(f"Deliveries: {m['req_per_sec']}/s")
        if "error_rate" in m:
            lines.append(f"Rework rate: {m['error_rate'] * 100:.1f}%")
        if "count" in m:
            lines.append(f"Workers: {m['count']}")
        if "uptime_hrs" in m:
            lines.append(f"Active: {m['uptime_hrs']}h")
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
            "state_colors": STATE_COLORS,
            "mappings": {
                "cluster": "building project",
                "node": "floor",
                "service": "room",
                "container": "wall section",
            },
        }
