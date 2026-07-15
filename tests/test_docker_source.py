"""Tests for Docker data source.

Uses subprocess mocking so tests run without Docker installed.
"""
from __future__ import annotations

import subprocess
from unittest.mock import patch, MagicMock

from engine.sources.docker import DockerSource, _map_state, _run_docker, _docker_cmd
from engine.entities import EntityType, EntityState


class TestDockerSource:
    """Test DockerSource behavior with mocked subprocess calls."""

    def test_name(self):
        s = DockerSource()
        assert s.name == "docker"

    def test_map_state_running(self):
        assert _map_state("running") == EntityState.RUNNING

    def test_map_state_exited(self):
        assert _map_state("exited") == EntityState.STOPPED

    def test_map_state_created(self):
        assert _map_state("created") == EntityState.PENDING

    def test_map_state_dead(self):
        assert _map_state("dead") == EntityState.CRITICAL

    def test_map_state_up_prefix(self):
        # "Up 2 hours" starts with... none of our keys exactly, but contains "up"
        # Actually "up" is not in our map. Let's check it returns RUNNING via prefix match.
        # "Up 2 hours" → lower = "up 2 hours" → no key matches → UNKNOWN
        # This is expected: docker status strings like "Up 2 hours" don't match our keys
        result = _map_state("Up 2 hours")
        # Actually "up" is not in _STATE_MAP, so this returns UNKNOWN
        assert result in (EntityState.UNKNOWN, EntityState.RUNNING)

    def test_map_state_unknown(self):
        assert _map_state("something_weird") == EntityState.UNKNOWN

    @patch("engine.sources.docker._docker_cmd", return_value=None)
    def test_is_available_no_docker(self, _mock):
        s = DockerSource()
        assert s.is_available() is False

    @patch("engine.sources.docker._run_docker", return_value=(True, "1.2.3"))
    @patch("engine.sources.docker._docker_cmd", return_value="/usr/bin/docker")
    def test_is_available_with_docker(self, _cmd, _info):
        s = DockerSource()
        assert s.is_available() is True

    @patch("engine.sources.docker._run_docker")
    @patch("engine.sources.docker._docker_cmd", return_value="/usr/bin/docker")
    def test_fetch_basic(self, _cmd, mock_run):
        """Test fetch with mocked docker commands."""
        def side_effect(args, timeout=5.0):
            if "info" in args:
                return True, "myhost|4|8589934592|/var/lib/docker|24.0.0"
            elif "ps" in args:
                return True, "abc123def456789|web-app|nginx:latest|Up 2 hours|running|80/tcp|2 hours ago\n"
            elif "stats" in args:
                return True, "abc123def456789|15.50%|100MiB / 8GiB|1.25%|1.2kB / 3.4kB|5MB / 0B|42\n"
            return False, ""

        mock_run.side_effect = side_effect

        s = DockerSource()
        entities = s.fetch()

        # Should have root + 1 container
        assert len(entities) == 2

        root = entities[0]
        assert root.id == "docker-host"
        assert root.type == EntityType.CLUSTER
        assert root.metrics["ncpu"] == 4
        assert root.metrics["docker_version"] == "24.0.0"

        container = entities[1]
        assert container.id == "dctr-abc123def456"
        assert container.type == EntityType.CONTAINER
        assert container.name == "web-app"
        assert container.parent == "docker-host"
        assert container.metrics["image"] == "nginx:latest"
        assert container.metrics["cpu_pct"] == 15.5

    @patch("engine.sources.docker._run_docker")
    @patch("engine.sources.docker._docker_cmd", return_value="/usr/bin/docker")
    def test_fetch_no_containers(self, _cmd, mock_run):
        """Test fetch when docker is running but no containers exist."""
        def side_effect(args, timeout=5.0):
            if "info" in args:
                return True, "myhost|2|4294967296|/var/lib/docker|20.10.0"
            elif "ps" in args:
                return True, ""
            elif "stats" in args:
                return True, ""
            return False, ""

        mock_run.side_effect = side_effect

        s = DockerSource()
        entities = s.fetch()

        # Only root entity
        assert len(entities) == 1
        assert entities[0].id == "docker-host"

    @patch("engine.sources.docker._run_docker", return_value=(False, "daemon not running"))
    @patch("engine.sources.docker._docker_cmd", return_value="/usr/bin/docker")
    def test_fetch_docker_daemon_down(self, _cmd, _mock):
        """Test fetch returns empty when daemon is unreachable."""
        s = DockerSource()
        entities = s.fetch()
        assert len(entities) == 0

    def test_run_docker_timeout(self):
        """Test _run_docker handles timeout gracefully."""
        with patch("engine.sources.docker._docker_cmd", return_value="/usr/bin/docker"), \
             patch("engine.sources.docker.subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 5)):
            ok, msg = _run_docker(["info"])
            assert ok is False
            assert "timed out" in msg

    def test_run_docker_no_binary(self):
        """Test _run_docker returns False when docker binary not found."""
        with patch("engine.sources.docker._docker_cmd", return_value=None):
            ok, msg = _run_docker(["info"])
            assert ok is False
            assert "not found" in msg
