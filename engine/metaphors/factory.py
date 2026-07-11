"""Factory metaphor renderer — Cluster→Factory Floor, Node→Workstation,
Service→Machine, Container→Conveyor Belt.

Industrial steampunk aesthetic: warm metal, copper, brass tones.
Machines have spinning gears (CPU), hoppers (memory).
Conveyor belts carry products (requests). Sparks for errors, steam for warnings.
"""
from __future__ import annotations
from typing import Any
from engine.metaphors.base import MetaphorRenderer


# Steampunk palette — warm metals, copper, brass
STATE_COLORS = {
    "healthy": "#4ade80",      # green indicator lamp
    "running": "#60a5fa",      # blue pilot light
    "idle": "#94a3b8",         # dull steel
    "warning": "#fbbf24",      # amber caution lamp
    "degraded": "#f97316",     # orange alert
    "critical": "#ef4444",     # red emergency
    "stopped": "#374151",      # dark iron
    "pending": "#a78bfa",      # purple standby
    "scaling": "#06b6d4",      # cyan ramping
    "unknown": "#6b7280",      # grey
}

# Steampunk structural palette
COPPER = "#b87333"
BRASS = "#cd7f32"
DARK_BRASS = "#8b4513"
WARM_METAL = "#d4a574"
IRON = "#704214"
STEEL_DARK = "#2d1f14"
FLOOR_WOOD = "#3e2723"
CONVEYOR_GREY = "#4a4a4a"
CONVEYOR_BELT = "#5c5c5c"
PIPE_COPPER = "#a0522d"


