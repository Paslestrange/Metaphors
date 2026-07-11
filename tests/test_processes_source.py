"""Tests for ProcessSource — real system process data via psutil.

TDD: tests define the contract before implementation.
"""
import pytest
import psutil
from unittest.mock import patch, MagicMock

from engine.entities import EntityType, EntityState
from engine.sources.processes import ProcessSource


class TestProcessSourceAvailability:
    """is_available() checks psutil importability."""

    def test_available_when_psutil_importable(self):
        source = ProcessSource()
        assert source.is_available() is True

    def test_name_is_processes(self):
        source = ProcessSource()
        assert source.name == "processes"


class TestProcessSourceFetch:
    """fetch() returns entities representing system processes."""

    def test_returns_list_of_entities(self):
        source = ProcessSource()
        entities = source.fetch()
        assert isinstance(entities, list)
        assert len(entities) > 0

    def test_root_entity_is_cluster_type(self):
        source = ProcessSource()
        entities = source.fetch()
        root = [e for e in entities if e.parent is None]
        assert len(root) == 1
        assert root[0].type == EntityType.CLUSTER

    def test_root_entity_has_system_overview_name(self):
        source = ProcessSource()
        entities = source.fetch()
        root = [e for e in entities if e.parent is None][0]
        assert "system" in root.name.lower() or "host" in root.name.lower()

    def test_process_entities_are_process_type(self):
        source = ProcessSource()
        entities = source.fetch()
        processes = [e for e in entities if e.parent is not None]
        assert len(processes) > 0
        assert all(e.type == EntityType.PROCESS for e in processes)

    def test_process_entities_have_required_metrics(self):
        source = ProcessSource()
        entities = source.fetch()
        processes = [e for e in entities if e.parent is not None]
        for proc in processes:
            assert "cpu_pct" in proc.metrics, f"Missing cpu_pct in {proc.name}"
            assert "mem_pct" in proc.metrics, f"Missing mem_pct in {proc.name}"
            assert "count" in proc.metrics, f"Missing count in {proc.name}"
            assert "pids" in proc.metrics, f"Missing pids in {proc.name}"

    def test_process_metrics_are_numeric(self):
        source = ProcessSource()
        entities = source.fetch()
        processes = [e for e in entities if e.parent is not None]
        for proc in processes:
            assert isinstance(proc.metrics["cpu_pct"], (int, float))
            assert isinstance(proc.metrics["mem_pct"], (int, float))
            assert isinstance(proc.metrics["count"], int)
            assert isinstance(proc.metrics["pids"], list)

    def test_max_30_process_groups(self):
        source = ProcessSource()
        entities = source.fetch()
        processes = [e for e in entities if e.parent is not None]
        assert len(processes) <= 30

    def test_root_children_references(self):
        source = ProcessSource()
        entities = source.fetch()
        root = [e for e in entities if e.parent is None][0]
        processes = [e for e in entities if e.parent is not None]
        process_ids = {e.id for e in processes}
        for child_id in root.children:
            assert child_id in process_ids

    def test_pids_are_nonempty(self):
        source = ProcessSource()
        entities = source.fetch()
        processes = [e for e in entities if e.parent is not None]
        for proc in processes:
            assert len(proc.metrics["pids"]) >= 1

    def test_count_matches_pids_length(self):
        source = ProcessSource()
        entities = source.fetch()
        processes = [e for e in entities if e.parent is not None]
        for proc in processes:
            assert proc.metrics["count"] == len(proc.metrics["pids"])

    def test_source_field_set(self):
        source = ProcessSource()
        entities = source.fetch()
        assert all(e.source == "processes" for e in entities)

    def test_processes_sorted_by_cpu_desc(self):
        source = ProcessSource()
        entities = source.fetch()
        processes = [e for e in entities if e.parent is not None]
        cpus = [p.metrics["cpu_pct"] for p in processes]
        assert cpus == sorted(cpus, reverse=True)


class TestProcessSourceMocked:
    """Test grouping logic with mocked psutil data."""

    def _make_mock_procs(self):
        """Create mock process objects for deterministic testing.
        
        process_iter(attrs=[...]) returns objects with .info dict.
        """
        procs = []
        # 3 python processes
        for pid in [100, 200, 300]:
            p = MagicMock()
            p.info = {
                "pid": pid,
                "name": "python3",
                "cpu_percent": 10.0,
                "memory_percent": 2.5,
            }
            procs.append(p)
        # 1 nginx process
        p = MagicMock()
        p.info = {
            "pid": 400,
            "name": "nginx",
            "cpu_percent": 50.0,
            "memory_percent": 1.0,
        }
        procs.append(p)
        return procs

    @patch("engine.sources.processes.psutil")
    def test_groups_by_name(self, mock_psutil):
        mock_psutil.process_iter.return_value = self._make_mock_procs()
        mock_psutil.cpu_count.return_value = 4

        source = ProcessSource()
        entities = source.fetch()
        processes = [e for e in entities if e.parent is not None]

        names = {p.name for p in processes}
        assert "python3" in names
        assert "nginx" in names

    @patch("engine.sources.processes.psutil")
    def test_aggregated_metrics(self, mock_psutil):
        mock_psutil.process_iter.return_value = self._make_mock_procs()
        mock_psutil.cpu_count.return_value = 4

        source = ProcessSource()
        entities = source.fetch()
        processes = [e for e in entities if e.parent is not None]

        python_proc = [p for p in processes if p.name == "python3"][0]
        assert python_proc.metrics["count"] == 3
        assert sorted(python_proc.metrics["pids"]) == [100, 200, 300]

    @patch("engine.sources.processes.psutil")
    def test_handles_zombie_process(self, mock_psutil):
        """Zombie/dead processes during iteration are skipped gracefully."""
        good_procs = self._make_mock_procs()[:1]  # just the first python3

        class ZombieProc:
            @property
            def info(self):
                raise psutil.NoSuchProcess(pid=999)

        import psutil as real_psutil
        mock_psutil.NoSuchProcess = real_psutil.NoSuchProcess
        mock_psutil.process_iter.return_value = good_procs + [ZombieProc()]
        mock_psutil.cpu_count.return_value = 4

        source = ProcessSource()
        entities = source.fetch()
        # Should not crash, should still return entities (root + 1 process)
        assert len(entities) >= 2
