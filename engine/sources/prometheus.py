"""Prometheus data source.

Queries a Prometheus server via HTTP API and maps metrics + alert states
to Entity objects. Supports:
  - Configurable URL via PROMETHEUS_URL env var
  - Node-level metrics: CPU usage, memory usage, load, filesystem
  - Alert state mapping: warning → WARNING, critical → CRITICAL, down → STOPPED
  - Cluster entity grouping all discovered nodes
"""
from __future__ import annotations

import os
import time
from typing import Any

import requests

from engine.entities import Entity, EntityType, EntityState
from .base import DataSource


class PrometheusSource(DataSource):
    """Fetches metrics from a Prometheus server and maps to entities."""

    name = "prometheus"

    def __init__(self, url: str | None = None):
        self.url = url or os.environ.get("PROMETHEUS_URL", "http://localhost:9090")
        self._alert_cache: dict[str, dict[str, str]] = {}  # instance → {alertname, severity}

    def is_available(self) -> bool:
        """Check connectivity by running a simple query."""
        try:
            resp = requests.get(
                f"{self.url}/api/v1/query",
                params={"query": "up"},
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def _query(self, promql: str) -> list[dict]:
        """Execute a PromQL instant query and return results."""
        try:
            resp = requests.get(
                f"{self.url}/api/v1/query",
                params={"query": promql},
                timeout=10,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            if data.get("status") != "success":
                return []
            return data.get("data", {}).get("result", [])
        except Exception:
            return []

    def _get_alerts(self) -> dict[str, dict[str, str]]:
        """Fetch active alerts and map instance → {alertname, severity}."""
        alerts: dict[str, dict[str, str]] = {}
        # Try ALERTS metric (recording rule) first
        results = self._query('ALERTS{state="firing"}')
        if not results:
            # Fallback: try prometheus_alerts API
            try:
                resp = requests.get(f"{self.url}/api/v1/alerts", timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    for alert in data.get("data", {}).get("alerts", []):
                        if alert.get("state") == "firing":
                            instance = alert.get("labels", {}).get("instance", "")
                            if instance:
                                alerts[instance] = {
                                    "alertname": alert.get("labels", {}).get("alertname", "unknown"),
                                    "severity": alert.get("labels", {}).get("severity", "warning"),
                                }
            except Exception:
                pass
        else:
            for r in results:
                labels = r.get("metric", {})
                instance = labels.get("instance", "")
                if instance:
                    alerts[instance] = {
                        "alertname": labels.get("alertname", "unknown"),
                        "severity": labels.get("severity", "warning"),
                    }
        self._alert_cache = alerts
        return alerts

    def _determine_node_state(self, instance: str, up_value: float) -> EntityState:
        """Map alert state + up metric to entity state."""
        if up_value == 0:
            return EntityState.CRITICAL
        alert = self._alert_cache.get(instance)
        if alert:
            severity = alert.get("severity", "warning")
            if severity == "critical":
                return EntityState.CRITICAL
            elif severity == "warning":
                return EntityState.WARNING
            elif severity == "info":
                return EntityState.DEGRADED
        if up_value == 1:
            return EntityState.HEALTHY
        return EntityState.UNKNOWN

    def fetch(self) -> list[Entity]:
        """Fetch all metrics and build entity tree."""
        entities: list[Entity] = []

        # 1. Fetch active alerts first (used for state mapping)
        self._get_alerts()

        # 2. Fetch 'up' metric → discovers instances
        up_results = self._query('up{job=~"node.*|prometheus.*|.*"}')
        if not up_results:
            return entities

        # Build cluster entity
        cluster_id = "prometheus-cluster"
        cluster = Entity(
            id=cluster_id,
            type=EntityType.CLUSTER,
            name="Prometheus Monitored",
            state=EntityState.HEALTHY,
            source=self.name,
            labels={"source": "prometheus"},
        )
        entities.append(cluster)

        # Collect per-instance data
        instance_data: dict[str, dict[str, Any]] = {}
        for r in up_results:
            labels = r.get("metric", {})
            instance = labels.get("instance", "")
            if not instance:
                continue
            up_val = float(r.get("value", [0, "0"])[1])
            instance_data[instance] = {
                "up": up_val,
                "job": labels.get("job", ""),
                "state": self._determine_node_state(instance, up_val),
            }

        # 3. CPU usage per instance
        cpu_results = self._query(
            '1 - avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m]))'
        )
        for r in cpu_results:
            inst = r.get("metric", {}).get("instance", "")
            if inst in instance_data:
                instance_data[inst]["cpu_pct"] = round(float(r.get("value", [0, "0"])[1]) * 100, 2)

        # 4. Memory usage per instance
        mem_total = self._query("node_memory_MemTotal_bytes")
        mem_avail = self._query("node_memory_MemAvailable_bytes")
        mem_totals = {r["metric"]["instance"]: float(r["value"][1]) for r in mem_total if "instance" in r.get("metric", {})}
        mem_avails = {r["metric"]["instance"]: float(r["value"][1]) for r in mem_avail if "instance" in r.get("metric", {})}
        for inst, total in mem_totals.items():
            if inst in instance_data and total > 0:
                avail = mem_avails.get(inst, 0)
                used_pct = round((1 - avail / total) * 100, 2)
                instance_data[inst]["mem_total_bytes"] = int(total)
                instance_data[inst]["mem_pct"] = used_pct

        # 5. Load average
        load_results = self._query("node_load1")
        for r in load_results:
            inst = r.get("metric", {}).get("instance", "")
            if inst in instance_data:
                instance_data[inst]["load1"] = round(float(r.get("value", [0, "0"])[1]), 2)

        # 6. Filesystem available
        fs_results = self._query('node_filesystem_avail_bytes{mountpoint="/"}')
        for r in fs_results:
            inst = r.get("metric", {}).get("instance", "")
            if inst in instance_data:
                instance_data[inst]["fs_avail_bytes"] = int(float(r.get("value", [0, "0"])[1]))

        # 7. Build node entities
        any_critical = False
        any_warning = False
        for inst, data in instance_data.items():
            node_id = f"prom-node-{inst.replace(':', '-').replace('.', '-')}"
            state = data.get("state", EntityState.UNKNOWN)
            if state == EntityState.CRITICAL:
                any_critical = True
            elif state == EntityState.WARNING:
                any_warning = True

            metrics = {
                "cpu_pct": data.get("cpu_pct", 0.0),
                "mem_pct": data.get("mem_pct", 0.0),
                "load1": data.get("load1", 0.0),
                "up": data.get("up", 0),
            }
            if "mem_total_bytes" in data:
                metrics["mem_total_bytes"] = data["mem_total_bytes"]
            if "fs_avail_bytes" in data:
                metrics["fs_avail_bytes"] = data["fs_avail_bytes"]

            alert_info = self._alert_cache.get(inst)
            annotations = {}
            if alert_info:
                annotations["alert"] = alert_info["alertname"]
                annotations["severity"] = alert_info["severity"]

            node = Entity(
                id=node_id,
                type=EntityType.NODE,
                name=inst,
                state=state,
                parent=cluster_id,
                source=self.name,
                metrics=metrics,
                labels={"instance": inst, "job": data.get("job", "")},
                annotations=annotations,
            )
            cluster.children.append(node_id)
            entities.append(node)

        # Update cluster state based on children
        if any_critical:
            cluster.state = EntityState.DEGRADED
        elif any_warning:
            cluster.state = EntityState.WARNING

        return entities
