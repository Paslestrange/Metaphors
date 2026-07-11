"""End-to-end integration test for the Metaphors application.

Starts the real FastAPI server on a free port, connects via WebSocket,
verifies mock data flows through to entity snapshots, tests metaphor
switching via the scheduler, checks the health endpoint, and tears down
cleanly.
"""
import asyncio
import json
import pytest
import httpx
import websockets
import uvicorn

from engine.scheduler import EntityScheduler
from engine.sources.mock import MockSource
from engine.entities import Entity, EntityType, EntityState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class StubSource:
    """Minimal data source for metaphor-switching tests."""

    name = "stub"

    def __init__(self, entities=None):
        self._entities = entities or []

    def is_available(self) -> bool:
        return True

    def fetch(self) -> list:
        return list(self._entities)


def _make_scheduler(interval=0.3):
    return EntityScheduler(sources=[MockSource()], interval_sec=interval)


async def _start_server(scheduler):
    """Start uvicorn with patched scheduler, return (port, server, task, restore_fn)."""
    import server as srv

    original_scheduler = srv.scheduler
    srv.scheduler = scheduler

    config = uvicorn.Config(srv.app, host="127.0.0.1", port=0, log_level="error")
    server_inst = uvicorn.Server(config)

    port_holder = []
    orig_startup = server_inst.startup

    async def patched_startup(sockets=None):
        await orig_startup(sockets=sockets)
        for srv_group in server_inst.servers:
            for sock in srv_group.sockets:
                port_holder.append(sock.getsockname()[1])

    server_inst.startup = patched_startup
    task = asyncio.create_task(server_inst.serve())

    # Wait until port is known
    for _ in range(200):
        if port_holder:
            break
        await asyncio.sleep(0.05)
    else:
        server_inst.should_exit = True
        await task
        srv.scheduler = original_scheduler
        raise RuntimeError("Server did not start in time")

    port = port_holder[0]

    async def teardown():
        server_inst.should_exit = True
        try:
            await asyncio.wait_for(task, timeout=5.0)
        except asyncio.TimeoutError:
            task.cancel()
        srv.scheduler = original_scheduler

    return port, server_inst, task, teardown


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint():
    """GET /health returns 200 with status ok."""
    scheduler = _make_scheduler()
    port, server_inst, task, teardown = await _start_server(scheduler)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://127.0.0.1:{port}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
    finally:
        await teardown()


@pytest.mark.asyncio
async def test_websocket_entity_snapshot():
    """Connect WebSocket, receive at least one valid entity snapshot."""
    scheduler = _make_scheduler()
    port, server_inst, task, teardown = await _start_server(scheduler)
    try:
        uri = f"ws://127.0.0.1:{port}/ws/entities"
        async with websockets.connect(uri) as ws:
            raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(raw)

            assert data["type"] == "entities"
            assert "timestamp" in data
            assert isinstance(data["timestamp"], float)
            assert isinstance(data["entities"], list)
            assert len(data["entities"]) > 0

            # Validate first entity has all required fields
            entity = data["entities"][0]
            required = {"id", "type", "name", "state", "metrics",
                        "children", "parent", "labels", "annotations", "source"}
            assert required.issubset(entity.keys())
    finally:
        await teardown()


@pytest.mark.asyncio
async def test_mock_data_flows_through():
    """MockSource entities appear in the WebSocket stream with correct structure."""
    scheduler = _make_scheduler()
    port, server_inst, task, teardown = await _start_server(scheduler)
    try:
        uri = f"ws://127.0.0.1:{port}/ws/entities"
        async with websockets.connect(uri) as ws:
            raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(raw)
            entities = data["entities"]

            # MockSource produces: 1 cluster + 3 nodes + services + containers
            assert len(entities) >= 4, f"Expected >=4 entities, got {len(entities)}"

            # Should have a cluster entity
            clusters = [e for e in entities if e["type"] == "cluster"]
            assert len(clusters) >= 1
            assert clusters[0]["name"] == "Production"
            assert clusters[0]["state"] == "healthy"

            # Should have node entities with parent=cluster
            nodes = [e for e in entities if e["type"] == "node"]
            assert len(nodes) == 3
            for node in nodes:
                assert node["parent"] == "cluster-prod"
                assert "cpu" in node["metrics"]
                assert "mem" in node["metrics"]

            # Should have service entities
            services = [e for e in entities if e["type"] == "service"]
            assert len(services) > 0
            for svc in services:
                assert svc["source"] == "mock"
                assert svc["state"] in ("healthy", "warning")

            # Should have container entities
            containers = [e for e in entities if e["type"] == "container"]
            assert len(containers) > 0
    finally:
        await teardown()


