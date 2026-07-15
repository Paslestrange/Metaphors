"""Docker data source — lists running containers, CPU/memory stats, state changes.

Each container becomes a CONTAINER entity. A CLUSTER entity serves as the
Docker host root. Uses `docker` CLI via subprocess (no pip dependency).

Falls back gracefully when Docker is not installed or not running.
"""
from __future__ import annotations

import json
import subprocess
import shutil

from engine.entities import Entity, EntityType, EntityState
from .base import DataSource


def _docker_cmd() -> str | None:
    """Return path to docker binary, or None if not found."""
    return shutil.which("docker")


def _run_docker(args: list[str], timeout: float = 5.0) -> tuple[bool, str]:
    """Run a docker CLI command. Returns (success, stdout_or_stderr)."""
    docker = _docker_cmd()
    if docker is None:
        return False, "docker binary not found"
    try:
        result = subprocess.run(
            [docker] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return False, result.stderr.strip()
        return True, result.stdout
    except subprocess.TimeoutExpired:
        return False, "docker command timed out"
    except Exception as e:
        return False, str(e)


# Map Docker container status strings to EntityState
_STATE_MAP = {
    "running": EntityState.RUNNING,
    "created": EntityState.PENDING,
    "restarting": EntityState.SCALING,
    "paused": EntityState.IDLE,
    "exited": EntityState.STOPPED,
    "dead": EntityState.CRITICAL,
    "removing": EntityState.WARNING,
}


def _map_state(status: str) -> EntityState:
    """Map a docker status string (e.g. 'Up 2 hours', 'Exited (0)') to EntityState."""
    lower = status.lower()
    for key, state in _STATE_MAP.items():
        if lower.startswith(key):
            return state
    return EntityState.UNKNOWN


class DockerSource(DataSource):
    """Reads live container data from the local Docker daemon."""

    name = "docker"

    def is_available(self) -> bool:
        """Check if docker CLI exists and daemon responds."""
        if _docker_cmd() is None:
            return False
        ok, _ = _run_docker(["info", "--format", "{{.ServerVersion}}"], timeout=3.0)
        return ok

    def fetch(self) -> list[Entity]:
        entities: list[Entity] = []

        # 1. Get host info for root cluster entity
        ok, host_info = _run_docker(["info", "--format",
            "{{.Name}}|{{.NCPU}}|{{.MemTotal}}|{{.DockerRootDir}}|{{.ServerVersion}}"])
        if not ok:
            return entities

        parts = host_info.strip().split("|")
        if len(parts) < 5:
            return entities

        hostname, ncpu, mem_total_raw, root_dir, version = parts
        try:
            mem_total_mb = int(int(mem_total_raw) / (1024 * 1024))
        except (ValueError, TypeError):
            mem_total_mb = 0

        root = Entity(
            id="docker-host",
            type=EntityType.CLUSTER,
            name=f"Docker — {hostname}",
            state=EntityState.HEALTHY,
            source=self.name,
            metrics={
                "ncpu": int(ncpu) if ncpu.isdigit() else 0,
                "mem_total_mb": mem_total_mb,
                "docker_version": version,
                "root_dir": root_dir,
            },
            labels={"hostname": hostname, "source": "docker"},
        )
        entities.append(root)

        # 2. List all containers (including stopped) with basic info
        ok, ps_out = _run_docker([
            "ps", "-a", "--no-trunc",
            "--format", "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.State}}|{{.Ports}}|{{.RunningFor}}"
        ])
        if not ok:
            return [root]

        containers_raw = ps_out.strip().split("\n") if ps_out.strip() else []

        # 3. Get stats for running containers (non-streaming, single snapshot)
        stats: dict[str, dict] = {}
        ok_stats, stats_out = _run_docker([
            "stats", "--no-stream", "--no-trunc",
            "--format", "{{.Container}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}|{{.NetIO}}|{{.BlockIO}}|{{.PIDs}}"
        ], timeout=10.0)

        if ok_stats and stats_out.strip():
            for line in stats_out.strip().split("\n"):
                parts = line.split("|")
                if len(parts) >= 7:
                    cid = parts[0].strip()
                    try:
                        cpu_pct = float(parts[1].replace("%", ""))
                        mem_pct = float(parts[3].replace("%", ""))
                    except (ValueError, IndexError):
                        cpu_pct, mem_pct = 0.0, 0.0
                    stats[cid] = {
                        "cpu_pct": round(cpu_pct, 2),
                        "mem_pct": round(mem_pct, 2),
                        "mem_usage": parts[2].strip(),
                        "net_io": parts[4].strip(),
                        "block_io": parts[5].strip(),
                        "pids": parts[6].strip(),
                    }

        # 4. Build entities from container list
        for line in containers_raw:
            if not line.strip():
                continue
            parts = line.split("|")
            if len(parts) < 7:
                continue

            full_id, name, image, status, state_str, ports, running_for = parts

            container_state = _map_state(state_str)
            short_id = full_id[:12]

            # Determine health: high CPU or critical state
            if container_state == EntityState.CRITICAL:
                health = EntityState.CRITICAL
            elif container_state == EntityState.STOPPED:
                health = EntityState.STOPPED
            else:
                container_stats = stats.get(full_id, stats.get(short_id, {}))
                cpu = container_stats.get("cpu_pct", 0.0)
                if cpu > 80:
                    health = EntityState.WARNING
                elif cpu > 0:
                    health = EntityState.RUNNING
                else:
                    health = container_state if container_state != EntityState.UNKNOWN else EntityState.RUNNING

            # Build container entity
            container_stats = stats.get(full_id, stats.get(short_id, {}))
            entity = Entity(
                id=f"dctr-{short_id}",
                type=EntityType.CONTAINER,
                name=name,
                state=health,
                parent=root.id,
                source=self.name,
                metrics={
                    "image": image,
                    "status": status,
                    "uptime": running_for,
                    "cpu_pct": container_stats.get("cpu_pct", 0.0),
                    "mem_pct": container_stats.get("mem_pct", 0.0),
                    "mem_usage": container_stats.get("mem_usage", "N/A"),
                    "net_io": container_stats.get("net_io", "N/A"),
                    "block_io": container_stats.get("block_io", "N/A"),
                    "pids": container_stats.get("pids", "0"),
                },
                labels={
                    "container_id": short_id,
                    "image": image,
                    "ports": ports or "none",
                },
            )
            root.children.append(entity.id)
            entities.append(entity)

        return entities
