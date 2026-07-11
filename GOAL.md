# Metaphors — Project Goal

## Vision

Build an open-source, pluggable infrastructure visualization platform that renders complex workloads (agents, containers, services, clusters, pipelines) through interchangeable visual metaphors. Think "Grafana meets Virtual Office" — real-time, interactive, and beautiful.

## Problem Statement

Infrastructure teams monitor their systems through dashboards full of charts, tables, and logs. This works, but it's cognitively expensive — you have to *read* to understand state, rather than *see* it. When something breaks at 3 AM, the engineer stares at 15 Grafana panels trying to piece together what's wrong.

**Metaphors** solves this by giving infrastructure a *spatial, visual representation* that leverages human pattern recognition. You don't read "service X is degraded" — you *see* a building flickering in the city. You don't parse "pod restart count is high" — you *see* a room lights switching on and off.

## Success Criteria

### Minimum Viable Product (MVP)
- [ ] Single "City" metaphor rendering real infrastructure
- [ ] At least 2 data sources: system processes + mock data
- [ ] Real-time updates via WebSocket (≤5s latency)
- [ ] Interactive: hover for tooltips, click for detail panel
- [ ] Works on localhost, accessible via browser
- [ ] All tests pass, clean code, documented

### Version 1.0
- [ ] 3 metaphors: City, Space Station, Garden
- [ ] 4 data sources: Processes, Docker, Kubernetes, Mock
- [ ] Metaphor switcher UI (dropdown or keyboard shortcut)
- [ ] Entity inspector panel (full details, metrics history)
- [ ] Keyboard navigation (vim keys or arrow keys)
- [ ] Responsive layout (works on tablet+)
- [ ] Docker Compose deployment
- [ ] README with screenshots and setup instructions

### Version 2.0 (Aspirational)
- [ ] Plugin system for custom metaphors (JS modules)
- [ ] Plugin system for custom data sources
- [ ] Historical playback (rewind to see past state)
- [ ] Alert overlay (PagerDuty, Slack integration)
- [ ] Multi-user / collaborative viewing
- [ ] Custom metaphor editor (drag-and-drop layout)
- [ ] Mobile-optimized touch interface
- [ ] AI-powered anomaly highlighting ("this looks weird")

## Core Principles

1. **Metaphor is the product.** The rendering is not just decoration — it's the interface. Each metaphor must convey information *faster* than a dashboard.

2. **Pluggable everything.** Data sources, metaphors, and entity types are all plugins. The core is small; the ecosystem is big.

3. **Real-time first.** Infrastructure changes constantly. The visualization must keep up — no manual refresh.

4. **Progressive complexity.** Start simple (one metaphor, one data source). Add complexity only when the simple version works.

5. **Developer experience.** Running locally should be trivial: `pip install -r requirements.txt && python server.py`. No Docker required for development.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend | Python FastAPI | Best ecosystem for infra tooling, async support, WebSocket built-in |
| Frontend | Vanilla JS + Canvas 2D | No build step, fast iteration, upgrade to WebGL if needed |
| Real-time | WebSocket | Lower latency than SSE, bidirectional for future interaction |
| Data format | JSON entities | Universal, debuggable, works with any source |
| Rendering | Plugin-based metaphors | Clean extension point, multiple views of same data |
| Testing | pytest + TDD | Catch regressions early, document behavior |

## Metaphor Design Philosophy

Each metaphor must satisfy three criteria:

1. **Instant recognition** — Within 2 seconds, you know what you're looking at
2. **Information density** — At least 3 dimensions of data visible simultaneously
3. **Emotional resonance** — Healthy = calm/beautiful, broken = urgent/alarming

### Metaphor Catalog (Planned)

