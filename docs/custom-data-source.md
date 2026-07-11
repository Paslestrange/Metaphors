# Custom Data Source Tutorial

How to create your own data source that feeds entities into the Metaphors visualization engine.

---

## What Is a Data Source?

A **data source** is a component that collects infrastructure (or any) data and converts it into `Entity` objects the engine can visualize. Each source represents one "lens" on your system — one might read local processes, another might query a Kubernetes API, a third might poll a REST endpoint.

The scheduler polls all registered sources on a fixed interval, merges their entities, and pushes the combined snapshot to connected WebSocket clients.

---

## The DataSource Interface

Every data source inherits from `engine.sources.base.DataSource` and implements exactly **two methods**:

```python
from engine.sources.base import DataSource
from engine.entities import Entity

class MySource(DataSource):
    name = "my_source"          # unique identifier string

    def is_available(self) -> bool:
        """Return True if this source can currently provide data."""
        ...

    def fetch(self) -> list[Entity]:
        """Return a complete snapshot of all entities from this source."""
        ...
```

### `is_available() -> bool`

Called by the scheduler before each fetch cycle. Return `True` if the source is reachable and ready, `False` to skip it this cycle. Use this for health checks — e.g. test a TCP connection, verify an API key, or check if a required library is installed.

### `fetch() -> list[Entity]`

Returns the **full current snapshot** of entities. Not a delta — the scheduler replaces the previous snapshot each cycle. Each entity must have a unique `id` within this source.

---

## Step 1: Create the Source File

Create your new source at `engine/sources/my_source.py`:

```
engine/sources/
├── __init__.py
├── base.py          # DataSource ABC
├── mock.py          # MockSource (dev/fallback)
├── processes.py     # ProcessSource (live system)
└── my_source.py     # <-- your new source
```

---

## Step 2: Implement `is_available()`

This method gates whether `fetch()` gets called. Keep it fast — it runs every scheduler tick.

```python
def is_available(self) -> bool:
    # Simple: always available
    return True

    # Or: check a real dependency
    try:
        import some_sdk
        client = some_sdk.Client(api_key=self.api_key)
        client.ping()
        return True
    except Exception:
        return False
```

**Tips:**
- Cache expensive checks if the scheduler interval is short (e.g. 3s).
- Don't raise exceptions — return `False` instead.

---

## Step 3: Implement `fetch()` → `list[Entity]`

This is the core. You must return `Entity` objects with proper hierarchy.

### The Entity Model

```python
@dataclass
class Entity:
    id: str                           # unique within source
    type: EntityType                  # CLUSTER, NODE, SERVICE, etc.
    name: str                         # display name
    state: EntityState = UNKNOWN      # HEALTHY, RUNNING, WARNING, etc.
    metrics: dict[str, Any] = {}      # arbitrary numeric data for visualization
    children: list[str] = []          # IDs of child entities
    parent: str | None = None         # ID of parent entity
    labels: dict[str, str] = {}       # key-value tags
    annotations: dict[str, str] = {}  # free-form metadata
    source: str = ""                  # name of this source
```

### Available Entity Types

```
CLUSTER, NODE, NAMESPACE, SERVICE, CONTAINER,
PROCESS, AGENT, SESSION, QUEUE, DATABASE, CUSTOM
```

### Available Entity States

```
UNKNOWN, HEALTHY, RUNNING, IDLE, WARNING,
DEGRADED, CRITICAL, STOPPED, PENDING, SCALING
```

### Building the Hierarchy

Entities form a tree. Set `parent` on children and `children` (list of IDs) on parents:

```python
root = Entity(id="root", type=EntityType.CLUSTER, name="My System", ...)
child = Entity(id="svc-1", type=EntityType.SERVICE, name="API", parent="root", ...)
root.children.append("svc-1")
```

---

## Step 4: Register in `engine/sources/__init__.py`

Add your source to the package exports:

```python
from .base import DataSource
from .mock import MockSource
from .processes import ProcessSource
from .my_source import MySource        # <-- add this
```

---

## Step 5: Add to `server.py` Scheduler

Import and instantiate your source in the scheduler's source list:

```python
from engine.sources.my_source import MySource

scheduler = EntityScheduler(
    sources=[MockSource(), ProcessSource(), MySource()],  # <-- add here
    interval_sec=3.0
)
```

That's it. The scheduler will now poll your source every `interval_sec` seconds and include its entities in the WebSocket stream.

---

## Step 6: Write Tests

Create `tests/test_my_source.py` following the project pattern:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.entities import Entity, EntityType
from engine.sources.my_source import MySource


def test_returns_entities():
    src = MySource()
    entities = src.fetch()
    assert len(entities) > 0
    for e in entities:
        assert isinstance(e, Entity)


def test_unique_ids():
    src = MySource()
    ids = [e.id for e in src.fetch()]
    assert len(ids) == len(set(ids))


def test_has_root():
    src = MySource()
    entities = src.fetch()
    roots = [e for e in entities if e.parent is None]
    assert len(roots) >= 1, "Need at least one root entity (no parent)"


