"""Process data source using psutil.

Groups running processes by name, reports top 30 by CPU usage.
Each group becomes a PROCESS entity with aggregated metrics.
A CLUSTER entity serves as the system-level root.
"""
from __future__ import annotations

import socket

import psutil

from engine.entities import Entity, EntityType, EntityState
from .base import DataSource


class ProcessSource(DataSource):
    """Reads live process data from the local system via psutil."""

    name = "processes"

    def is_available(self) -> bool:
        return True

    def fetch(self) -> list[Entity]:
        entities: list[Entity] = []

        # Gather processes, group by name using .info dict (batch mode)
        groups: dict[str, dict] = {}

        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = proc.info
                name = info.get("name") or f"pid-{info['pid']}"
                cpu = info.get("cpu_percent") or 0.0
                mem_pct = info.get("memory_percent") or 0.0
                pid = info["pid"]

                if name not in groups:
                    groups[name] = {"pids": [], "cpu_pct": 0.0, "mem_pct": 0.0}
                groups[name]["pids"].append(pid)
                groups[name]["cpu_pct"] += cpu
                groups[name]["mem_pct"] += mem_pct
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                continue

        # Sort by cpu_pct descending, take top 30
        sorted_groups = sorted(
            groups.items(), key=lambda x: x[1]["cpu_pct"], reverse=True
        )[:30]

        # Root: system overview (cluster)
        hostname = socket.gethostname()
        root = Entity(
            id="host-processes",
            type=EntityType.CLUSTER,
            name=f"System — {hostname}",
            state=EntityState.HEALTHY,
            source=self.name,
            metrics={
                "cpu_count": psutil.cpu_count() or 1,
                "mem_total_mb": round(psutil.virtual_memory().total / (1024 * 1024)),
                "mem_used_pct": psutil.virtual_memory().percent,
            },
            labels={"hostname": hostname},
        )
        entities.append(root)

        for name, data in sorted_groups:
            proc_id = f"proc-{name}"
            if data["cpu_pct"] > 80:
                state = EntityState.WARNING
            elif data["cpu_pct"] > 0:
                state = EntityState.RUNNING
            else:
                state = EntityState.IDLE

            entity = Entity(
                id=proc_id,
                type=EntityType.PROCESS,
                name=name,
                state=state,
                parent=root.id,
                source=self.name,
                metrics={
                    "cpu_pct": round(data["cpu_pct"], 2),
                    "mem_pct": round(data["mem_pct"], 2),
                    "count": len(data["pids"]),
                    "pids": sorted(data["pids"]),
                },
            )
            root.children.append(proc_id)
            entities.append(entity)

        return entities