| Metaphor | Mapping | Best For |
|----------|---------|----------|
| **City** | Buildings=services, height=CPU, color=health, windows=activity | General infrastructure, web services |
| **Space Station** | Modules=pods, docking=ingress, life support=health | Kubernetes, microservices |
| **Garden** | Plants=services, growth=health, weeds=unused, soil=resources | Organic systems, ML pipelines |
| **Factory** | Assembly lines=pipelines, stations=stages, output=throughput | CI/CD, data pipelines |
| **Office** | Desks=agents, meetings=collaboration, coffee=idle | AI agents, task queues |
| **Organism** | Heartbeat=uptime, circulation=data flow, immune=security | Distributed systems, mesh networks |

## Data Source Priority

| Source | Complexity | Value | Priority |
|--------|-----------|-------|----------|
| System processes | Low | Medium (always available) | P0 (MVP) |
| Mock data | Low | High (development) | P0 (MVP) |
| Docker | Medium | High (most common) | P1 (v1.0) |
| Kubernetes | High | Very high (enterprise) | P1 (v1.0) |
| Cloud APIs (AWS/GCP) | High | High (cloud-native) | P2 (v2.0) |
| Prometheus/Grafana | Medium | Medium (existing tooling) | P2 (v2.0) |
| GitHub Actions | Low | Medium (CI/CD) | P2 (v2.0) |
| Custom webhook | Low | High (extensibility) | P1 (v1.0) |

## Non-Goals

- **Not a monitoring replacement.** Metaphors is a *complement* to Grafana/Datadog, not a replacement. Click a building → open Grafana dashboard.
- **Not a control plane.** You can't restart pods from Metaphors (yet). It's read-only visualization.
- **Not mobile-first.** Tablet+ is the target. Phone screens are too small for spatial visualization.
- **Not a game.** It looks like a game, but it's a tool. Every visual element must convey information.

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Foundation | Week 1-2 | Entity model, data sources, City metaphor, tests |
| Real-time | Week 3-4 | WebSocket, frontend rendering, live updates |
| Polish | Week 5-6 | Inspector, switcher, Space Station + Garden metaphors |
| Docker/K8s | Week 7-8 | Docker data source, Kubernetes data source |
| v1.0 Release | Week 9-10 | Documentation, screenshots, Docker Compose, README |

## How We Work

### Task Workflow (5 Phases)

Every kanban task goes through this cycle:

```
BRANCH → PLAN → IMPLEMENT → REVIEW → (fix loop) → MERGE → DELETE BRANCH
```

| Phase | Agent | What Happens |
|-------|-------|--------------|
| **1. Branch** | Worker | Creates `task/<id>-<slug>` branch from `main` |
| **2. Plan** | Hermes | Analyzes task, reads codebase, creates implementation plan |
| **3. Implement** | agy | TDD: tests first, then code on feature branch. Commits to branch. |
| **4. Review** | Hermes | Reviews branch diff vs main. Verdict: PASS or FAIL |
| **5. Fix** | agy | If FAIL: fixes on branch, loops back to review (max 2 rounds) |
| **6. Merge** | Worker | Squash merge branch → main, delete branch |
| **7. Notify** | Worker | Posts summary to Discord |

### Review Loop

```
┌─────────────────────────────────────────────┐
│                                             │
▼                                             │
IMPLEMENT ──→ REVIEW ──→ PASS ──→ MERGE MAIN  │
                │                             │
                └──→ FAIL ──→ FIX ────────────┘
                              (max 2 rounds)
```

### Git Workflow

```
main ───────────────────────────────────────────── (clean)
  │
  └─→ task/t_abc1-my-feature ──→ plan ──→ implement ──→ review ──→ fix
                                                       │
                                                       ▼
main ←────────────────────── squash merge ←──────── PASS
```

- Each task gets its own feature branch: `task/<short-id>-<slug>`
- All work happens on the branch (never directly on main)
- Review compares branch diff against main
**Toolchain**

- **Hermes** handles planning, code review, and orchestration (Qwen3.7 Plus)
- **agy (Antigravity)** handles implementation tasks (Gemini-powered)
- **Cronjob** drives steady progress: one task per cycle, every 4 hours
- **Kanban** tracks all work items and their status
- **TDD** for all code — test first, then implement
- **Conservative usage** — one task per cron cycle, ~6 tasks/day max
