"""Kitchen metaphor renderer — Cluster=Restaurant, Node=Station, Service=Chef, Container=Pot/Pan.

Warm kitchen aesthetic: reds, oranges, yellows, steam effects.
Order tickets scrolling (request queue), chefs cooking at stations,
plates moving to serving window, steam rising from active pots,
pantry shelves for memory, kitchen fire for critical,
health inspector clipboard for warnings, empty station = stopped.
"""
from __future__ import annotations
from typing import Any
from engine.metaphors.base import MetaphorRenderer


# Warm kitchen color palette
STATE_COLORS = {
    "healthy": "#e8a838",      # golden sizzle
    "running": "#d4763a",      # searing orange
    "idle": "#8b7355",         # worn wood
    "warning": "#f5c542",      # health inspector yellow
    "degraded": "#c45a3c",     # burnt sienna
    "critical": "#cc2936",     # kitchen fire red
    "stopped": "#3d2b1f",      # dark espresso (empty station)
    "pending": "#b8860b",      # raw dough
    "scaling": "#e07020",      # flame
    "unknown": "#6b5b4f",      # cast iron
}

# Warm background tones
BG_COLOR = "#1a0f0a"           # dark wood floor
FLOOR_COLOR = "#2d1f14"        # warm tile
STATION_BG = "#261a10"         # station counter
SERVING_WINDOW = "#3a2a1a"     # warm pass


