from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
import asyncio
import json

from engine.scheduler import EntityScheduler
from engine.sources.mock import MockSource
from engine.sources.processes import ProcessSource
from engine.metaphors import MetaphorRegistry
from engine.metaphors.city import CityRenderer
from engine.metaphors.traffic_light import TrafficLightRenderer

app = FastAPI(title="Metaphors", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Metaphor registry — register metaphors on startup
registry = MetaphorRegistry()
registry.register("city", CityRenderer())
registry.register("traffic_light", TrafficLightRenderer())
active_metaphor = "city"

# Scheduler with both mock and live process sources
scheduler = EntityScheduler(sources=[MockSource(), ProcessSource()], interval_sec=3.0)


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
        "city3d": "Infrastructure as a 3D cyberpunk city",
        "solar": "Systems as orbiting celestial bodies",
        "forest": "Services as a living forest ecosystem",
        "traffic_light": "Infrastructure as traffic signals at an intersection",
        "space": "Systems as a space station with orbiting modules",
        "garden": "Infrastructure as a garden with plants, terrain, and lighting",
    }
    for name in names:
        metaphor_info.append({
            "id": name,
            "name": name.capitalize(),
            "description": descriptions.get(name, f"The {name} metaphor"),
        })
    # Also include client-side-only metaphors that have frontend renderers
    known_client = ["solar", "forest", "space", "city3d", "garden"]
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