@pytest.mark.asyncio
async def test_metaphor_switching():
    """Scheduler can swap data sources and new data flows through WebSocket."""
    # Start with mock source
    scheduler = _make_scheduler()
    port, server_inst, task, teardown = await _start_server(scheduler)
    try:
        uri = f"ws://127.0.0.1:{port}/ws/entities"
        async with websockets.connect(uri) as ws:
            # Receive mock data
            raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(raw)
            assert data["entities"][0]["source"] == "mock"

            # Switch to a stub source with custom entities
            custom_entity = Entity(
                id="custom-1",
                type=EntityType.AGENT,
                name="TestAgent",
                state=EntityState.IDLE,
                source="stub",
                metrics={"tasks": 42},
            )
            scheduler.sources.clear()
            scheduler.sources.append(StubSource(entities=[custom_entity]))

            # Wait for next poll cycle to pick up new source
            raw2 = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data2 = json.loads(raw2)

            # Should eventually get stub data
            # (might need a few messages until the scheduler cycles)
            found_stub = False
            if data2["entities"] and data2["entities"][0].get("source") == "stub":
                found_stub = True
            else:
                # Try a few more messages
                for _ in range(10):
                    raw3 = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data3 = json.loads(raw3)
                    if data3["entities"] and data3["entities"][0].get("source") == "stub":
                        assert data3["entities"][0]["id"] == "custom-1"
                        assert data3["entities"][0]["name"] == "TestAgent"
                        assert data3["entities"][0]["type"] == "agent"
                        assert data3["entities"][0]["state"] == "idle"
                        assert data3["entities"][0]["metrics"]["tasks"] == 42
                        found_stub = True
                        break

            assert found_stub, "Stub source data never appeared in stream after switch"
    finally:
        await teardown()


@pytest.mark.asyncio
async def test_static_files_served():
    """Index page and static assets are served correctly."""
    scheduler = _make_scheduler()
    port, server_inst, task, teardown = await _start_server(scheduler)
    try:
        async with httpx.AsyncClient() as client:
            # Index page
            resp = await client.get(f"http://127.0.0.1:{port}/")
            assert resp.status_code == 200
            assert "text/html" in resp.headers.get("content-type", "")
            assert "canvas" in resp.text

            # Main JS
            resp_js = await client.get(f"http://127.0.0.1:{port}/static/main.js")
            assert resp_js.status_code == 200
            assert "WebSocket" in resp_js.text
            assert "computeLayout" in resp_js.text
            assert "City" in resp_js.text or "city" in resp_js.text.lower()

            # Style CSS
            resp_css = await client.get(f"http://127.0.0.1:{port}/static/style.css")
            assert resp_css.status_code == 200
    finally:
        await teardown()


@pytest.mark.asyncio
async def test_multiple_websocket_clients():
    """Multiple WebSocket clients can connect simultaneously and all receive data."""
    scheduler = _make_scheduler()
    port, server_inst, task, teardown = await _start_server(scheduler)
    try:
        uri = f"ws://127.0.0.1:{port}/ws/entities"
        async with websockets.connect(uri) as ws1, \
                   websockets.connect(uri) as ws2:

            raw1 = await asyncio.wait_for(ws1.recv(), timeout=5.0)
            raw2 = await asyncio.wait_for(ws2.recv(), timeout=5.0)

            data1 = json.loads(raw1)
            data2 = json.loads(raw2)

            # Both clients should get valid snapshots
            assert data1["type"] == "entities"
            assert data2["type"] == "entities"
            assert len(data1["entities"]) > 0
            assert len(data2["entities"]) > 0

            # Entity counts should match (same scheduler, same poll)
            assert len(data1["entities"]) == len(data2["entities"])
    finally:
        await teardown()


@pytest.mark.asyncio
async def test_clean_teardown():
    """Server shuts down cleanly without hanging or errors."""
    scheduler = _make_scheduler()
    port, server_inst, task, teardown = await _start_server(scheduler)

    # Connect a client, then teardown while connected
    uri = f"ws://127.0.0.1:{port}/ws/entities"
    async with websockets.connect(uri) as ws:
        raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
        assert json.loads(raw)["type"] == "entities"

        # Teardown should complete without hanging
        await asyncio.wait_for(teardown(), timeout=10.0)

    # Server task should be done
    assert task.done()
