"""Naval Ship metaphor renderer — Cluster→Fleet, Node→Ship Section, Service→Station, Container→Compartment."""
from __future__ import annotations
import math
from typing import Any
from engine.metaphors.base import MetaphorRenderer


# Naval bridge aesthetic — deep blues, radar greens, steel grays
STATE_COLORS = {
    "healthy": "#00ff88",      # sonar green
    "running": "#4fc3f7",      # radar blue
    "idle": "#607d8b",         # steel gray
    "warning": "#ffab00",      # amber signal
    "degraded": "#ff6d00",     # orange alert
    "critical": "#ff1744",     # battle damage red
    "stopped": "#263238",      # dark steel
    "pending": "#7c4dff",      # purple signal
    "scaling": "#00e5ff",      # cyan active
    "unknown": "#546e7a",      # muted steel
}

# Ship section names for node-level layout
SHIP_SECTIONS = ["Bridge", "Engine Room", "Cargo Hold", "Weapons Bay"]

# Hull color palette
HULL_COLOR = "#0d1b2a"
DECK_COLOR = "#1b2838"
WATER_COLOR = "#0a1628"
RADAR_GREEN = "#00ff88"
STEEL_BORDER = "#37474f"
COMPARTMENT_FILL = "#162032"


class ShipRenderer(MetaphorRenderer):
    """Naval ship metaphor: clusters are fleets, nodes are ship sections,
    services are stations, containers are compartments.

    Visual features:
    - Ship cross-section layout (hull shape)
    - Radar pings for active services (request detection)
    - Sonar waves for health checks
    - Damage indicators for critical state (holes, sparks)
    - Battle stations alarm for critical cluster
    - Fuel gauge for memory, Engine RPM for CPU
    - Signal delay indicator for latency
    """

    name = "ship"
    description = "Infrastructure as a naval warship cross-section"

    def __init__(self):
        self._layout: dict[str, dict[str, Any]] = {}

    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, Any]]:
        """Compute positions for all entities in a ship cross-section layout.

        The ship hull is an elliptical cross-section. Clusters (fleets) get
        horizontal bands. Nodes (ship sections) are positioned as Bridge (top),
        Engine Room (bottom-left), Cargo (center), Weapons Bay (right).
        Services (stations) and Containers (compartments) fill within sections.
        """
        layout: dict[str, dict[str, float]] = {}
        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        # Hull dimensions — ship occupies 90% of canvas with margin
        hull_margin_x = w * 0.05
        hull_margin_y = h * 0.08
        hull_w = w - 2 * hull_margin_x
        hull_h = h - 2 * hull_margin_y

        # Fleet (cluster) layout — vertical stacking within hull
        fleet_count = max(len(roots), 1)
        fleet_h = hull_h / fleet_count

        for fi, root in enumerate(roots):
            fy = hull_margin_y + fi * fleet_h
            layout[root["id"]] = {
                "x": hull_margin_x, "y": fy,
                "w": hull_w, "h": fleet_h,
                "section": "fleet",
            }

            # Ship sections (nodes) — map to Bridge/Engine/Cargo/Weapons
            children = [by_id[cid] for cid in (root.get("children") or []) if cid in by_id]
            if not children:
                continue

            section_w = hull_w / max(len(children), 1)
            for si, child in enumerate(children):
                # Assign section name based on position
                section_name = SHIP_SECTIONS[si % len(SHIP_SECTIONS)]
                sx = hull_margin_x + si * section_w
                layout[child["id"]] = {
                    "x": sx + 4, "y": fy + 20,
                    "w": section_w - 8, "h": fleet_h - 28,
                    "section": section_name,
                }

                # Stations (services) — grid within section
                grandchildren = [by_id[gcid] for gcid in (child.get("children") or []) if gcid in by_id]
                if not grandchildren:
                    continue

                cols = max(1, int(math.ceil(math.sqrt(len(grandchildren)))))
                rows = max(1, int(math.ceil(len(grandchildren) / cols)))
                station_w = (section_w - 24) / max(cols, 1)
                station_h = (fleet_h - 48) / max(rows, 1)

                for gi, gc in enumerate(grandchildren):
                    row = gi // cols
                    col = gi % cols
                    gx = sx + 12 + col * station_w
                    gy = fy + 28 + row * station_h
                    layout[gc["id"]] = {
                        "x": gx + 2, "y": gy + 2,
                        "w": station_w - 4, "h": station_h - 4,
                        "section": "station",
                    }

                    # Compartments (containers) — nested within station
                    great_grandchildren = [by_id[ggcid] for ggcid in (gc.get("children") or []) if ggcid in by_id]
                    for cgi, ggc in enumerate(great_grandchildren):
                        comp_w = (station_w - 12) / max(len(great_grandchildren), 1)
                        layout[ggc["id"]] = {
                            "x": gx + 4 + cgi * comp_w,
                            "y": gy + station_h - 14,
                            "w": comp_w - 2, "h": 10,
                            "section": "compartment",
                        }

        self._layout = layout
        return layout

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the naval ship metaphor.

        Draws a ship cross-section with:
        - Dark ocean background
        - Hull outline (elliptical)
        - Sections with radar/sonar effects
        - Stations as instrument panels
        - Gauges for CPU (RPM) and memory (fuel)
        """
        layout = self.compute_layout(entities, w, h)

        # Ocean background
        ctx.fillStyle(WATER_COLOR)
        ctx.fillRect(0, 0, w, h)

        # Water line effect
        ctx.fillStyle("#0d2137")
        ctx.fillRect(0, h * 0.85, w, h * 0.15)

        # Hull outline — draw as rounded rectangle approximating ship cross-section
        hull_x = w * 0.03
        hull_y = h * 0.05
        hull_w = w * 0.94
        hull_h = h * 0.80
        ctx.fillStyle(HULL_COLOR)
        ctx.fillRect(hull_x, hull_y, hull_w, hull_h)
        ctx.strokeStyle(STEEL_BORDER)
        ctx.lineWidth(2)
        ctx.strokeRect(hull_x, hull_y, hull_w, hull_h)

        # Deck line
        ctx.fillStyle(DECK_COLOR)
        ctx.fillRect(hull_x, hull_y, hull_w, 8)

        # Render each entity by type
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            state = entity.get("state", "unknown")
            color = STATE_COLORS.get(state, STATE_COLORS["unknown"])
            etype = entity.get("type", "")
            metrics = entity.get("metrics") or {}

            if etype == "cluster":
                # Fleet — draw hull section border + battle stations alarm if critical
                ctx.strokeStyle(color)
                ctx.lineWidth(2)
                ctx.strokeRect(pos["x"] + 1, pos["y"] + 1, pos["w"] - 2, pos["h"] - 2)

                # Fleet label
                ctx.fillStyle(color)
                ctx.font("bold 13px monospace")
                ctx.fillText(f"FLEET: {entity.get('name', '')}", pos["x"] + 8, pos["y"] + 16)

                # Battle stations alarm for critical cluster
                if state == "critical":
                    ctx.strokeStyle("#ff1744")
                    ctx.lineWidth(3)
                    # Flashing border effect (static representation)
                    ctx.strokeRect(pos["x"] - 2, pos["y"] - 2, pos["w"] + 4, pos["h"] + 4)

            elif etype == "node":
                # Ship section — Bridge/Engine Room/Cargo/Weapons
                section_name = pos.get("section", "Section")
                ctx.fillStyle(DECK_COLOR)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle(STEEL_BORDER)
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

                # Section label
                ctx.fillStyle("#90a4ae")
                ctx.font("bold 11px monospace")
                ctx.fillText(f"[{section_name}]", pos["x"] + 4, pos["y"] + 14)

                # Sonar wave indicator for health
                if state in ("healthy", "running"):
                    # Concentric arcs (sonar ping)
                    for radius in [8, 14, 20]:
                        ctx.strokeStyle(f"rgba(0, 255, 136, {0.3 - radius * 0.01})")
                        ctx.lineWidth(1)
                        cx = pos["x"] + pos["w"] - 20
                        cy = pos["y"] + 14
                        ctx.beginPath()
                        ctx.arc(cx, cy, radius, -math.pi * 0.4, math.pi * 0.4)
                        ctx.stroke()

            elif etype == "service":
                # Station — instrument panel with radar ping
                ctx.fillStyle(color)
                ctx.setGlobalAlpha(0.25)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.setGlobalAlpha(1.0)

                ctx.strokeStyle(color)
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

                # Radar ping for active services
                if state in ("healthy", "running", "scaling"):
                    ctx.fillStyle(RADAR_GREEN)
                    ping_r = 3
                    px = pos["x"] + pos["w"] - 8
                    py = pos["y"] + 8
                    ctx.beginPath()
                    ctx.arc(px, py, ping_r, 0, math.pi * 2)
                    ctx.fill()

                # Damage indicators for critical
                if state == "critical":
                    # Sparks / damage marks
                    ctx.strokeStyle("#ff1744")
                    ctx.lineWidth(2)
                    dx = pos["x"] + pos["w"] * 0.5
                    dy = pos["y"] + pos["h"] * 0.5
                    for angle in [0, math.pi / 3, math.pi * 2 / 3]:
                        x1 = dx + math.cos(angle) * 6
                        y1 = dy + math.sin(angle) * 6
                        x2 = dx - math.cos(angle) * 6
                        y2 = dy - math.sin(angle) * 6
                        ctx.beginPath()
                        ctx.moveTo(x1, y1)
                        ctx.lineTo(x2, y2)
                        ctx.stroke()

                # Station label
                ctx.fillStyle("#cfd8dc")
                ctx.font("9px monospace")
                name = entity.get("name", "")[:14]
                ctx.fillText(name, pos["x"] + 3, pos["y"] + pos["h"] - 4)

                # Fuel gauge (memory) — small bar on left side
                mem_pct = metrics.get("mem_pct", metrics.get("mem", 0))
                if mem_pct and pos["h"] > 20:
                    gauge_h = pos["h"] - 16
                    fuel_level = gauge_h * (mem_pct / 100)
                    gx = pos["x"] + 2
                    gy = pos["y"] + 8 + (gauge_h - fuel_level)
                    ctx.fillStyle("#1a237e" if mem_pct < 80 else "#b71c1c")
                    ctx.fillRect(gx, gy, 3, fuel_level)
                    ctx.strokeStyle("#455a64")
                    ctx.lineWidth(0.5)
                    ctx.strokeRect(gx, pos["y"] + 8, 3, gauge_h)

                # Engine RPM (CPU) — small bar on right side
                cpu_pct = metrics.get("cpu_pct", metrics.get("cpu", 0))
                if cpu_pct and pos["h"] > 20:
                    gauge_h = pos["h"] - 16
                    rpm_level = gauge_h * (cpu_pct / 100)
                    gx = pos["x"] + pos["w"] - 5
                    gy = pos["y"] + 8 + (gauge_h - rpm_level)
                    ctx.fillStyle("#004d40" if cpu_pct < 80 else "#ff6f00")
                    ctx.fillRect(gx, gy, 3, rpm_level)
                    ctx.strokeStyle("#455a64")
                    ctx.lineWidth(0.5)
                    ctx.strokeRect(gx, pos["y"] + 8, 3, gauge_h)

                # Signal delay indicator (latency) — dots above station
                latency = metrics.get("latency_ms", 0)
                if latency and pos["w"] > 20:
                    dot_count = min(5, max(1, int(latency / 20)))
                    for di in range(dot_count):
                        dx = pos["x"] + 6 + di * 5
                        dy = pos["y"] + 3
                        ctx.fillStyle("#ffab00" if latency > 60 else RADAR_GREEN)
                        ctx.beginPath()
                        ctx.arc(dx, dy, 1.5, 0, math.pi * 2)
                        ctx.fill()

            elif etype == "container":
                # Compartment — small filled rect within station
                ctx.fillStyle(COMPARTMENT_FILL)
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle(STEEL_BORDER)
                ctx.lineWidth(0.5)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])

                # Status dot
                ctx.fillStyle(color)
                ctx.beginPath()
                ctx.arc(pos["x"] + pos["w"] / 2, pos["y"] + pos["h"] / 2, 2, 0, math.pi * 2)
                ctx.fill()

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Generate tooltip text for a ship entity."""
        etype = entity.get("type", "?")
        mapping = {
            "cluster": "Fleet",
            "node": "Ship Section",
            "service": "Station",
            "container": "Compartment",
        }
        lines = [
            f"{entity.get('name', '?')} ({mapping.get(etype, etype)})",
            f"State: {entity.get('state', 'unknown')}",
        ]
        m = entity.get("metrics") or {}
        if "cpu_pct" in m:
            lines.append(f"Engine RPM: {m['cpu_pct']}%")
        if "mem_pct" in m:
            lines.append(f"Fuel Level: {m['mem_pct']}%")
        if "cpu" in m:
            lines.append(f"Engine RPM: {m['cpu']}%")
        if "mem" in m:
            lines.append(f"Fuel Level: {m['mem']}%")
        if "latency_ms" in m:
            lines.append(f"Signal Delay: {m['latency_ms']}ms")
        if "req_per_sec" in m:
            lines.append(f"Radar Contacts: {m['req_per_sec']}/s")
        if "error_rate" in m:
            lines.append(f"Damage Report: {m['error_rate'] * 100:.1f}%")
        if "count" in m:
            lines.append(f"Compartments: {m['count']}")
        if "uptime_hrs" in m:
            lines.append(f"Sea Time: {m['uptime_hrs']}h")
        return "\n".join(lines)

    def hit_test(self, entity: dict[str, Any], x: int, y: int) -> bool:
        """Check if (x,y) falls within this entity's layout bounds."""
        eid = entity.get("id")
        if not eid:
            return False
        pos = self._layout.get(eid)
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
                "cluster": "fleet",
                "node": "ship_section",
                "service": "station",
                "container": "compartment",
            },
            "ship_sections": SHIP_SECTIONS,
            "visual_features": [
                "radar_ping",
                "sonar_wave",
                "damage_indicator",
                "battle_stations_alarm",
                "fuel_gauge",
                "engine_rpm",
                "signal_delay",
            ],
        }
