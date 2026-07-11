"""System process data source — groups processes by name using psutil."""
from __future__ import annotations
import socket
from collections import defaultdict
import psutil
from engine.entities import Entity, EntityType, EntityState
from engine.sources.base import DataSource


class ProcessSource(DataSource):
    """Reads live system processes via psutil, groups by name, returns top 30 by CPU."""

    name = "processes"

    def is_available(self) -> bool:
        try:
            import psutil  # noqa: F401
            return True
        except ImportError:
            return False

    def fetch(self) -> list[Entity]:
        # Group processes by name
        groups: dict[str, dict] = defaultdict(lambda: {"cpu": 0.0, "mem": 0.0, "pids": []})

        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                name = proc.name()
                if not name:
                    continue
                cpu = proc.cpu_percent() or 0.0
                mem = proc.memory_percent() or 0.0
                pid = proc.pid
                groups[name]["cpu"] += cpu
                groups[name]["mem"] += mem
                groups[name]["pids"].append(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                continue

        # Sort by CPU descending, take top 30
        sorted_groups = sorted(groups.items(), key=lambda x: x[1]["cpu"], reverse=True)[:30]

        # Build root entity
        hostname = socket.gethostname()
        root = Entity(
            id="host-processes",
            type=EntityType.CLUSTER,
            name=f"System — {hostname}",
            state=EntityState.HEALTHY,
            source=self.name,
        )

        entities: list[Entity] = [root]

        for name, data in sorted_groups:
            count = len(data["pids"])
            # State based on CPU intensity
            if data["cpu"] > 80:
                state = EntityState.CRITICAL
            elif data["cpu"] > 50:
                state = EntityState.WARNING
            elif data["cpu"] > 10:
                state = EntityState.RUNNING
            else:
                state = EntityState.IDLE

            proc_entity = Entity(
                id=f"proc-{name}",
                type=EntityType.PROCESS,
                name=name,
                state=state,
                parent=root.id,
                source=self.name,
                metrics={
                    "cpu_pct": round(data["cpu"], 1),
                    "mem_pct": round(data["mem"], 1),
                    "count": count,
                    "pids": sorted(data["pids"]),
                },
            )
            root.children.append(proc_entity.id)
            entities.append(proc_entity)

        return entities
