import asyncio
import json
import time
from engine.entities import Entity
from engine.sources.base import DataSource

class EntityScheduler:
    """Polls data sources and broadcasts entity snapshots."""

    def __init__(self, sources: list[DataSource], interval_sec: float = 5.0):
        self.sources = sources
        self.interval = interval_sec
        self.subscribers: list[asyncio.Queue] = []
        self._running = False

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers = [s for s in self.subscribers if s is not q]

    async def start(self) -> None:
        self._running = True
        while self._running:
            entities = []
            for source in self.sources:
                if source.is_available():
                    try:
                        entities.extend(source.fetch())
                    except Exception as e:
                        print(f"Source {source.name} error: {e}")

            snapshot = {
                "type": "entities",
                "timestamp": time.time(),
                "entities": [e.to_dict() if isinstance(e, Entity) else e for e in entities],
            }
            payload = json.dumps(snapshot)

            for q in self.subscribers:
                try:
                    q.put_nowait(payload)
                except asyncio.QueueFull:
                    pass

            await asyncio.sleep(self.interval)

    def stop(self) -> None:
        self._running = False
