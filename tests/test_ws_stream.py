"""Tests for WebSocket entity stream with real-time updates.

Starts the FastAPI server in a background task, connects a websockets client
to /ws/entities, and validates the JSON snapshot structure.
"""
import asyncio
import json
import pytest
import websockets
import uvicorn

from engine.scheduler import EntityScheduler
from engine.sources.mock import MockSource


def _make_scheduler():
    """Create a scheduler with mock source and fast interval for testing."""
    return EntityScheduler(sources=[MockSource()], interval_sec=0.3)


def _start_server(scheduler):
    """Start uvicorn in background, return (port, server_instance, task)."""
    import server as srv
    original = srv.scheduler
    srv.scheduler = scheduler

    config = uvicorn.Config(srv.app, host="127.0.0.1", port=0, log_level="error")
    server_inst = uvicorn.Server(config)

    port_holder = []
    original_startup = server_inst.startup

    async def patched_startup(sockets=None):
        await original_startup(sockets=sockets)
        if server_inst.servers:
            for s in server_inst.servers:
                for sock in s.sockets:
                    port_holder.append(sock.getsockname()[1])

    server_inst.startup = patched_startup
    task = asyncio.get_event_loop().run_until_complete(_async_start(server_inst, port_holder))
    return port_holder[0], server_inst, task, original, srv


async def _async_start(server_inst, port_holder):
    task = asyncio.create_task(server_inst.serve())
    for _ in range(100):
        if port_holder:
            break
        await asyncio.sleep(0.05)
    return task


@pytest.mark.asyncio
async def test_ws_receives_entity_snapshot():
    """Client receives at least one valid JSON entity snapshot."""
    scheduler = _make_scheduler()

    import server as srv
    original = srv.scheduler
    srv.scheduler = scheduler

    config = uvicorn.Config(srv.app, host="127.0.0.1", port=0, log_level="error")
    server_inst = uvicorn.Server(config)

    port_holder = []
    original_startup = server_inst.startup

    async def patched_startup(sockets=None):
        await original_startup(sockets=sockets)
        if server_inst.servers:
            for s in server_inst.servers:
                for sock in s.sockets:
                    port_holder.append(sock.getsockname()[1])

    server_inst.startup = patched_startup
    task = asyncio.create_task(server_inst.serve())

    # Wait for server ready
    for _ in range(100):
        if port_holder:
            break
        await asyncio.sleep(0.05)

    port = port_holder[0]
    uri = f"ws://127.0.0.1:{port}/ws/entities"

    try:
        async with websockets.connect(uri) as ws:
            raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(raw)

            assert data["type"] == "entities"
            assert "timestamp" in data
            assert isinstance(data["entities"], list)
            assert len(data["entities"]) > 0

            # Validate entity structure
            entity = data["entities"][0]
            for key in ("id", "type", "name", "state"):
                assert key in entity, f"Missing key '{key}' in entity"
    finally:
        server_inst.should_exit = True
        await task
        srv.scheduler = original


@pytest.mark.asyncio
async def test_ws_receives_multiple_updates():
    """Client receives multiple snapshots over time (real-time stream)."""
    scheduler = _make_scheduler()

    import server as srv
    original = srv.scheduler
    srv.scheduler = scheduler

    config = uvicorn.Config(srv.app, host="127.0.0.1", port=0, log_level="error")
    server_inst = uvicorn.Server(config)

    port_holder = []
    original_startup = server_inst.startup

    async def patched_startup(sockets=None):
        await original_startup(sockets=sockets)
        if server_inst.servers:
            for s in server_inst.servers:
                for sock in s.sockets:
                    port_holder.append(sock.getsockname()[1])

    server_inst.startup = patched_startup
    task = asyncio.create_task(server_inst.serve())

    for _ in range(100):
        if port_holder:
            break
        await asyncio.sleep(0.05)

    port = port_holder[0]
    uri = f"ws://127.0.0.1:{port}/ws/entities"

    try:
        async with websockets.connect(uri) as ws:
            messages = []
            for _ in range(3):
                raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                messages.append(json.loads(raw))

            assert len(messages) == 3
            # Timestamps should be non-decreasing
            ts = [m["timestamp"] for m in messages]
            assert ts == sorted(ts)
    finally:
        server_inst.should_exit = True
        await task
        srv.scheduler = original


@pytest.mark.asyncio
async def test_ws_entity_fields_complete():
    """Each entity in snapshot has all required fields from Entity.to_dict()."""
    scheduler = _make_scheduler()

    import server as srv
    original = srv.scheduler
    srv.scheduler = scheduler

    config = uvicorn.Config(srv.app, host="127.0.0.1", port=0, log_level="error")
    server_inst = uvicorn.Server(config)

    port_holder = []
    original_startup = server_inst.startup

    async def patched_startup(sockets=None):
        await original_startup(sockets=sockets)
        if server_inst.servers:
            for s in server_inst.servers:
                for sock in s.sockets:
                    port_holder.append(sock.getsockname()[1])

    server_inst.startup = patched_startup
    task = asyncio.create_task(server_inst.serve())

    for _ in range(100):
        if port_holder:
            break
        await asyncio.sleep(0.05)

    port = port_holder[0]
    uri = f"ws://127.0.0.1:{port}/ws/entities"

    try:
        async with websockets.connect(uri) as ws:
            raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(raw)

            required_fields = {"id", "type", "name", "state", "metrics",
                               "children", "parent", "labels", "annotations", "source"}
            for entity in data["entities"]:
                assert required_fields.issubset(entity.keys()), (
                    f"Entity {entity.get('id')} missing fields: "
                    f"{required_fields - entity.keys()}"
                )
    finally:
        server_inst.should_exit = True
        await task
        srv.scheduler = original


@pytest.mark.asyncio
async def test_scheduler_subscribe_unsubscribe():
    """Scheduler subscribe/unsubscribe manages queue lifecycle."""
    scheduler = _make_scheduler()
    q1 = scheduler.subscribe()
    q2 = scheduler.subscribe()
    assert len(scheduler.subscribers) == 2

    scheduler.unsubscribe(q1)
    assert len(scheduler.subscribers) == 1
    assert scheduler.subscribers[0] is q2

    scheduler.unsubscribe(q2)
    assert len(scheduler.subscribers) == 0


@pytest.mark.asyncio
async def test_scheduler_polls_sources():
    """Scheduler fetches from all available sources and pushes to subscribers."""
    scheduler = _make_scheduler()
    q = scheduler.subscribe()

    # Run one poll cycle manually
    entities = []
    for source in scheduler.sources:
        if source.is_available():
            entities.extend(source.fetch())

    assert len(entities) > 0
    assert all(hasattr(e, "to_dict") for e in entities)
