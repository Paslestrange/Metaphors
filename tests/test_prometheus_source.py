"""Tests for Prometheus data source.

The PrometheusSource queries a Prometheus server via HTTP API and maps
metrics + alerts to Entity objects. Tests use mocked HTTP responses
to avoid requiring a live Prometheus instance.
"""
from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock

from engine.entities import Entity, EntityType, EntityState
from engine.sources.prometheus import PrometheusSource


class TestPrometheusSourceAvailability(unittest.TestCase):
    """Test is_available() connectivity check."""

    def test_available_when_up_query_succeeds(self):
        source = PrometheusSource(url="http://prometheus:9090")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"resultType": "vector", "result": [{"metric": {}, "value": [1, "1"]}]}
        }
        with patch("engine.sources.prometheus.requests.get", return_value=mock_response):
            self.assertTrue(source.is_available())

    def test_unavailable_when_connection_fails(self):
        source = PrometheusSource(url="http://prometheus:9090")
        with patch("engine.sources.prometheus.requests.get", side_effect=Exception("Connection refused")):
            self.assertFalse(source.is_available())

    def test_unavailable_on_non_200(self):
        source = PrometheusSource(url="http://prometheus:9090")
        mock_response = MagicMock()
        mock_response.status_code = 503
        with patch("engine.sources.prometheus.requests.get", return_value=mock_response):
            self.assertFalse(source.is_available())


