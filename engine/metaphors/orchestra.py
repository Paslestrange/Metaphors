"""Orchestra metaphor renderer — Cluster=Section, Node=Chair, Service=Musician, Container=Instrument.

Concert hall aesthetic: warm wood tones, stage lighting, curtain backdrop.
Musicians seated in section layout (strings, brass, woodwinds, percussion).
Sound waves visualized as flowing lines. Tempo = BPM from req/s.
Volume bars for CPU. Sheet music scroll for active processes.
Discordant flash for errors. Standing ovation for all-healthy cluster.
"""
from __future__ import annotations
import math
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

# Section → warm wood tone colors
SECTION_COLORS = {
    "strings": "#8B6914",       # warm golden wood
    "brass": "#B8860B",         # dark goldenrod
    "woodwinds": "#6B4226",     # dark walnut
    "percussion": "#5C4033",    # dark oak
    "default": "#7B5B3A",       # medium wood
}

# Concert hall palette
HALL_BG = "#1a0f08"            # dark stage floor
CURTAIN_COLOR = "#8B0000"      # deep red curtain
STAGE_WOOD = "#3d2b1f"         # stage wood floor
SPOTLIGHT_COLOR = "#fff8dc"    # warm spotlight
SOUND_WAVE_COLOR = "#d4a574"   # warm amber wave


