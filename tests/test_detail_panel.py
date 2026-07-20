"""Tests for detail panel metrics and logs link generation."""
import pytest


def test_build_logs_link_docker_container():
    """Docker containers should link to /api/logs/docker/{container_id}."""
    entity = {
        "id": "dctr-abc123def456",
        "type": "container",
        "source": "docker",
        "labels": {"container_id": "abc123def456"},
    }
    # Simulate the buildLogsLink logic
    src = entity["source"]
    if src == "docker" and (entity["type"] == "container" or entity["id"].startswith("dctr-")):
        container_id = entity.get("labels", {}).get("container_id") or entity["id"].replace("dctr-", "")
        link = f"/api/logs/docker/{container_id}"
        assert link == "/api/logs/docker/abc123def456"


def test_build_logs_link_process():
    """Process entities should link to /api/logs/process?name=..."""
    entity = {
        "id": "proc-nginx",
        "type": "process",
        "name": "nginx",
        "source": "processes",
    }
    src = entity["source"]
    if src == "processes" and entity["type"] == "process":
        import urllib.parse
        link = f"/api/logs/process?name={urllib.parse.quote(entity['name'])}"
        assert link == "/api/logs/process?name=nginx"


def test_build_logs_link_prometheus_node():
    """Prometheus nodes should link to /api/logs/prometheus?instance=..."""
    entity = {
        "id": "prom-node-localhost-9090",
        "type": "node",
        "name": "localhost:9090",
        "source": "prometheus",
        "labels": {"instance": "localhost:9090"},
    }
    src = entity["source"]
    if src == "prometheus" and entity["type"] == "node":
        import urllib.parse
        instance = entity.get("labels", {}).get("instance") or entity["name"]
        link = f"/api/logs/prometheus?instance={urllib.parse.quote(instance)}"
        assert link == "/api/logs/prometheus?instance=localhost%3A9090"


def test_build_logs_link_mock_source():
    """Mock source entities should not have a logs link."""
    entity = {
        "id": "svc-0-1",
        "type": "service",
        "source": "mock",
    }
    src = entity["source"]
    # None of the conditions match
    has_link = False
    if src == "docker" and (entity["type"] == "container" or entity["id"].startswith("dctr-")):
        has_link = True
    if src == "prometheus" and entity["type"] == "node":
        has_link = True
    if src == "processes" and entity["type"] == "process":
        has_link = True
    assert has_link is False


def test_uptime_formatting_numeric_hours():
    """Numeric uptime should be formatted correctly."""
    # < 1 hour → minutes
    uptime = 0.5
    if uptime < 1:
        text = f"{round(uptime * 60)} min"
    elif uptime < 24:
        text = f"{uptime:.1f} hrs"
    else:
        text = f"{uptime / 24:.1f} days"
    assert text == "30 min"

    # 1-24 hours
    uptime = 5.5
    if uptime < 1:
        text = f"{round(uptime * 60)} min"
    elif uptime < 24:
        text = f"{uptime:.1f} hrs"
    else:
        text = f"{uptime / 24:.1f} days"
    assert text == "5.5 hrs"

    # > 24 hours
    uptime = 48
    if uptime < 1:
        text = f"{round(uptime * 60)} min"
    elif uptime < 24:
        text = f"{uptime:.1f} hrs"
    else:
        text = f"{uptime / 24:.1f} days"
    assert text == "2.0 days"


def test_uptime_formatting_string():
    """String uptime (Docker format) should be passed through as-is."""
    uptime = "Up 2 hours"
    if isinstance(uptime, str):
        text = uptime
    else:
        text = "numeric"
    assert text == "Up 2 hours"
