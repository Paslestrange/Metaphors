from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import asyncio

from engine.scheduler import EntityScheduler
from engine.sources.mock import MockSource

app = FastAPI(title="Metaphors", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

scheduler = EntityScheduler(sources=[MockSource()], interval_sec=3.0)

@app.get("/")
async def index():
    return FileResponse("static/index.html")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.websocket("/ws/entities")
async def ws_entities(websocket: WebSocket):
    await websocket.accept()
    queue = scheduler.subscribe()
    try:
        while True:
            data = await queue.get()
            await websocket.send_text(data)
    except WebSocketDisconnect:
        pass
    finally:
        scheduler.unsubscribe(queue)

@app.on_event("startup")
async def startup():
    asyncio.create_task(scheduler.start())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