class OrchestraRenderer(MetaphorRenderer):
    """Orchestra metaphor: clusters are sections, nodes are chairs,
    services are musicians, containers are instruments.

    Concert hall layout with curved section arrangement.
    Volume bars show CPU. Tempo indicator shows req/s as BPM.
    """

    name = "orchestra"
    description = "Infrastructure as a concert hall orchestra"

    def __init__(self):
        self._layout: dict[str, dict[str, float]] = {}
        self.tempo_bpm: float = 0
        self._ovation: bool = False

    def compute_layout(self, entities: list[dict[str, Any]], w: int, h: int) -> dict[str, dict[str, float]]:
        """Compute concert hall seating arrangement.

        Sections (clusters) arranged in curved rows from stage front.
        Chairs (nodes) are positions within sections.
        Musicians (services) sit in chairs with volume bars.
        """
        layout: dict[str, dict[str, float]] = {}
        by_id = {e["id"]: e for e in entities}
        roots = [e for e in entities if not e.get("parent")]

        if not roots:
            self._layout = layout
            return layout

        # Compute tempo from any entity with req_per_sec
        self.tempo_bpm = 0
        for e in entities:
            m = e.get("metrics") or {}
            if "req_per_sec" in m:
                self.tempo_bpm = m["req_per_sec"]
                break

        # Stage area: top 15% for curtain, bottom 85% for seating
        stage_top = int(h * 0.15)
        stage_h = h - stage_top

        # Arrange sections (clusters) in arc rows
        section_w = w / max(len(roots), 1)
        for si, root in enumerate(roots):
            sx = si * section_w
            layout[root["id"]] = {
                "x": sx, "y": stage_top,
                "w": section_w, "h": stage_h,
            }

            # Chairs (nodes) within section
            children = [by_id[cid] for cid in (root.get("children") or []) if cid in by_id]
            if not children:
                continue

            chair_h = stage_h / max(len(children), 1)
            for ci, child in enumerate(children):
                cx = sx + 10
                cy = stage_top + ci * chair_h
                layout[child["id"]] = {
                    "x": cx, "y": cy + 5,
                    "w": section_w - 20, "h": chair_h - 10,
                }

                # Musicians (services) within chair
                grandchildren = [by_id[gcid] for gcid in (child.get("children") or []) if gcid in by_id]
                if not grandchildren:
                    continue

                musician_w = (section_w - 40) / max(len(grandchildren), 1)
                for mi, gc in enumerate(grandchildren):
                    mx = sx + 20 + mi * musician_w
                    my = cy + 10
                    cpu = (gc.get("metrics") or {}).get("cpu", 50)
                    max_mh = chair_h - 30
                    mh = max(15, max_mh * 0.6)  # musician height
                    volume_h = max(2, max_mh * 0.3 * (cpu / 100))  # volume bar

                    layout[gc["id"]] = {
                        "x": mx, "y": my,
                        "w": musician_w - 6, "h": mh,
                        "volume_h": volume_h,
                    }

        self._layout = layout
        return layout

    def _check_standing_ovation(self, entities: list[dict[str, Any]]) -> bool:
        """All services healthy = standing ovation."""
        services = [e for e in entities if e.get("type") == "service"]
        if not services:
            return False
        return all(e.get("state") in ("healthy", "running") for e in services)

    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        """Render the concert hall orchestra."""
        layout = self.compute_layout(entities, w, h)
        self._ovation = self._check_standing_ovation(entities)

        # === Backdrop: curtain ===
        ctx.fillStyle(CURTAIN_COLOR)
        ctx.fillRect(0, 0, w, int(h * 0.15))

        # Curtain folds
        fold_w = 30
        for fx in range(0, w, fold_w):
            ctx.fillStyle("#6B0000")
            ctx.fillRect(fx, 0, fold_w // 3, int(h * 0.15))

        # === Stage floor ===
        ctx.fillStyle(STAGE_WOOD)
        ctx.fillRect(0, int(h * 0.15), w, h - int(h * 0.15))

        # Wood grain lines
        ctx.strokeStyle("#2a1a0f")
        ctx.lineWidth(1)
        for gy in range(int(h * 0.15), h, 40):
            ctx.beginPath()
            ctx.moveTo(0, gy)
            ctx.lineTo(w, gy)
            ctx.stroke()

        # === Spotlights ===
        spot_count = max(3, w // 200)
        spot_spacing = w / (spot_count + 1)
        for i in range(spot_count):
            sx = spot_spacing * (i + 1)
            ctx.save()
            ctx.globalAlpha(0.08)
            ctx.fillStyle(SPOTLIGHT_COLOR)
            ctx.beginPath()
            ctx.moveTo(sx, 0)
            ctx.lineTo(sx - 60, h)
            ctx.lineTo(sx + 60, h)
            ctx.fill()
            ctx.restore()

        # === Render entities ===
        for entity in entities:
            pos = layout.get(entity["id"])
            if not pos:
                continue
            state = entity.get("state", "unknown")
            color = STATE_COLORS.get(state, STATE_COLORS["unknown"])
            etype = entity.get("type", "")

            if etype == "cluster":
                # Section boundary — warm outline
                section_name = entity.get("name", "").lower()
                section_color = SECTION_COLORS.get(section_name, SECTION_COLORS["default"])
                ctx.strokeStyle(section_color)
                ctx.lineWidth(2)
                ctx.strokeRect(pos["x"] + 2, pos["y"] + 2, pos["w"] - 4, pos["h"] - 4)
                # Section label
                ctx.fillStyle(section_color)
                ctx.font("bold 13px Georgia, serif")
                ctx.fillText(entity.get("name", ""), pos["x"] + 8, pos["y"] + 18)

            elif etype == "node":
                # Chair — subtle wood background
                ctx.fillStyle("#2a1a0f")
                ctx.fillRect(pos["x"], pos["y"], pos["w"], pos["h"])
                ctx.strokeStyle("#4a3520")
                ctx.lineWidth(1)
                ctx.strokeRect(pos["x"], pos["y"], pos["w"], pos["h"])
                # Chair label
                ctx.fillStyle("#9ca3af")
                ctx.font("11px Georgia, serif")
                ctx.fillText(entity.get("name", ""), pos["x"] + 6, pos["y"] + 14)

            elif etype == "service":
                # Musician figure (circle head + rect body)
                cx = pos["x"] + pos["w"] / 2
                head_r = min(pos["w"] * 0.2, 8)

                # Discordant flash for errors
                if state in ("critical", "degraded", "warning"):
                    ctx.fillStyle("#ef4444")
                    ctx.globalAlpha(0.3)
                    ctx.fillRect(pos["x"] - 2, pos["y"] - 2, pos["w"] + 4, pos["h"] + 4)
                    ctx.globalAlpha(1.0)

                # Head
                ctx.fillStyle(color)
                ctx.beginPath()
                ctx.arc(cx, pos["y"] + head_r, head_r, 0, 2 * math.pi)
                ctx.fill()

                # Body
                body_y = pos["y"] + head_r * 2 + 2
                body_h = pos["h"] - head_r * 2 - 2
                if body_h > 0:
                    ctx.fillStyle(color)
                    ctx.fillRect(pos["x"] + 2, body_y, pos["w"] - 4, body_h)

                # Volume bar (CPU)
                volume_h = pos.get("volume_h", 5)
                vol_y = pos["y"] + pos["h"] + 2
                ctx.fillStyle("#1a1a1a")
                ctx.fillRect(pos["x"] + 2, vol_y, pos["w"] - 4, 8)
                ctx.fillStyle(color)
                ctx.fillRect(pos["x"] + 2, vol_y, (pos["w"] - 4) * 0.8, volume_h)

                # Sound wave lines (flowing from musician)
                if state in ("healthy", "running"):
                    ctx.strokeStyle(SOUND_WAVE_COLOR)
                    ctx.lineWidth(1)
                    ctx.globalAlpha(0.4)
                    wave_x = pos["x"] + pos["w"]
                    for wi in range(3):
                        ctx.beginPath()
                        ctx.moveTo(wave_x + wi * 6, pos["y"] + pos["h"] / 2)
                        ctx.lineTo(wave_x + wi * 6 + 4, pos["y"] + pos["h"] / 2 - 3)
                        ctx.lineTo(wave_x + wi * 6 + 8, pos["y"] + pos["h"] / 2)
                        ctx.stroke()
                    ctx.globalAlpha(1.0)

                # Label
                if pos["w"] > 25:
                    ctx.fillStyle("#fff")
                    ctx.font("9px Georgia, serif")
                    ctx.fillText(entity.get("name", "")[:10], pos["x"] + 2, pos["y"] + pos["h"] + 22)

        # === Tempo indicator (top-right) ===
        if self.tempo_bpm > 0:
            ctx.fillStyle(SPOTLIGHT_COLOR)
            ctx.font("bold 12px Georgia, serif")
            ctx.fillText(f"♩ = {int(self.tempo_bpm)} BPM", w - 120, 20)

        # === Sheet music scroll (bottom) ===
        ctx.fillStyle("#f5f0e0")
        ctx.fillRect(0, h - 20, w, 20)
        # Staff lines
        ctx.strokeStyle("#333")
        ctx.lineWidth(0.5)
        for sl in range(5):
            ly = h - 18 + sl * 4
            ctx.beginPath()
            ctx.moveTo(0, ly)
            ctx.lineTo(w, ly)
            ctx.stroke()
        # Notes (active processes)
        active = [e for e in entities if e.get("state") in ("healthy", "running")]
        note_spacing = w / max(len(active) + 1, 2)
        for ni in range(min(len(active), 20)):
            nx = note_spacing * (ni + 1)
            ny = h - 10 + (ni % 5) * 3 - 6
            ctx.fillStyle("#333")
            ctx.beginPath()
            ctx.arc(nx, ny, 2.5, 0, 2 * math.pi)
            ctx.fill()
            # Stem
            ctx.beginPath()
            ctx.moveTo(nx + 2.5, ny)
            ctx.lineTo(nx + 2.5, ny - 10)
            ctx.stroke()

        # === Standing ovation ===
        if self._ovation:
            ctx.fillStyle(SPOTLIGHT_COLOR)
            ctx.globalAlpha(0.15)
            ctx.fillRect(0, 0, w, h)
            ctx.globalAlpha(1.0)
            ctx.fillStyle("#ffd700")
            ctx.font("bold 16px Georgia, serif")
            ctx.fillText("👏 Standing Ovation", w // 2 - 80, h // 2)

    def get_tooltip(self, entity: dict[str, Any], x: int, y: int) -> str | None:
        """Generate tooltip text for an entity."""
        etype = entity.get("type", "?")
        mapping = {"cluster": "Section", "node": "Chair", "service": "Musician", "container": "Instrument"}
        lines = [
            f"🎵 {entity.get('name', '?')} ({mapping.get(etype, etype)})",
            f"State: {entity.get('state', 'unknown')}",
        ]
        m = entity.get("metrics") or {}
        if "cpu" in m:
            lines.append(f"Volume: {m['cpu']}%")
        if "mem" in m:
            lines.append(f"Mem: {m['mem']}%")
        if "cpu_pct" in m:
            lines.append(f"Volume: {m['cpu_pct']}%")
        if "mem_pct" in m:
            lines.append(f"Mem: {m['mem_pct']}%")
        if "req_per_sec" in m:
            lines.append(f"Tempo: {m['req_per_sec']} BPM")
        if "error_rate" in m:
            lines.append(f"Discord: {m['error_rate'] * 100:.1f}%")
        if "count" in m:
            lines.append(f"Players: {m['count']}")
        if "uptime_hrs" in m:
            lines.append(f"Performance: {m['uptime_hrs']}h")
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
            "section_colors": SECTION_COLORS,
            "mappings": {
                "cluster": "section",
                "node": "chair",
                "service": "musician",
                "container": "instrument",
            },
        }
