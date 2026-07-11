"""City metaphor renderer — Cluster→District, Node→Block, Service→Building."""
from __future__ import annotations
from typing import Any
from engine.metaphors.base import MetaphorRenderer


# State → color map
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


class CityRenderer(MetaphorRenderer):
    """City metaphor: clusters are districts, nodes are blocks, services are buildings.

    Building height scales with CPU usage. Color reflects state.
    Windows light up when healthy.
    """

    name = "city"
    description = "Infrastructure as a city skyline"

    def __init__(self):
        self._layout: dict[str, dict[str, float]] = {}

    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, float]]:
        """Compute positions for all entities. Returns layout dict."""
        layout: dict[str, dict[str, float]] = {}
        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        district_w = w / max(len(roots), 1)
        for di, root in enumerate(roots):
            dx = di * district_w
            layout[root["id"]] = {"x": dx, "y": 0, "w": district_w, "h": h}

            children = [by_id[cid] for cid in (root.get("children") or []) if cid in by_id]
            block_h = h / max(len(children), 1)
            for bi, child in enumerate(children):
                by_ = bi * block_h
                layout[child["id"]] = {
                    "x": dx + 10, "y": by_ + 10,
                    "w": district_w - 20, "h": block_h - 20,
                }

                grandchildren = [by_id[gcid] for gcid in (child.get("children") or []) if gcid in by_id]
                if not grandchildren:
                    continue
                building_w = (district_w - 40) / max(len(grandchildren), 1)
                for gi, gc in enumerate(grandchildren):
                    bx = dx + 20 + gi * building_w
                    cpu = (gc.get("metrics") or {}).get("cpu", 50)
                    max_bh = block_h - 40
                    bh = max(20, max_bh * (cpu / 100))
                    layout[gc["id"]] = {
                        "x": bx, "y": by_ + 10 + (max_bh - bh),
                        "w": building_w - 8, "h": bh,
                    }

        self._layout = layout
        return layout

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the city metaphor. ctx is a canvas-like drawing context."""
        layout = self.compute_layout(entities, w, h)

        # Background
        ctx.fillStyle("#0a0a1a")
        ctx.fillRect(0, 0, w, h)

        # Ground
        ctx.fillStyle("#1a1a2e")
        ctx.fillRect(0, h - 40, w, 40)

        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            color = STATE_COLORS.get(entity.get("state", "unknown"), STATE_COLORS["unknown"])
            etype = entity.get("type", "")

            if etype == "cluster":
                ctx.strokeStyle(color)
                ctx.lineWidth(2)
                ctx.strokeRect(pos["x"] + 2, pos["y"] + 2, pos["w"] - 4, pos["h"] - 4)
                ctx.fillStyle(color)
                ctx.font("bold 14px system-ui, sans-serif")
                ctx.fillText(entity.get("name", ""), pos["x"] + 8, pos["y"] + 20)

            elif etype == "node":
                ctx.fillStyle("#111827")
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle("#374151")
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.fillStyle("#9ca3af")
                ctx.font("11px system-ui, sans-serif")
                ctx.fillText(entity.get("name", ""), pos["x"] + 6, pos["y"] + 16)

            elif etype == "service":
                # Building
                ctx.fillStyle(color)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle("#000")
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

                # Windows
                if pos["h"] > 30 and pos["w"] > 15:
                    wy = pos["y"] + 8
                    while wy < pos["y"] + pos["h"] - 8:
                        wx = pos["x"] + 4
                        while wx < pos["x"] + pos["w"] - 4:
                            state = entity.get("state", "")
                            if state in ("healthy", "running"):
                                ctx.fillStyle("#fbbf24")
                            elif state == "warning":
                                ctx.fillStyle("#f97316")
                            else:
                                ctx.fillStyle("#1f2937")
                            ctx.fillRect(wx, wy, 4, 4)
                            wx += 10
                        wy += 12

                # Label
                if pos["w"] > 30:
                    ctx.fillStyle("#fff")
                    ctx.font("9px system-ui, sans-serif")
                    ctx.fillText(entity.get("name", "")[:12], pos["x"] + 2, pos["y"] + pos["h"] + 12)

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
        return (pos["x"] <= x <= pos["x"] + pos["w"] and
                pos["y"] <= y <= pos["y"] + pos["h"])

    def config(self) -> dict[str, Any]:
        """Return metaphor configuration metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "state_colors": STATE_COLORS,
            "mappings": {
                "cluster": "district",
                "node": "block",
                "service": "building",
            },
        }
