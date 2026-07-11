"""Space Station metaphor renderer — Cluster→Station Ring, Node→Module, Service→Pod, Container→Compartment.

Dark space background with stars, modules connected by illuminated corridors,
docking ports glow on request traffic, life support indicators per module.
CPU = power core glow, Memory = storage bay fill, Health = life support status.
Critical = breach animation (sparks, red alerts).
"""
from __future__ import annotations
import math
import random
from typing import Any
from engine.metaphors.base import MetaphorRenderer


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
    """Space Station metaphor: clusters are station rings, nodes are modules,
    services are pods, containers are compartments.

    Radial layout around a central power core. Modules orbit the ring,
    connected by illuminated corridors. Docking ports glow with request traffic.
    """

    name = "space"
    description = "Infrastructure as an orbital space station"

    def __init__(self):
        self._layout: dict[str, dict[str, Any]] = {}
        self._stars: list[tuple[float, float, float]] = []  # (x, y, brightness)

    def _generate_stars(self, w: int, h: int, count: int = 120) -> None:
        """Generate deterministic star field for parallax background."""
        rng = random.Random(42)  # deterministic seed
        self._stars = [
            (rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.2, 1.0))
            for _ in range(count)
        ]

    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, Any]]:
        """Compute radial layout for space station arrangement.

        Cluster (Station Ring) sits at center.
        Nodes (Modules) orbit radially around it.
        Services (Pods) dock at module ports.
        Containers (Compartments) nest inside pods.
        """
        if not entities:
            self._layout = {}
            return {}

        self._generate_stars(w, h)
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

            # Non-cluster roots (orphaned services/containers) handled later
            if etype != "cluster":
                continue

            # Power core radius scales with CPU
            core_radius = 20 + (base_radius * 0.3) * (cpu / 100)

            layout[root["id"]] = {
                "x": cx - core_radius, "y": cy - core_radius,
                "w": core_radius * 2, "h": core_radius * 2,
                "cx": cx, "cy": cy,
                "core_radius": core_radius,
                "ring_radius": base_radius,
                "power_glow": cpu / 100,
                "breach": root.get("state") == "critical",
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

                layout[child["id"]] = {
                    "x": mod_x - mod_size, "y": mod_y - mod_size,
                    "w": mod_size * 2, "h": mod_size * 2,
                    "cx": mod_x, "cy": mod_y,
                    "angle": angle,
                    "orbit_radius": base_radius,
                    "life_support": LIFE_SUPPORT.get(child.get("state", "unknown"), "unknown"),
                    "breach": child.get("state") == "critical",
                }

                # Grandchildren (Pods) at module docking ports
                grandchildren = [by_id[gcid] for gcid in (child.get("children") or []) if gcid in by_id]
                for pi, pod in enumerate(grandchildren):
                    pod_metrics = pod.get("metrics") or {}
                    req = pod_metrics.get("req_per_sec", 0)
                    pod_mem = pod_metrics.get("mem", 0)
                    pod_cpu = pod_metrics.get("cpu", 0)

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

                    layout[pod["id"]] = {
                        "x": pod_x - pod_size, "y": pod_y - pod_size,
                        "w": pod_size * 2, "h": pod_size * 2,
                        "cx": pod_x, "cy": pod_y,
                        "storage_fill": storage_fill,
                        "docking_glow": docking_glow,
                        "breach": pod.get("state") == "critical",
                    }

                    # Great-grandchildren (Compartments) inside pods
                    compartments = [by_id[ccid] for ccid in (pod.get("children") or []) if ccid in by_id]
                    for ci, comp in enumerate(compartments):
                        comp_size = 8
                        comp_x = pod_x + (ci - len(compartments) / 2) * (comp_size + 2)
                        comp_y = pod_y

                        layout[comp["id"]] = {
                            "x": comp_x - comp_size, "y": comp_y - comp_size,
                            "w": comp_size * 2, "h": comp_size * 2,
                            "cx": comp_x, "cy": comp_y,
                            "breach": comp.get("state") == "critical",
                        }

            # Handle standalone services (no cluster parent)
            # Already covered above if they have no parent

        # Handle entities not yet placed (standalone or orphaned)
        for e in entities:
            if e["id"] in layout:
                continue
            etype = e.get("type", "")
            metrics = e.get("metrics") or {}
            if etype == "service":
                req = metrics.get("req_per_sec", 0)
                layout[e["id"]] = {
                    "x": cx - 15, "y": cy - 15, "w": 30, "h": 30,
                    "cx": cx, "cy": cy,
                    "storage_fill": metrics.get("mem", 0) / 100,
                    "docking_glow": min(req / 50, 1.0) if req else 0.0,
                    "breach": e.get("state") == "critical",
                }
            elif etype == "container":
                layout[e["id"]] = {
                    "x": cx - 8, "y": cy - 8, "w": 16, "h": 16,
                    "cx": cx, "cy": cy,
                    "breach": e.get("state") == "critical",
                }
            else:
                layout[e["id"]] = {
                    "x": cx - 10, "y": cy - 10, "w": 20, "h": 20,
                    "cx": cx, "cy": cy,
                    "breach": e.get("state") == "critical",
                }

        self._layout = layout
        return layout

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the space station metaphor."""
        layout = self.compute_layout(entities, w, h)

        # Dark space background
        ctx.fillStyle("#050510")
        ctx.fillRect(0, 0, w, h)

        # Stars (parallax background)
        for sx, sy, brightness in self._stars:
            ctx.globalAlpha(brightness)
            ctx.fillStyle("#ffffff")
            ctx.fillRect(sx, sy, 1.5, 1.5)
        ctx.globalAlpha(1.0)

        by_id = {e["id"]: e for e in entities}

        # Draw corridors (connections between modules and their parent ring)
        for entity in entities:
            if entity.get("type") == "node":
                pos = layout.get(entity["id"])
                parent_id = entity.get("parent")
                parent_pos = layout.get(parent_id) if parent_id else None
                if pos and parent_pos:
                    ctx.strokeStyle("#1e40af")
                    ctx.lineWidth(2)
                    ctx.beginPath()
                    ctx.moveTo(parent_pos["cx"], parent_pos["cy"])
                    ctx.lineTo(pos["cx"], pos["cy"])
                    ctx.stroke()

        # Draw entities
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            color = STATE_COLORS.get(entity.get("state", "unknown"), STATE_COLORS["unknown"])
            etype = entity.get("type", "")

            if etype == "cluster":
                # Station Ring — outer ring
                ctx.strokeStyle(color)
                ctx.lineWidth(3)
                ctx.beginPath()
                ctx.arc(pos["cx"], pos["cy"], pos["ring_radius"], 0, 2 * math.pi)
                ctx.stroke()

                # Power core glow (CPU)
                ctx.globalAlpha(0.3 + 0.5 * pos.get("power_glow", 0.5))
                ctx.fillStyle(color)
                ctx.beginPath()
                ctx.arc(pos["cx"], pos["cy"], pos["core_radius"], 0, 2 * math.pi)
                ctx.fill()
                ctx.globalAlpha(1.0)

                # Core outline
                ctx.strokeStyle(color)
                ctx.lineWidth(2)
                ctx.beginPath()
                ctx.arc(pos["cx"], pos["cy"], pos["core_radius"], 0, 2 * math.pi)
                ctx.stroke()

                # Label
                ctx.fillStyle("#e2e8f0")
                ctx.font("bold 13px system-ui, sans-serif")
                ctx.fillText(entity.get("name", ""), pos["cx"] - 30, pos["cy"] + 4)

            elif etype == "node":
                # Module — circular node on the ring
                ctx.fillStyle("#111827" if entity.get("state") != "critical" else "#1a0505")
                ctx.beginPath()
                ctx.arc(pos["cx"], pos["cy"], pos["w"] / 2, 0, 2 * math.pi)
                ctx.fill()

                # Life support indicator ring
                ctx.strokeStyle(color)
                ctx.lineWidth(3)
                ctx.beginPath()
                ctx.arc(pos["cx"], pos["cy"], pos["w"] / 2, 0, 2 * math.pi)
                ctx.stroke()

                # Breach animation for critical
                if pos.get("breach"):
                    ctx.strokeStyle("#ef4444")
                    ctx.lineWidth(1)
                    for _ in range(6):
                        spark_angle = random.uniform(0, 2 * math.pi)
                        spark_len = random.uniform(5, 15)
                        ctx.beginPath()
                        ctx.moveTo(
                            pos["cx"] + (pos["w"] / 2) * math.cos(spark_angle),
                            pos["cy"] + (pos["w"] / 2) * math.sin(spark_angle),
                        )
                        ctx.lineTo(
                            pos["cx"] + (pos["w"] / 2 + spark_len) * math.cos(spark_angle),
                            pos["cy"] + (pos["w"] / 2 + spark_len) * math.sin(spark_angle),
                        )
                        ctx.stroke()

                # Label
                ctx.fillStyle("#d1d5db")
                ctx.font("10px system-ui, sans-serif")
                ctx.fillText(entity.get("name", "")[:14], pos["cx"] - 20, pos["cy"] + pos["w"] / 2 + 14)

            elif etype == "service":
                # Pod — docking port with glow
                glow = pos.get("docking_glow", 0)
                if glow > 0:
                    ctx.globalAlpha(glow * 0.4)
                    ctx.fillStyle("#38bdf8")
                    ctx.beginPath()
                    ctx.arc(pos["cx"], pos["cy"], pos["w"] / 2 + 6, 0, 2 * math.pi)
                    ctx.fill()
                    ctx.globalAlpha(1.0)

                # Pod body
                ctx.fillStyle(color)
                ctx.beginPath()
                ctx.arc(pos["cx"], pos["cy"], pos["w"] / 2, 0, 2 * math.pi)
                ctx.fill()

                # Storage bay fill (memory)
                fill_h = pos["h"] * pos.get("storage_fill", 0)
                if fill_h > 0:
                    ctx.globalAlpha(0.4)
                    ctx.fillStyle("#60a5fa")
                    ctx.fillRect(pos["x"], pos["y"] + pos["h"] - fill_h, pos["w"], fill_h)
                    ctx.globalAlpha(1.0)

                # Breach sparks
                if pos.get("breach"):
                    ctx.strokeStyle("#ef4444")
                    ctx.lineWidth(1)
                    for _ in range(4):
                        spark_angle = random.uniform(0, 2 * math.pi)
                        spark_len = random.uniform(3, 8)
                        ctx.beginPath()
                        ctx.moveTo(pos["cx"], pos["cy"])
                        ctx.lineTo(
                            pos["cx"] + (pos["w"] / 2 + spark_len) * math.cos(spark_angle),
                            pos["cy"] + (pos["w"] / 2 + spark_len) * math.sin(spark_angle),
                        )
                        ctx.stroke()

                # Label
                ctx.fillStyle("#fff")
                ctx.font("8px system-ui, sans-serif")
                ctx.fillText(entity.get("name", "")[:10], pos["cx"] - 12, pos["cy"] + pos["h"] / 2 + 10)

            elif etype == "container":
                # Compartment — small rectangle inside pod
                ctx.fillStyle(color)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle("#000")
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

                # Breach flash
                if pos.get("breach"):
                    ctx.globalAlpha(0.6)
                    ctx.fillStyle("#ef4444")
                    ctx.fillRect(pos["x"] - 2, pos["y"] - 2, pos["w"] + 4, pos["h"] + 4)
                    ctx.globalAlpha(1.0)

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Generate tooltip with space station terminology."""
        etype = entity.get("type", "?")
        mapping = {"cluster": "Station Ring", "node": "Module", "service": "Pod", "container": "Compartment"}
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
                "cluster": "station ring",
                "node": "module",
                "service": "pod",
                "container": "compartment",
            },
        }