class TestPrometheusSourceFetch(unittest.TestCase):
    """Test fetch() entity generation from Prometheus queries."""

    def _mock_query_side_effect(self, url, **kwargs):
        """Return different responses based on the query param."""
        resp = MagicMock()
        resp.status_code = 200
        params = kwargs.get("params", {})
        query = params.get("query", "")

        if "up{" in query or query.startswith("up"):
            resp.json.return_value = {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {"metric": {"__name__": "up", "instance": "node1:9100", "job": "node"}, "value": [1, "1"]},
                        {"metric": {"__name__": "up", "instance": "node2:9100", "job": "node"}, "value": [1, "1"]},
                        {"metric": {"__name__": "up", "instance": "node3:9100", "job": "node"}, "value": [1, "0"]},
                    ]
                }
            }
        elif "rate(node_cpu" in query:
            resp.json.return_value = {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {"metric": {"instance": "node1:9100"}, "value": [1, "0.45"]},
                        {"metric": {"instance": "node2:9100"}, "value": [1, "0.72"]},
                        {"metric": {"instance": "node3:9100"}, "value": [1, "0.15"]},
                    ]
                }
            }
        elif "node_memory" in query and "MemTotal" in query:
            resp.json.return_value = {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {"metric": {"instance": "node1:9100"}, "value": [1, "16000000000"]},
                        {"metric": {"instance": "node2:9100"}, "value": [1, "32000000000"]},
                        {"metric": {"instance": "node3:9100"}, "value": [1, "16000000000"]},
                    ]
                }
            }
        elif "node_memory" in query and "MemAvailable" in query:
            resp.json.return_value = {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {"metric": {"instance": "node1:9100"}, "value": [1, "8000000000"]},
                        {"metric": {"instance": "node2:9100"}, "value": [1, "16000000000"]},
                        {"metric": {"instance": "node3:9100"}, "value": [1, "12000000000"]},
                    ]
                }
            }
        elif "node_load1" in query:
            resp.json.return_value = {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {"metric": {"instance": "node1:9100"}, "value": [1, "2.5"]},
                        {"metric": {"instance": "node2:9100"}, "value": [1, "4.1"]},
                        {"metric": {"instance": "node3:9100"}, "value": [1, "0.8"]},
                    ]
                }
            }
        elif "node_filesystem_avail" in query:
            resp.json.return_value = {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {"metric": {"instance": "node1:9100", "mountpoint": "/"}, "value": [1, "50000000000"]},
                        {"metric": {"instance": "node2:9100", "mountpoint": "/"}, "value": [1, "100000000000"]},
                        {"metric": {"instance": "node3:9100", "mountpoint": "/"}, "value": [1, "80000000000"]},
                    ]
                }
            }
        elif "ALERTS" in query or "alerts" in query:
            resp.json.return_value = {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {
                            "metric": {
                                "alertname": "HighCPU",
                                "severity": "warning",
                                "instance": "node2:9100"
                            },
                            "value": [1, "1"]
                        },
                        {
                            "metric": {
                                "alertname": "NodeDown",
                                "severity": "critical",
                                "instance": "node3:9100"
                            },
                            "value": [1, "1"]
                        }
                    ]
                }
            }
        else:
            resp.json.return_value = {"status": "success", "data": {"resultType": "vector", "result": []}}
        return resp

    def test_fetch_returns_entities(self):
        source = PrometheusSource(url="http://prometheus:9090")
        with patch("engine.sources.prometheus.requests.get") as mock_get:
            mock_get.side_effect = self._mock_query_side_effect
            entities = source.fetch()
        self.assertIsInstance(entities, list)
        self.assertGreater(len(entities), 0)

    def test_fetch_creates_cluster_entity(self):
        source = PrometheusSource(url="http://prometheus:9090")
        with patch("engine.sources.prometheus.requests.get") as mock_get:
            mock_get.side_effect = self._mock_query_side_effect
            entities = source.fetch()
        clusters = [e for e in entities if e.type == EntityType.CLUSTER]
        self.assertEqual(len(clusters), 1)
        self.assertIn("prometheus", clusters[0].id.lower())

    def test_fetch_creates_node_entities_per_instance(self):
        source = PrometheusSource(url="http://prometheus:9090")
        with patch("engine.sources.prometheus.requests.get") as mock_get:
            mock_get.side_effect = self._mock_query_side_effect
            entities = source.fetch()
        nodes = [e for e in entities if e.type == EntityType.NODE]
        # We have 3 instances in mock data
        self.assertEqual(len(nodes), 3)

    def test_node_has_cpu_and_mem_metrics(self):
        source = PrometheusSource(url="http://prometheus:9090")
        with patch("engine.sources.prometheus.requests.get") as mock_get:
            mock_get.side_effect = self._mock_query_side_effect
            entities = source.fetch()
        nodes = [e for e in entities if e.type == EntityType.NODE]
        for node in nodes:
            self.assertIn("cpu_pct", node.metrics)
            self.assertIn("mem_pct", node.metrics)
            self.assertIsInstance(node.metrics["cpu_pct"], float)
            self.assertIsInstance(node.metrics["mem_pct"], float)

    def test_node_state_reflects_alerts(self):
        """Alert states should map to entity states."""
        source = PrometheusSource(url="http://prometheus:9090")
        with patch("engine.sources.prometheus.requests.get") as mock_get:
            mock_get.side_effect = self._mock_query_side_effect
            entities = source.fetch()
        nodes = {e.name: e for e in entities if e.type == EntityType.NODE}
        # node2 has warning alert → WARNING
        self.assertEqual(nodes.get("node2:9100", nodes.get("node2")).state, EntityState.WARNING)
        # node3 has critical alert → CRITICAL
        self.assertEqual(nodes.get("node3:9100", nodes.get("node3")).state, EntityState.CRITICAL)
        # node1 has no alert → HEALTHY (since up=1)
        node1 = nodes.get("node1:9100", nodes.get("node1"))
        self.assertIn(node1.state, [EntityState.HEALTHY, EntityState.RUNNING])

    def test_fetch_handles_empty_prometheus(self):
        """When Prometheus has no data, return at least an empty list (not crash)."""
        source = PrometheusSource(url="http://prometheus:9090")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "success", "data": {"resultType": "vector", "result": []}}
        with patch("engine.sources.prometheus.requests.get", return_value=mock_resp):
            entities = source.fetch()
        self.assertIsInstance(entities, list)

    def test_fetch_down_instance_marked_stopped(self):
        """Instances with up=0 should be marked STOPPED/CRITICAL."""
        source = PrometheusSource(url="http://prometheus:9090")
        with patch("engine.sources.prometheus.requests.get") as mock_get:
            mock_get.side_effect = self._mock_query_side_effect
            entities = source.fetch()
        nodes = {e.name: e for e in entities if e.type == EntityType.NODE}
        # node3 has up=0 → should be critical/stopped
        node3 = nodes.get("node3:9100", nodes.get("node3"))
        self.assertIn(node3.state, [EntityState.CRITICAL, EntityState.STOPPED])

    def test_source_label_set_on_all_entities(self):
        source = PrometheusSource(url="http://prometheus:9090")
        with patch("engine.sources.prometheus.requests.get") as mock_get:
            mock_get.side_effect = self._mock_query_side_effect
            entities = source.fetch()
        for e in entities:
            self.assertEqual(e.source, "prometheus")


class TestPrometheusSourceConfig(unittest.TestCase):
    """Test configuration from env vars."""

    @patch.dict("os.environ", {"PROMETHEUS_URL": "http://custom:9090"})
    def test_url_from_env(self):
        source = PrometheusSource()
        self.assertEqual(source.url, "http://custom:9090")

    def test_url_default(self):
        with patch.dict("os.environ", {}, clear=False):
            source = PrometheusSource()
            # Should default to localhost:9090
            self.assertIn("9090", source.url)

    def test_explicit_url_overrides_env(self):
        source = PrometheusSource(url="http://explicit:9090")
        self.assertEqual(source.url, "http://explicit:9090")


if __name__ == "__main__":
    unittest.main()
