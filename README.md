# Metaphors

**Infrastructure visualization through interchangeable metaphors.**

See your infrastructure the way your brain wants to — not as rows in a table, but as living, breathing scenes. When a service degrades, you *see* a building flicker. When a pod restarts, you *see* a light switch on and off.

> Grafana tells you what happened. Metaphors shows you what's happening *right now*.

<!-- Hero screenshot placeholder — replace with actual screenshot -->
![Metaphors — City View](docs/images/hero.png)

---

## Features

- **6 visual metaphors** — city, space station, factory, kitchen, construction site, garden
- **Real-time updates** — WebSocket-driven, ≤3s refresh cycle
- **Pluggable architecture** — add custom metaphors or data sources by implementing a base class
- **Interactive** — hover for tooltips, click for detail panel, minimap navigation
- **Zoom & pan** — full canvas navigation with keyboard and button controls
- **Metaphor switcher** — dropdown + fade transitions + localStorage persistence
- **Zero build step** — vanilla JS + Canvas 2D, no npm/webpack required

---

## Quick Start

```bash
git clone https://github.com/your-org/metaphors.git
cd metaphors
pip install -r requirements.txt
python3 server.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Supported Data Sources

| Source | Status | Description |
|--------|--------|-------------|
| **Mock** | ✅ Stable | Simulated clusters, nodes, services, containers with randomized metrics |
| **Processes** | ✅ Stable | Live system processes via `psutil` — top 30 by CPU, grouped by name |
| **Docker** | 🔜 Planned | Container inspection and resource metrics |
| **Kubernetes** | 🔜 Planned | Pod/service/cluster hierarchy from kubectl API |

---

## Metaphor Gallery

| Metaphor | Emoji | Mapping (Cluster → Container) | Best For |
|----------|-------|-------------------------------|----------|
| **City** | 🏙️ | District → Block → Building → Floor | General-purpose infra overview |
| **Space Station** | 🛸 | Ring → Module → Pod → Compartment | Microservice architectures |
| **Factory** | 🏭 | Floor → Workstation → Machine → Belt | Batch/pipeline workloads |
| **Kitchen** | 🍳 | Restaurant → Station → Chef → Pot | Team/service ownership mapping |
| **Construction Site** | 🏗️ | Project → Floor → Room → Wall | Deployment/rollout progress |
| **Solar System** | 🪐 | Galaxy → Star → Planet → Moon | Large-scale multi-cluster |
| **Orchestra** | 🎻 | Section → Chair → Musician → Instrument | Harmonious service dependencies |
| **Naval Ship** | 🚢 | Fleet → Section → Station → Compartment | Hierarchical command structures |
| **Garden** | 🌱 | Bed → Row → Plant → Branch | Organic growth / auto-scaling |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser (Canvas 2D)               │
│  ┌───────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Metaphor  │  │ Minimap  │  │  Detail Panel    │ │
│  │ Renderer  │  │          │  │  (click entity)  │ │
│  └─────▲─────┘  └──────────┘  └──────────────────┘ │
│        │ WebSocket                                   │
└────────┼────────────────────────────────────────────┘
         │
┌────────┼────────────────────────────────────────────┐
│        │         FastAPI Server (server.py)          │
│  ┌─────┴─────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  Entity    │  │   Metaphor   │  │  REST API   │ │
│  │ Scheduler  │  │   Registry   │  │  /api/*     │ │
│  └─────▲─────┘  └──────────────┘  └─────────────┘ │
│        │                                            │
│  ┌─────┴──────────────────┐                        │
│  │     Data Sources        │                        │
│  │  ┌──────┐ ┌──────────┐ │                        │
│  │  │ Mock │ │ Process  │ │  (+ Docker, K8s...)    │ │
│  │  └──────┘ └──────────┘ │                        │
│  └────────────────────────┘                        │
└────────────────────────────────────────────────────┘
```

**Data flow:** Sources → EntityScheduler (3s tick) → WebSocket broadcast → Canvas render

---

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PORT` | `8000` | Server port |
| `HOST` | `0.0.0.0` | Bind address |
| `UPDATE_INTERVAL` | `3.0` | Entity refresh interval (seconds) |
| `LOG_LEVEL` | `info` | Logging level (debug/info/warning/error) |

---

## Project Structure

```
metaphors/
├── server.py              # FastAPI app + WebSocket + REST API
├── engine/
│   ├── entities.py        # Entity model (Cluster/Node/Service/Container)
│   ├── scheduler.py       # EntityScheduler — polls sources, broadcasts
│   ├── sources/           # Data source plugins
│   │   ├── base.py        # DataSource ABC
│   │   ├── mock.py        # Simulated workload generator
│   │   └── processes.py   # Live system process scanner (psutil)
│   └── metaphors/         # Visual metaphor plugins
│       ├── base.py        # MetaphorRenderer ABC + MetaphorRegistry
│       ├── city.py        # 🏙️ Neon cyberpunk cityscape
│       ├── space.py       # 🛸 Radial space station
│       ├── factory.py     # 🏭 Assembly line factory
│       ├── kitchen.py     # 🍳 Restaurant kitchen
│       ├── construction.py# 🏗️ Blueprint construction site
│       ├── garden.py      # 🌱 Organic garden ecosystem
├── static/                # Frontend (vanilla JS + Canvas)
│   ├── index.html
│   ├── main.js
│   └── style.css
├── tests/                 # pytest test suite
├── requirements.txt
└── README.md
```

---

## Adding a Custom Metaphor

1. Create `engine/metaphors/my_metaphor.py`
2. Subclass `MetaphorRenderer` from `engine.metaphors.base`
3. Implement `render()`, `get_tooltip()`, and `hit_test()`
4. Register in `server.py`: `registry.register("my_metaphor", MyRenderer())`

That's it. No config files, no build step.

---

## Development

```bash
# Run tests
pytest tests/ -v

# Run with auto-reload
uvicorn server:app --reload --port 8000
```

---

## Contributing

Contributions welcome! Areas we're looking for:

- New data sources (Docker, Kubernetes, Prometheus, cloud APIs)
- New metaphors (underwater reef? volcano? ant colony?)
- Performance optimizations (WebGL renderer, virtual scrolling)
- Documentation and translations

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-metaphor`)
3. Add tests for new code
4. Open a Pull Request

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <sub>Built with FastAPI, Canvas 2D, and too much coffee.</sub>
</p>