def test_is_available():
    src = MySource()
    assert isinstance(src.is_available(), bool)
```

Run with: `python -m pytest tests/test_my_source.py -v`

---

## Complete Working Example: RandomData Source

A minimal but fully functional source that generates random infrastructure data. Useful as a template or for UI development.

```python
"""engine/sources/random_data.py — Random data source for development."""
from __future__ import annotations

import random
import time

from engine.entities import Entity, EntityType, EntityState
from .base import DataSource


class RandomDataSource(DataSource):
    """Generates random entity trees for testing and development."""

    name = "random_data"

    def __init__(self, num_nodes: int = 3, services_per_node: int = 3):
        self.num_nodes = num_nodes
        self.services_per_node = services_per_node

    def is_available(self) -> bool:
        return True

    def fetch(self) -> list[Entity]:
        entities: list[Entity] = []

        # Root cluster
        cluster = Entity(
            id="rnd-cluster",
            type=EntityType.CLUSTER,
            name="Random Cluster",
            state=EntityState.HEALTHY,
            source=self.name,
            labels={"env": "dev", "generated": "true"},
            metrics={"tick": int(time.time()) % 1000},
        )
        entities.append(cluster)

        # Nodes
        for i in range(self.num_nodes):
            node_id = f"rnd-node-{i}"
            node = Entity(
                id=node_id,
                type=EntityType.NODE,
                name=f"node-{i}.random.internal",
                state=EntityState.RUNNING,
                parent=cluster.id,
                source=self.name,
                metrics={
                    "cpu": random.randint(5, 95),
                    "mem": random.randint(10, 90),
                },
            )
            cluster.children.append(node_id)
            entities.append(node)

            # Services per node
            for j in range(self.services_per_node):
                svc_id = f"rnd-svc-{i}-{j}"
                svc = Entity(
                    id=svc_id,
                    type=EntityType.SERVICE,
                    name=random.choice([
                        "api", "worker", "cache", "proxy",
                        "scheduler", "logger", "metrics",
                    ]),
                    state=random.choice([
                        EntityState.HEALTHY,
                        EntityState.HEALTHY,
                        EntityState.WARNING,
                        EntityState.IDLE,
                    ]),
                    parent=node_id,
                    source=self.name,
                    metrics={
                        "cpu": random.randint(1, 80),
                        "mem": random.randint(5, 70),
                        "req_per_sec": random.randint(0, 1000),
                    },
                )
                node.children.append(svc_id)
                entities.append(svc)

        return entities
```

---

## Mapping External Data to the Entity Model

When wrapping an external API or data source, follow this mapping strategy:

| External Concept    | Entity Type   | Example                              |
|---------------------|---------------|--------------------------------------|
| Account / Org       | CLUSTER       | `"my-org"`                           |
| Server / VM / Host  | NODE          | `"web-server-01"`                    |
| Application / App   | SERVICE       | `"auth-service"`                     |
| Container / Pod     | CONTAINER     | `"auth-service-abc123"`              |
| Worker / Task       | PROCESS       | `"celery-worker-3"`                  |
| Database Instance   | DATABASE      | `"postgres-primary"`                 |
| Agent / Bot         | AGENT         | `"monitoring-agent"`                 |
| Message Queue       | QUEUE         | `"task-queue"`                       |

### State Mapping

| External Status         | EntityState    |
|-------------------------|----------------|
| running / active / ok   | HEALTHY        |
| starting / provisioning | PENDING        |
| degraded / limping      | WARNING        |
| down / failed / error   | CRITICAL       |
| stopped / terminated    | STOPPED        |
| scaling / resizing      | SCALING        |
| unknown / other         | UNKNOWN        |

### Metrics

Put anything numeric in `metrics` — the visualization engine uses these for sizing, coloring, and animations:

```python
metrics={
    "cpu": 45.2,          # → affects node glow/size
    "mem": 72.0,          # → affects container size
    "req_per_sec": 340,   # → affects pulse animation speed
    "error_rate": 0.02,   # → affects color (green → red)
}
```

### Labels & Annotations

- **Labels** (`dict[str, str]`): Structured tags for filtering/grouping. E.g. `{"env": "prod", "region": "eu-west"}`.
- **Annotations** (`dict[str, str]`): Free-form metadata for tooltips. E.g. `{"version": "v2.3.1", "deploy_time": "2026-07-11T10:00:00Z"}`.

---

## Checklist

- [ ] Created `engine/sources/my_source.py`
- [ ] Inherited from `DataSource`
- [ ] Set `name` class attribute (unique string)
- [ ] Implemented `is_available() -> bool`
- [ ] Implemented `fetch() -> list[Entity]`
- [ ] All entity IDs are unique within the source
- [ ] Parent/children relationships are bidirectional
- [ ] Registered in `engine/sources/__init__.py`
- [ ] Added to `server.py` scheduler sources list
- [ ] Wrote tests in `tests/test_my_source.py`
- [ ] All tests pass: `python -m pytest tests/ -v`