class FactoryRenderer(MetaphorRenderer):
    """Factory metaphor: clusters are factory floors, nodes are workstations,
    services are machines, containers are conveyor belts.

    Linear assembly-line layout. Machine height scales with CPU.
    Conveyor belts show product flow. Bottlenecks visualized as pileups.
    """

    name = "factory"
    description = "Infrastructure as a steampunk factory assembly line"

    def __init__(self):
        self._layout: dict[str, dict[str, float]] = {}

    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, float]]:
        """Compute positions for linear assembly arrangement.

        Clusters span full width as factory floors.
        Nodes are workstations stacked vertically within floors.
        Services (machines) arranged left-to-right as assembly stations.
        Containers (conveyor belts) placed between machines.
        """
        layout: dict[str, dict[str, float]] = {}
        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        if not roots:
            self._layout = layout
            return layout

        # Factory floors (clusters) span horizontally
        floor_h = h / max(len(roots), 1)
        for fi, root in enumerate(roots):
            fy = fi * floor_h
            layout[root["id"]] = {"x": 0, "y": fy, "w": w, "h": floor_h}

            # Workstations (nodes) stacked vertically within floor
            children = [by_id[cid] for cid in (root.get("children") or []) if cid in by_id]
            if not children:
                continue
            ws_h = (floor_h - 40) / max(len(children), 1)

            for wi, child in enumerate(children):
                wy = fy + 30 + wi * ws_h
                layout[child["id"]] = {
                    "x": 20, "y": wy,
                    "w": w - 40, "h": ws_h - 10,
                }

                # Machines (services) arranged left-to-right as assembly line
                grandchildren = [by_id[gcid] for gcid in (child.get("children") or [])
                                 if gcid in by_id]
                if not grandchildren:
                    continue

                machine_count = len(grandchildren)
                machine_slot_w = (w - 80) / max(machine_count, 1)

                for mi, gc in enumerate(grandchildren):
                    mx = 40 + mi * machine_slot_w
                    cpu = (gc.get("metrics") or {}).get("cpu", 50)
                    max_mh = ws_h - 50
                    mh = max(30, max_mh * (cpu / 100))

                    layout[gc["id"]] = {
                        "x": mx, "y": wy + 20 + (max_mh - mh),
                        "w": machine_slot_w - 20, "h": mh,
                    }

                    # Conveyor belts (containers) between machines
                    great_grandchildren = [by_id[ggcid] for ggcid in (gc.get("children") or [])
                                           if ggcid in by_id]
                    for ci, container in enumerate(great_grandchildren):
                        # Place conveyor belt below/after the machine
                        layout[container["id"]] = {
                            "x": mx + 5, "y": wy + 20 + max_mh + 5,
                            "w": machine_slot_w - 30, "h": 16,
                        }

        self._layout = layout
        return layout

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the factory metaphor with steampunk aesthetic."""
        layout = self.compute_layout(entities, w, h)

        # Background — dark workshop floor
        ctx.fillStyle(STEEL_DARK)
        ctx.fillRect(0, 0, w, h)

        # Wooden floor texture
        ctx.fillStyle(FLOOR_WOOD)
        ctx.fillRect(0, h - 20, w, 20)

        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            color = STATE_COLORS.get(entity.get("state", "unknown"), STATE_COLORS["unknown"])
            etype = entity.get("type", "")

            if etype == "cluster":
                # Factory floor — copper frame, brick interior
                ctx.fillStyle("#1a0f0a")
                ctx.fillRect(pos["x"] + 2, pos["y"] + 2, pos["w"] - 4, pos["h"] - 4)
                ctx.strokeStyle(COPPER)
                ctx.lineWidth(3)
                ctx.strokeRect(pos["x"] + 2, pos["y"] + 2, pos["w"] - 4, pos["h"] - 4)
                # Rivets at corners
                ctx.fillStyle(BRASS)
                for rx, ry in [(pos["x"] + 8, pos["y"] + 8),
                               (pos["x"] + pos["w"] - 12, pos["y"] + 8),
                               (pos["x"] + 8, pos["y"] + pos["h"] - 12),
                               (pos["x"] + pos["w"] - 12, pos["y"] + pos["h"] - 12)]:
                    ctx.beginPath()
                    ctx.arc(rx, ry, 3, 0, 6.28)
                    ctx.fill()
                # Label
                ctx.fillStyle(COPPER)
                ctx.font("bold 14px monospace")
                ctx.fillText(entity.get("name", ""), pos["x"] + 16, pos["y"] + 22)

            elif etype == "node":
                # Workstation — iron frame
                ctx.fillStyle("#1c1208")
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle(IRON)
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])
                # Pipe along top
                ctx.fillStyle(PIPE_COPPER)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], 4)
                # Label
                ctx.fillStyle(WARM_METAL)
                ctx.font("11px monospace")
                ctx.fillText(entity.get("name", ""), pos["x"] + 8, pos["y"] + 18)

            elif etype == "service":
                # Machine — body with gear
                ctx.fillStyle(color)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle(DARK_BRASS)
                ctx.lineWidth(2)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

                # Gear (CPU indicator) — circle in center
                if pos["w"] > 25 and pos["h"] > 25:
                    cx = pos["x"] + pos["w"] / 2
                    cy = pos["y"] + pos["h"] / 2
                    gear_r = min(pos["w"], pos["h"]) / 4
                    ctx.fillStyle(BRASS)
                    ctx.beginPath()
                    ctx.arc(cx, cy, gear_r, 0, 6.28)
                    ctx.fill()
                    ctx.strokeStyle(DARK_BRASS)
                    ctx.lineWidth(1)
                    ctx.stroke()
                    # Gear teeth (simplified)
                    ctx.fillStyle(COPPER)
                    for angle in range(0, 360, 45):
                        import math
                        rad = math.radians(angle)
                        tx = cx + (gear_r + 4) * math.cos(rad)
                        ty = cy + (gear_r + 4) * math.sin(rad)
                        ctx.beginPath()
                        ctx.arc(tx, ty, 3, 0, 6.28)
                        ctx.fill()

                # Hopper (memory) — triangle on top
                mem = (entity.get("metrics") or {}).get("mem", 0)
                if mem > 0 and pos["w"] > 20:
                    hopper_h = max(5, 15 * (mem / 100))
                    ctx.fillStyle("#8b6914")
                    ctx.beginPath()
                    ctx.moveTo(pos["x"] + 5, pos["y"])
                    ctx.lineTo(pos["x"] + pos["w"] - 5, pos["y"])
                    ctx.lineTo(pos["x"] + pos["w"] / 2, pos["y"] - hopper_h)
                    ctx.closePath()
                    ctx.fill()

                # Sparks for errors
                state = entity.get("state", "")
                if state in ("critical", "degraded"):
                    ctx.fillStyle("#ff6b35")
                    import math
                    for i in range(5):
                        sx = pos["x"] + (pos["w"] * (i + 1) / 6)
                        sy = pos["y"] - 5 - (i % 3) * 4
                        ctx.beginPath()
                        ctx.arc(sx, sy, 2, 0, 6.28)
                        ctx.fill()

                # Steam for warnings
                if state == "warning":
                    ctx.fillStyle("rgba(200,200,200,0.4)")
                    for i in range(3):
                        sx = pos["x"] + pos["w"] / 2 + (i - 1) * 8
                        sy = pos["y"] - 8 - i * 5
                        ctx.beginPath()
                        ctx.arc(sx, sy, 4 + i, 0, 6.28)
                        ctx.fill()

                # Label
                if pos["w"] > 30:
                    ctx.fillStyle("#fff")
                    ctx.font("9px monospace")
                    ctx.fillText(entity.get("name", "")[:12],
                                 pos["x"] + 2, pos["y"] + pos["h"] + 12)

            elif etype == "container":
                # Conveyor belt
                ctx.fillStyle(CONVEYOR_BELT)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle(CONVEYOR_GREY)
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])
                # Belt rollers
                ctx.fillStyle("#888")
                roller_spacing = max(12, pos["w"] / 6)
                rx = pos["x"] + 6
                while rx < pos["x"] + pos["w"] - 6:
                    ctx.beginPath()
                    ctx.arc(rx, pos["y"] + pos["h"] / 2, 3, 0, 6.28)
                    ctx.fill()
                    rx += roller_spacing

                # Bottleneck pileup — products stacked if machine is bottleneck
                parent_id = entity.get("parent")
                if parent_id is not None:
                    parent_entity = next((e for e in entities if e["id"] == parent_id), None)
                    if parent_entity and self.is_bottleneck(parent_entity):
                        ctx.fillStyle("#ff4444")
                        for i in range(3):
                            px = pos["x"] + 8 + i * 10
                            py = pos["y"] - 6 - i * 4
                            ctx.fillRect(px, py, 8, 6)

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Generate tooltip text for an entity."""
        etype = entity.get("type", "?")
        metaphor_name = {
            "cluster": "Factory Floor",
            "node": "Workstation",
            "service": "Machine",
            "container": "Conveyor Belt",
        }.get(etype, etype)

        lines = [
            f"{entity.get('name', '?')} ({metaphor_name})",
            f"State: {entity.get('state', 'unknown')}",
        ]
        m = entity.get("metrics") or {}
        if "cpu" in m:
            lines.append(f"Gear Speed (CPU): {m['cpu']}%")
        if "mem" in m:
            lines.append(f"Hopper (Mem): {m['mem']}%")
        if "cpu_pct" in m:
            lines.append(f"Gear Speed (CPU): {m['cpu_pct']}%")
        if "mem_pct" in m:
            lines.append(f"Hopper (Mem): {m['mem_pct']}%")
        if "throughput" in m:
            lines.append(f"Throughput: {m['throughput']} products/min")
        if "req_per_sec" in m:
            lines.append(f"Belt Speed: {m['req_per_sec']} req/s")
        if "error_rate" in m:
            lines.append(f"Defect Rate: {m['error_rate'] * 100:.1f}%")
        if "count" in m:
            lines.append(f"Units: {m['count']}")

        if self.is_bottleneck(entity):
            lines.append("⚠ BOTTLENECK — pileup detected!")

        return "\n".join(lines)

    def hit_test(self, entity: dict[str, Any], x: int, y: int) -> bool:
        """Check if (x,y) falls within this entity's layout bounds."""
        pos = self._layout.get(entity.get("id"))
        if not pos:
            return False
        return (pos["x"] <= x <= pos["x"] + pos["w"] and
                pos["y"] <= y <= pos["y"] + pos["h"])

    def is_bottleneck(self, entity: dict[str, Any]) -> bool:
        """Detect if a machine is a bottleneck (high CPU + queue buildup)."""
        m = entity.get("metrics") or {}
        cpu = m.get("cpu", 0)
        queue = m.get("queue_depth", 0)
        state = entity.get("state", "")
        return (cpu > 80 and queue > 10) or state in ("critical", "degraded")

    def compute_throughput(self, entities: list[dict[str, Any]]) -> int:
        """Compute aggregate throughput (products per minute) across services."""
        total = 0
        for e in entities:
            if e.get("type") == "service":
                total += (e.get("metrics") or {}).get("throughput", 0)
        return total

    def config(self) -> dict[str, Any]:
        """Return metaphor configuration metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "state_colors": STATE_COLORS,
            "mappings": {
                "cluster": "factory_floor",
                "node": "workstation",
                "service": "machine",
                "container": "conveyor_belt",
            },
        }
