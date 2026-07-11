"""Traffic Light metaphor renderer — Cluster=Intersection, Node=Road,
Service=Traffic Light, Container=Lamp.

Urban road aesthetic: dark asphalt, signal colors (red/yellow/green).
"""
from __future__ import annotations
from typing import Any
from engine.metaphors.base import MetaphorRenderer


# State-to-signal color mapping
STATE_COLORS = {
    "healthy":  "#22c55e",   # green light — go
    "running":  "#22c55e",   # green light — go
    "idle":     "#eab308",   # yellow light — caution
    "warning":  "#eab308",   # yellow light — caution
    "degraded": "#f97316",   # orange — attention
    "critical": "#ef4444",   # red light — stop
    "stopped":  "#6b7280",   # dark — no signal
    "pending":  "#a78bfa",   # purple — waiting
    "scaling":  "#06b6d4",   # cyan — ramping
    "unknown":  "#4b5563",   # grey
}

ASPHALT = "#1e1e1e"
ROAD_MARKING = "#fbbf24"
HOUSING = "#111827"


class TrafficLightRenderer(MetaphorRenderer):
    """Traffic Light metaphor: clusters are intersections, nodes are roads,
    services are traffic lights, containers are lamps."""

    name = "traffic_light"
    description = "Infrastructure as a city traffic intersection"

    def __init__(self):
        self._layout: dict[str, dict[str, float]] = {}

    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, float]]:
        """Compute intersection layout.

        Clusters = intersections (horizontal split).
        Nodes = roads through intersection (vertical lanes).
        Services = traffic lights at road edges.
        Containers = individual lamps.
        """
        layout: dict[str, dict[str, float]] = {}
        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        if not roots:
            self._layout = layout
            return layout

        # Intersections divide canvas horizontally
        intersection_w = w / max(len(roots), 1)
        for i, root in enumerate(roots):
            ix = i * intersection_w
            layout[root["id"]] = {"x": ix, "y": 0, "w": intersection_w, "h": h}

            # Roads (nodes) are vertical lanes within each intersection
            children = [by_id[cid] for cid in (root.get("children") or []) if cid in by_id]
            if not children:
                continue
            lane_w = (intersection_w - 20) / max(len(children), 1)

            for li, child in enumerate(children):
                lx = ix + 10 + li * lane_w
                layout[child["id"]] = {
                    "x": lx, "y": 10,
                    "w": lane_w - 4, "h": h - 20,
                }

                # Traffic lights (services) sit along each road
                grandchildren = [by_id[gcid] for gcid in (child.get("children") or [])
                                 if gcid in by_id]
                if not grandchildren:
                    continue

                light_h = min(80, (h - 40) / max(len(grandchildren), 1))
                for gi, gc in enumerate(grandchildren):
                    cpu = (gc.get("metrics") or {}).get("cpu", 50)
                    light_w = 20 + (lane_w - 30) * (cpu / 100)
                    gx = lx + (lane_w - light_w) / 2
                    gy = 20 + gi * light_h

                    layout[gc["id"]] = {
                        "x": gx, "y": gy,
                        "w": light_w, "h": light_h - 8,
                    }

                    # Lamps (containers) inside each traffic light
                    great_grandchildren = [by_id[ggcid] for ggcid in (gc.get("children") or [])
                                           if ggcid in by_id]
                    lamp_h = (light_h - 16) / max(len(great_grandchildren), 1)
                    for ci, container in enumerate(great_grandchildren):
                        layout[container["id"]] = {
                            "x": gx + 4, "y": gy + 4 + ci * lamp_h,
                            "w": light_w - 8, "h": lamp_h - 2,
                        }

        self._layout = layout
        return layout

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the traffic light metaphor."""
        layout = self.compute_layout(entities, w, h)

        # Background — dark asphalt
        ctx.fillStyle(ASPHALT)
        ctx.fillRect(0, 0, w, h)

        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue

            color = STATE_COLORS.get(entity.get("state", "unknown"), STATE_COLORS["unknown"])
            etype = entity.get("type", "")

            if etype == "cluster":
                # Intersection — asphalt with road markings
                ctx.fillStyle("#252525")
                ctx.fillRect(pos["x"] + 2, pos["y"] + 2, pos["w"] - 4, pos["h"] - 4)
                # Yellow center line
                ctx.fillStyle(ROAD_MARKING)
                ctx.fillRect(pos["x"] + pos["w"] / 2 - 1, pos["y"], 2, pos["h"])
                # Label
                ctx.fillStyle("#9ca3af")
                ctx.font("bold 13px monospace")
                ctx.fillText(entity.get("name", ""), pos["x"] + 8, pos["y"] + 18)

            elif etype == "node":
                # Road lane — dark grey with dashed markings
                ctx.fillStyle("#2a2a2a")
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                # Dashed center line
                ctx.fillStyle(ROAD_MARKING)
                dy = pos["y"] + 10
                while dy < pos["y"] + pos["h"] - 10:
                    ctx.fillRect(pos["x"] + pos["w"] / 2 - 1, dy, 2, 8)
                    dy += 16
                # Label
                ctx.fillStyle("#6b7280")
                ctx.font("10px monospace")
                ctx.fillText(entity.get("name", ""), pos["x"] + 4, pos["y"] + 14)

            elif etype == "service":
                # Traffic light housing — dark box with colored signal
                ctx.fillStyle(HOUSING)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle("#374151")
                ctx.lineWidth(2)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

                # Signal light (colored circle)
                cx = pos["x"] + pos["w"] / 2
                cy = pos["y"] + pos["h"] / 2
                radius = min(pos["w"], pos["h"]) / 3
                ctx.fillStyle(color)
                ctx.beginPath()
                ctx.arc(cx, cy, radius, 0, 6.28)
                ctx.fill()

                # Label below
                ctx.fillStyle("#d1d5db")
                ctx.font("9px monospace")
                name = entity.get("name", "")[:10]
                ctx.fillText(name, pos["x"] + 2, pos["y"] + pos["h"] + 12)

            elif etype == "container":
                # Individual lamp — small colored rectangle
                ctx.fillStyle(color)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle("#1f2937")
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Generate tooltip text for an entity."""
        etype = entity.get("type", "?")
        metaphor_name = {
            "cluster": "Intersection",
            "node": "Road",
            "service": "Traffic Light",
            "container": "Lamp",
        }.get(etype, etype)

        signal_state = {
            "healthy": "GREEN — flowing",
            "running": "GREEN — flowing",
            "idle": "YELLOW — idle",
            "warning": "YELLOW — caution",
            "critical": "RED — stop!",
            "stopped": "OFF — no signal",
        }.get(entity.get("state", ""), "UNKNOWN")

        lines = [
            f"{entity.get('name', '?')} ({metaphor_name})",
            f"Signal: {signal_state}",
        ]
        m = entity.get("metrics") or {}
        if "cpu" in m:
            lines.append(f"Brightness (CPU): {m['cpu']}%")
        if "mem" in m:
            lines.append(f"Lamp Size (Mem): {m['mem']}%")
        if "req_per_sec" in m:
            lines.append(f"Traffic Flow: {m['req_per_sec']} cars/s")

        return "\n".join(lines)

    def hit_test(self, entity: dict[str, Any], x: int, y: int) -> bool:
        """Check if (x,y) falls within this entity's rendered area."""
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
                "cluster": "intersection",
                "node": "road",
                "service": "traffic_light",
                "container": "lamp",
            },
        }
