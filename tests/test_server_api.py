import asyncio
import json
import pytest
import websockets
import uvicorn

from engine.scheduler import EntityScheduler
from engine.sources.mock import MockSource


def _make_scheduler():
    return EntityScheduler(sources=[MockSource()], interval_sec=0.3)


async def _start_test():
    import server as srv
    original_scheduler = srv.scheduler
    scheduler = _make_scheduler()
    srv.scheduler = scheduler
    config = uvicorn.Config(srv.app, host='127.0.0.1', port=0, log_level='error')
    si = uvicorn.Server(config)
    ph = []
    ou = si.startup
    async def ps(sockets=None):
        await ou(sockets=sockets)
        if si.servers:
            for s in si.servers:
                for sock in s.sockets:
                    ph.append(sock.getsockname()[1])
    si.startup = ps
    task = asyncio.create_task(si.serve())
    for _ in range(100):
        if ph: break
        await asyncio.sleep(0.05)
    return ph[0], si, task, original_scheduler, srv


@pytest.mark.asyncio
async def test_get_metaphors_list():
    import httpx
    port, si, task, orig, srv = await _start_test()
    try:
        base = 'http://127.0.0.1:' + str(port)
        async with httpx.AsyncClient(base_url=base) as c:
            r = await c.get('/api/metaphors')
            assert r.status_code == 200
            d = r.json()
            assert 'metaphors' in d
            assert 'city' in d['metaphors']
            assert d['active'] == 'city'
    finally:
        si.should_exit = True
        await task
        srv.scheduler = orig


@pytest.mark.asyncio
async def test_get_metaphor_city_config():
    import httpx
    port, si, task, orig, srv = await _start_test()
    try:
        base = 'http://127.0.0.1:' + str(port)
        async with httpx.AsyncClient(base_url=base) as c:
            r = await c.get('/api/metaphors/city')
            assert r.status_code == 200
            d = r.json()
            assert d['name'] == 'city'
            assert 'state_colors' in d
            assert 'mappings' in d
    finally:
        si.should_exit = True
        await task
        srv.scheduler = orig


@pytest.mark.asyncio
async def test_get_metaphor_not_found():
    import httpx
    port, si, task, orig, srv = await _start_test()
    try:
        base = 'http://127.0.0.1:' + str(port)
        async with httpx.AsyncClient(base_url=base) as c:
            r = await c.get('/api/metaphors/nonexistent')
            assert r.status_code == 404
            d = r.json()
            assert 'error' in d
    finally:
        si.should_exit = True
        await task
        srv.scheduler = orig


@pytest.mark.asyncio
async def test_ws_metaphor_switch():
    port, si, task, orig, srv = await _start_test()
    try:
        uri = 'ws://127.0.0.1:' + str(port) + '/ws/entities'
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({'type': 'switch_metaphor', 'name': 'city'}))
            for _ in range(20):
                raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(raw)
                if data.get('type') == 'metaphor_switched':
                    assert data['name'] == 'city'
                    break
            else:
                pytest.fail('No metaphor_switched')
    finally:
        si.should_exit = True
        await task
        srv.scheduler = orig


@pytest.mark.asyncio
async def test_ws_metaphor_switch_unknown():
    port, si, task, orig, srv = await _start_test()
    try:
        uri = 'ws://127.0.0.1:' + str(port) + '/ws/entities'
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({'type': 'switch_metaphor', 'name': 'nope'}))
            for _ in range(20):
                raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(raw)
                if data.get('type') == 'error':
                    assert 'Unknown metaphor' in data['message']
                    break
            else:
                pytest.fail('No error msg')
    finally:
        si.should_exit = True
        await task
        srv.scheduler = orig


@pytest.mark.asyncio
async def test_ws_entities_include_metaphor_field():
    port, si, task, orig, srv = await _start_test()
    try:
        uri = 'ws://127.0.0.1:' + str(port) + '/ws/entities'
        async with websockets.connect(uri) as ws:
            for _ in range(10):
                raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(raw)
                if data.get('type') == 'entities':
                    assert 'metaphor' in data
                    assert data['metaphor'] == 'city'
                    break
            else:
                pytest.fail('No entities with metaphor')
    finally:
        si.should_exit = True
        await task
        srv.scheduler = orig