class KitchenRenderer(MetaphorRenderer):
    """Kitchen metaphor: clusters are restaurants, nodes are stations,
    services are chefs, containers are pots/pans.

    Chef height scales with CPU (cooking intensity).
    Steam rises from active pots. Fire for critical. Warm aesthetic throughout.
    """

    name = "kitchen"
    description = "Infrastructure as a bustling restaurant kitchen"

    def __init__(self):
        self._layout: dict[str, dict[str, float]] = {}

    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, float]]:
        """Compute kitchen layout: restaurants → stations → chefs → pots/pans."""
        layout: dict[str, dict[str, float]] = {}
        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        # Restaurants divide the canvas horizontally
        restaurant_w = w / max(len(roots), 1)
        for ri, root in enumerate(roots):
            rx = ri * restaurant_w
            layout[root["id"]] = {"x": rx, "y": 0, "w": restaurant_w, "h": h}

            # Stations (nodes) divide each restaurant vertically
            children = [by_id[cid] for cid in (root.get("children") or []) if cid in by_id]
            station_h = h / max(len(children), 1)
            for si, child in enumerate(children):
                sx = rx + 8
                sy = si * station_h + 8
                sw = restaurant_w - 16
                sh = station_h - 16
                layout[child["id"]] = {"x": sx, "y": sy, "w": sw, "h": sh}

                # Chefs (services) line up along the station
                grandchildren = [by_id[gcid] for gcid in (child.get("children") or []) if gcid in by_id]
                if not grandchildren:
                    continue
                chef_w = (sw - 16) / max(len(grandchildren), 1)
                for ci, gc in enumerate(grandchildren):
                    cpu = (gc.get("metrics") or {}).get("cpu", 50)
                    max_chef_h = sh - 24
                    chef_h = max(16, max_chef_h * (cpu / 100))
                    cx = sx + 8 + ci * chef_w
                    cy = sy + 8 + (max_chef_h - chef_h)
                    layout[gc["id"]] = {"x": cx, "y": cy, "w": chef_w - 6, "h": chef_h}

                    # Pots/pans (containers) sit on top of the chef
                    great_grandchildren = [by_id[ggcid] for ggcid in (gc.get("children") or []) if ggcid in by_id]
                    if not great_grandchildren:
                        continue
                    pot_w = (chef_w - 12) / max(len(great_grandchildren), 1)
                    for pi, ggc in enumerate(great_grandchildren):
                        px = cx + 3 + pi * pot_w
                        py = cy - 12  # pot sits above the chef
                        pw = pot_w - 4
                        ph = min(14, chef_h * 0.3)
                        layout[ggc["id"]] = {"x": px, "y": py, "w": pw, "h": ph}

        self._layout = layout
        return layout

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the kitchen metaphor with warm aesthetic."""
        layout = self.compute_layout(entities, w, h)

        # Dark warm wood background
        ctx.fillStyle(BG_COLOR)
        ctx.fillRect(0, 0, w, h)

        # Warm tile floor at bottom
        ctx.fillStyle(FLOOR_COLOR)
        ctx.fillRect(0, h - 30, w, 30)

        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            color = STATE_COLORS.get(entity.get("state", "unknown"), STATE_COLORS["unknown"])
            etype = entity.get("type", "")

            if etype == "cluster":
                # Restaurant border — warm outline with label
                ctx.strokeStyle(color)
                ctx.lineWidth(2)
                ctx.strokeRect(pos["x"] + 2, pos["y"] + 2, pos["w"] - 4, pos["h"] - 4)
                # Restaurant name label
                ctx.fillStyle(color)
                ctx.font("bold 14px system-ui, sans-serif")
                ctx.fillText(entity.get("name", ""), pos["x"] + 8, pos["y"] + 20)
                # Serving window indicator at top-right
                ctx.fillStyle(SERVING_WINDOW)
                ctx.fillRect(pos["x"] + pos["w"] - 40, pos["y"] + 4, 36, 16)
                ctx.fillStyle("#d4a76a")
                ctx.font("9px system-ui, sans-serif")
                ctx.fillText("PASS", pos["x"] + pos["w"] - 36, pos["y"] + 15)

            elif etype == "node":
                # Kitchen station counter
                ctx.fillStyle(STATION_BG)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle("#4a3728")
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])
                # Station label
                ctx.fillStyle("#c4a882")
                ctx.font("11px system-ui, sans-serif")
                ctx.fillText(entity.get("name", ""), pos["x"] + 6, pos["y"] + 16)

                # Empty station indicator if stopped
                if entity.get("state") == "stopped":
                    ctx.fillStyle("#5a4a3a")
                    ctx.font("9px system-ui, sans-serif")
                    ctx.fillText("[ CLOSED ]", pos["x"] + pos["w"] - 60, pos["y"] + 16)

                # Health inspector clipboard for warnings
                if entity.get("state") == "warning":
                    ctx.fillStyle("#f5c542")
                    ctx.fillRect(pos["x"] + pos["w"] - 20, pos["y"] + 4, 14, 18)
                    ctx.fillStyle("#1a0f0a")
                    ctx.font("8px system-ui, sans-serif")
                    ctx.fillText("!", pos["x"] + pos["w"] - 16, pos["y"] + 16)

            elif etype == "service":
                # Chef — body is the colored rectangle
                ctx.fillStyle(color)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle("#000")
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

                # Chef hat (white arc on top)
                if pos["w"] > 12:
                    hat_cx = pos["x"] + pos["w"] / 2
                    hat_cy = pos["y"]
                    hat_r = min(pos["w"] / 3, 8)
                    ctx.fillStyle("#f5f0e8")
                    ctx.beginPath()
                    ctx.arc(hat_cx, hat_cy, hat_r, 3.14159, 0)
                    ctx.fill()

                # Cooking animation lines (when active)
                state = entity.get("state", "")
                if state in ("healthy", "running") and pos["h"] > 20:
                    ctx.strokeStyle("#ffcc66")
                    ctx.lineWidth(1)
                    # Sizzle lines
                    for i in range(3):
                        lx = pos["x"] + 4 + i * (pos["w"] / 3)
                        ly = pos["y"] + pos["h"] * 0.4
                        ctx.moveTo(lx, ly)
                        ctx.lineTo(lx + 2, ly - 4)
                        ctx.stroke()

                # Kitchen fire for critical
                if state == "critical" and pos["w"] > 15:
                    ctx.fillStyle("#ff4500")
                    fire_y = pos["y"] - 6
                    for i in range(3):
                        fx = pos["x"] + 3 + i * (pos["w"] / 3)
                        ctx.beginPath()
                        ctx.moveTo(fx, fire_y + 6)
                        ctx.lineTo(fx + 3, fire_y)
                        ctx.lineTo(fx + 6, fire_y + 6)
                        ctx.fill()

                # Label
                if pos["w"] > 25:
                    ctx.fillStyle("#fff")
                    ctx.font("9px system-ui, sans-serif")
                    ctx.fillText(entity.get("name", "")[:12], pos["x"] + 2, pos["y"] + pos["h"] + 12)

            elif etype == "container":
                # Pot/pan — rounded rectangle with steam
                ctx.fillStyle(color)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle("#555")
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

                # Pot handles
                if pos["w"] > 10:
                    ctx.fillStyle("#888")
                    ctx.fillRect(pos["x"] - 3, pos["y"] + pos["h"] / 2 - 2, 3, 4)
                    ctx.fillRect(pos["x"] + pos["w"], pos["y"] + pos["h"] / 2 - 2, 3, 4)

                # Steam rising from active pots
                state = entity.get("state", "")
                cpu = (entity.get("metrics") or {}).get("cpu", 0)
                if state in ("healthy", "running") and cpu > 20:
                    ctx.setGlobalAlpha(0.4)
                    ctx.fillStyle("#e8d8c8")
                    steam_base_y = pos["y"] - 2
                    for i in range(min(3, int(cpu / 25) + 1)):
                        sx = pos["x"] + pos["w"] * (0.25 + i * 0.25)
                        # Steam puffs (small circles rising)
                        ctx.beginPath()
                        ctx.arc(sx, steam_base_y - 4 - i * 3, 2, 0, 6.28318)
                        ctx.fill()
                    ctx.setGlobalAlpha(1.0)

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Generate tooltip text for an entity."""
        etype = entity.get("type", "")
        # Map entity types to kitchen terms
        type_labels = {
            "cluster": "Restaurant",
            "node": "Station",
            "service": "Chef",
            "container": "Pot/Pan",
        }
        type_label = type_labels.get(etype, etype)

        lines = [
            f"{entity.get('name', '?')} ({type_label})",
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
            lines.append(f"Orders/min: {m['req_per_sec']}")
        if "error_rate" in m:
            lines.append(f"Returned: {m['error_rate'] * 100:.1f}%")
        if "count" in m:
            lines.append(f"Count: {m['count']}")
        if "uptime_hrs" in m:
            lines.append(f"Shift: {m['uptime_hrs']}h")
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
                "cluster": "restaurant",
                "node": "station",
                "service": "chef",
                "container": "pot/pan",
            },
        }
