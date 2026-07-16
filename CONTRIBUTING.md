# Contributing to Metaphors

Thanks for your interest in contributing! Metaphors is an infrastructure visualizer that renders your systems through creative metaphors — a city skyline, a space station, a garden. This guide explains how to extend it with your own metaphors and data sources.

---

## Table of Contents

- [Getting Started](#getting-started)
- [Creating a Custom Metaphor](#creating-a-custom-metaphor)
- [Creating a Data Source Plugin](#creating-a-data-source-plugin)
- [Code Style](#code-style)
- [PR Workflow](#pr-workflow)
- [Issue Templates](#issue-templates)
- [Code of Conduct](#code-of-conduct)

---

## Getting Started

```bash
git clone https://github.com/<your-username>/metaphors.git
cd metaphors
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install black ruff pytest
```

Run the test suite to verify your setup:

```bash
pytest tests/
```

Run the dev server:

```bash
python3 server.py
```

---

## Creating a Custom Metaphor

A metaphor maps infrastructure entities (clusters, nodes, services, containers) to visual elements in your chosen theme.

### Step-by-step

1. **Pick a theme.** What real-world system does infrastructure remind you of? A kitchen? A factory? An orchestra?
2. **Define your mapping.** How do clusters, nodes, services, and containers translate to elements in your theme?
3. **Create the file.** Add `engine/metaphors/<your_theme>.py`.
4. **Subclass `MetaphorRenderer`.** Implement the three required methods.
5. **Register it.** Add your renderer to `engine/metaphors/__init__.py`.
6. **Write tests.** Add `tests/test_<your_theme>.py`.

### MetaphorRenderer Interface Contract

```python
from engine.metaphors.base import MetaphorRenderer

class MetaphorRenderer(ABC):

    def render(self, entities: list[dict], ctx, w: int, h: int) -> None:
        """Render all entities to the canvas context.

        Args:
            entities: List of entity dicts (from Entity.to_dict())
            ctx: Canvas rendering context (HTML5 Canvas API)
            w: Canvas width in pixels
            h: Canvas height in pixels
        """

    def get_tooltip(self, entity: dict, x: int, y: int) -> str | None:
        """Return tooltip text if (x, y) is over this entity, else None."""

    def hit_test(self, entity: dict, x: int, y: int) -> bool:
        """Return True if point (x, y) falls within this entity's bounds."""
```

### Entity Dict Structure

Each entity dict passed to `render()` has this shape:

```python
{
    "id": "svc-0-1",
    "type": "service",        # cluster|node|service|container|...
    "name": "api-gateway",
    "state": "healthy",       # healthy|running|warning|critical|stopped|...
    "metrics": {"cpu": 45, "mem": 72, "req_per_sec": 120},
    "children": ["ctr-0-1-0"],
    "parent": "node-1",
    "labels": {"version": "v2.3.1"},
    "annotations": {},
    "source": "mock"
}
```

### Example: Minimal Metaphor (~20 lines)

A "dots" metaphor — entities as colored circles, size by CPU:

```python
# engine/metaphors/dots.py
from __future__ import annotations
from typing import Any
from engine.metaphors.base import MetaphorRenderer

STATE_COLORS = {
    "healthy": "#4ade80", "warning": "#fbbf24",
    "critical": "#ef4444", "stopped": "#374151",
}

class DotsRenderer(MetaphorRenderer):
    def render(self, entities: list[dict[str, Any]], ctx: Any, w: int, h: int) -> None:
        cols = max(1, int(len(entities) ** 0.5))
        size = min(w, h) // (cols + 1)
        for i, e in enumerate(entities):
            cx = (i % cols) * size + size // 2
            cy = (i // cols) * size + size // 2
            r = max(5, int(e.get("metrics", {}).get("cpu", 50) * size / 200))
            ctx.beginPath()
            ctx.arc(cx, cy, r, 0, 6.28)
            ctx.fillStyle = STATE_COLORS.get(e["state"], "#6b7280")
            ctx.fill()

    def get_tooltip(self, entity: dict, x: int, y: int) -> str | None:
        return f"{entity['name']} ({entity['state']})"

    def hit_test(self, entity: dict, x: int, y: int) -> bool:
        return False  # implement bounds check for interactivity
```

Then register in `engine/metaphors/__init__.py`:

```python
from engine.metaphors.dots import DotsRenderer
```

---

## Creating a Data Source Plugin

A data source feeds entities into the visualization. Sources can pull from Kubernetes, Docker, cloud APIs, databases — anything.

### Step-by-step

1. **Identify your data.** What system exposes the infrastructure you want to visualize?
2. **Create the file.** Add `engine/sources/<your_source>.py`.
3. **Subclass `DataSource`.** Implement `fetch()` and `is_available()`.
4. **Register it.** Add your source to `engine/sources/__init__.py`.
5. **Write tests.** Add `tests/test_<your_source>.py`.

### DataSource Interface Contract

```python
from engine.sources.base import DataSource
from engine.entities import Entity

class DataSource(ABC):
    name: str = "my_source"

    def fetch(self) -> list[Entity]:
        """Return current snapshot of all entities.
        Called periodically by the scheduler.
        Must return a flat list (parent/child links via Entity.parent and Entity.children).
        """

    def is_available(self) -> bool:
        """Return True if this source can connect right now.
        Used by the UI to show source availability status.
        """
```

### Entity Dataclass

```python
@dataclass
class Entity:
    id: str                              # unique identifier
    type: EntityType                     # cluster|node|service|container|process|agent|...
    name: str                            # display name
    state: EntityState = UNKNOWN         # healthy|running|warning|critical|stopped|...
    metrics: dict = {}                   # arbitrary key-value metrics (cpu, mem, etc.)
    children: list[str] = []             # child entity IDs
    parent: str | None = None            # parent entity ID
    labels: dict[str, str] = {}          # metadata tags
    annotations: dict[str, str] = {}     # additional notes
    source: str = ""                     # which source produced this entity
```

### Example: Minimal Data Source (~15 lines)

A source that reads services from a JSON file:

```python
# engine/sources/jsonfile.py
import json
from engine.entities import Entity, EntityType, EntityState
from engine.sources.base import DataSource

class JsonFileSource(DataSource):
    name = "jsonfile"

    def __init__(self, path: str = "infra.json"):
        self.path = path

    def is_available(self) -> bool:
        import os
        return os.path.isfile(self.path)

    def fetch(self) -> list[Entity]:
        with open(self.path) as f:
            data = json.load(f)
        return [
            Entity(
                id=item["id"],
                type=EntityType(item["type"]),
                name=item["name"],
                state=EntityState(item.get("state", "unknown")),
                metrics=item.get("metrics", {}),
                source=self.name,
            )
            for item in data
        ]
```

Then register in `engine/sources/__init__.py`:

```python
from .jsonfile import JsonFileSource
```

---

## Code Style

This project uses:

- **black** — code formatting (default settings, line length 88)
- **ruff** — linting and import sorting
- **pytest** — testing

Before submitting a PR:

```bash
black engine/ tests/
ruff check engine/ tests/
pytest tests/
```

All tests must pass. Aim for meaningful test coverage — at minimum, test that your renderer instantiates, renders without errors, and that your data source returns valid entities.

### Test Conventions

- One test file per module: `test_<module>.py`
- Test the interface contract: `render()` doesn't throw, `hit_test()` returns bool, `fetch()` returns `list[Entity]`
- Use the `MockSource` for renderer tests — it provides deterministic-ish entity trees
- Name tests descriptively: `test_render_empty_entities`, `test_hit_test_inside_bounds`

---

## PR Workflow

1. **Fork** the repository on GitHub.
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/my-new-metaphor
   ```
3. **Make your changes.** Follow the code style above.
4. **Write tests.** Every new metaphor/source needs tests.
5. **Run the full suite:**
   ```bash
   black --check engine/ tests/
   ruff check engine/ tests/
   pytest tests/ -v
   ```
6. **Commit** with a clear message:
   ```bash
   git commit -m "feat: add ocean metaphor renderer"
   ```
7. **Push and open a PR** against `main`. Describe what your metaphor maps to, include a screenshot if possible.

### Branch Naming

- `feature/<name>` — new metaphor or data source
- `fix/<description>` — bug fixes
- `docs/<description>` — documentation only

### Commit Messages

Use conventional commits:

- `feat:` — new feature (metaphor, source, UI enhancement)
- `fix:` — bug fix
- `docs:` — documentation changes
- `test:` — test additions/fixes
- `refactor:` — code restructuring without behavior change

---

## Issue Templates

When opening an issue, please use the appropriate template:

### Bug Report
- What happened vs. what you expected
- Steps to reproduce
- Environment (OS, Python version, browser)
- Screenshots if visual

### Feature Request
- What problem this solves
- Proposed approach (optional)
- Alternatives considered

### New Metaphor Request
- Theme name and concept
- Entity mapping (what maps to what)
- Visual style description or reference images
- Why this metaphor is interesting/useful

---

## Code of Conduct

Be respectful. Assume good intent. Give constructive feedback.

We follow the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Report issues to the maintainers.

---

## Questions?

Open a GitHub Discussion or reach out in an issue. We're happy to help you get your first metaphor or data source working.
