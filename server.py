from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import uvicorn
import asyncio
import json
import subprocess
import shutil

from engine.scheduler import EntityScheduler
from engine.sources.mock import MockSource
from engine.sources.processes import ProcessSource
from engine.sources.docker import DockerSource
from engine.sources.prometheus import PrometheusSource
from engine.metaphors import MetaphorRegistry
from engine.metaphors.city import CityRenderer
from engine.metaphors.space import SpaceStationRenderer
from engine.metaphors.garden import GardenRenderer


app = FastAPI(title="Metaphors", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Metaphor registry — register metaphors on startup
registry = MetaphorRegistry()
registry.register("city", CityRenderer())
registry.register("space", SpaceStationRenderer())
registry.register("garden", GardenRenderer())

active_metaphor = "city"

# Scheduler with both mock and live process sources
scheduler = EntityScheduler(sources=[MockSource(), ProcessSource(), DockerSource(), PrometheusSource()], interval_sec=3.0)


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/3d")
async def index_3d():
    return FileResponse("static/3d/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


# --- Metaphor REST API ---

@app.get("/api/metaphors")
async def list_metaphors():
    """List all available metaphor renderers."""
    names = registry.list()
    # Return rich metaphor metadata
    metaphor_info = []
    descriptions = {
        "city": "Infrastructure as a cityscape",
        "space": "Systems as a space station with orbiting modules",
        "garden": "Infrastructure as a garden with plants, terrain, and lighting",
        "kitchen": "Infrastructure as a kitchen with appliances, prep stations, and cooking",
        "factory": "Infrastructure as a factory with conveyor belts, robot arms, and assembly lines",
        "construction": "Infrastructure as a construction site with cranes, scaffolding, and workers",
        "ship": "Infrastructure as a ship with decks, crew stations, and cargo holds",
        "orchestra": "Infrastructure as an orchestra with instrument sections and musicians",
    }
    for name in names:
        metaphor_info.append({
            "id": name,
            "name": name.capitalize(),
            "description": descriptions.get(name, f"The {name} metaphor"),
        })
    # Also include client-side-only metaphors that have frontend renderers
    known_client = ["space", "garden"]
    for name in known_client:
        if name not in names:
            metaphor_info.append({
                "id": name,
                "name": name.capitalize(),
                "description": descriptions.get(name, f"The {name} metaphor"),
            })
    return {
        "metaphors": metaphor_info,
        "active": active_metaphor,
        "default": active_metaphor,
    }


@app.get("/api/metaphors/{name}")
async def get_metaphor(name: str):
    """Get configuration for a specific metaphor."""
    renderer = registry.get(name)
    if renderer is None:
        return JSONResponse(status_code=404, content={"error": f"Metaphor '{name}' not found"})
    if hasattr(renderer, "config"):
        return renderer.config()
    return {"name": name}


# --- Logs API ---

@app.get("/api/logs/docker/{container_id}")
async def docker_logs(container_id: str, tail: int = Query(default=100, ge=1, le=1000)):
    """Fetch recent logs from a Docker container."""
    docker = shutil.which("docker")
    if docker is None:
        return JSONResponse(status_code=503, content={"error": "docker not available"})
    try:
        result = subprocess.run(
            [docker, "logs", "--tail", str(tail), container_id],
            capture_output=True, text=True, timeout=5.0,
        )
        logs = result.stdout or result.stderr or "(no output)"
        return {"container_id": container_id, "logs": logs}
    except subprocess.TimeoutExpired:
        return JSONResponse(status_code=504, content={"error": "docker logs timed out"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/logs/process")
async def process_logs(name: str = Query(...), lines: int = Query(default=50, ge=1, le=500)):
    """Fetch recent syslog/journal entries for a process name."""
    journalctl = shutil.which("journalctl")
    if journalctl:
        try:
            result = subprocess.run(
                [journalctl, "--no-pager", "-n", str(lines), "-t", name],
                capture_output=True, text=True, timeout=5.0,
            )
            logs = result.stdout or "(no journal entries)"
            return {"process": name, "logs": logs, "source": "journalctl"}
        except subprocess.TimeoutExpired:
            return JSONResponse(status_code=504, content={"error": "journalctl timed out"})
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
    # Fallback: search dmesg
    dmesg = shutil.which("dmesg")
    if dmesg:
        try:
            result = subprocess.run(
                ["dmesg", "--level=info,warn,err", "-T"],
                capture_output=True, text=True, timeout=5.0,
            )
            matching = [l for l in result.stdout.splitlines() if name.lower() in l.lower()][-lines:]
            logs = "\n".join(matching) if matching else f"(no dmesg entries for '{name}')"
            return {"process": name, "logs": logs, "source": "dmesg"}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
    return JSONResponse(status_code=503, content={"error": "no log source available"})


@app.get("/api/logs/prometheus")
async def prometheus_logs(instance: str = Query(default="")):
    """Fetch alert/rule info for a Prometheus-monitored instance."""
    # Prometheus itself doesn't expose system logs — return recent alert state
    prom = None
    for src in scheduler.sources:
        if src.name == "prometheus":
            prom = src
            break
    if prom is None:
        return JSONResponse(status_code=503, content={"error": "prometheus source not configured"})
    try:
        from engine.sources.prometheus import PrometheusSource
        if not isinstance(prom, PrometheusSource):
            return JSONResponse(status_code=503, content={"error": "prometheus source not configured"})
        alerts = prom._get_alerts()
        instance_alerts = {k: v for k, v in alerts.items() if not instance or k == instance}
        return {"instance": instance, "alerts": instance_alerts, "source": "prometheus"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# --- WebSocket ---

@app.websocket("/ws/entities")
async def ws_entities(websocket: WebSocket):
    await websocket.accept()
    queue = scheduler.subscribe()
    try:
        while True:
            # Check for incoming control messages (non-blocking)
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
                msg = json.loads(raw)
                if msg.get("type") == "switch_metaphor":
                    global active_metaphor
                    new_name = msg.get("name", "")
                    if registry.get(new_name) is not None:
                        active_metaphor = new_name
                        await websocket.send_text(json.dumps({
                            "type": "metaphor_switched",
                            "name": active_metaphor,
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"Unknown metaphor: {new_name}",
                        }))
            except (asyncio.TimeoutError, Exception):
                pass

            # Send entity data
            try:
                data = queue.get_nowait()
                # Inject active metaphor into payload
                payload = json.loads(data)
                payload["metaphor"] = active_metaphor
                await websocket.send_text(json.dumps(payload))
            except asyncio.QueueEmpty:
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        scheduler.unsubscribe(queue)


@app.on_event("startup")
async def startup():
    asyncio.create_task(scheduler.start())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
