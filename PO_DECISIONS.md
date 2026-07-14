# Metaphors — Product Owner Decisions

## Product Vision

**Metaphors** is a niche infrastructure visualization platform that renders complex workloads as interactive 3D environments. Not a monitoring replacement — a **visualization layer** that sits on top of existing data sources (Prometheus, Datadog, Kubernetes) and makes infrastructure instantly legible.

## Target Market

**Primary:** Small-to-mid DevOps teams (5-50 engineers) who want an intuitive shared dashboard for their infrastructure. Teams that already have monitoring (Grafana, Datadog) but struggle with onboarding new engineers and communicating system state to non-technical stakeholders.

**Secondary:** Engineering managers and CTOs who need a "war room" display for their office — something that shows system health at a glance without requiring deep dashboard knowledge.

**NOT targeting:** Enterprise Fortune 500 (too crowded, too much red tape). Individual hobbyists (no budget).

## Competitive Position

| Competitor | What They Do | Our Advantage |
|------------|-------------|---------------|
| Grafana | Dense dashboards | We're visual and intuitive |
| Datadog | Full APM platform | We're lightweight and beautiful |
| Virtual Office | Agent visualization | We visualize infrastructure, not agents |
| eBPF tools | Kernel-level data | We're a presentation layer, not a data source |

## Pricing Strategy

- **Free tier:** Mock data source + 1 real data source, 1 metaphor
- **Pro ($29/mo per team):** All data sources, all metaphors, 3 users
- **Team ($99/mo):** Unlimited users, custom metaphors, API access
- **Enterprise ($499/mo):** SSO, RBAC, on-prem, SLA

## MVP Definition (Must Have for Launch)

1. **Real data sources** — Docker, Kubernetes, Prometheus (not just mock)
2. **3D visuals that look real** — not flat blocks
3. **Click entity → real metrics** — CPU, memory, status, logs link
4. **Alert integration** — webhook/Slack notifications on state change
5. **Documentation** — install guide, API docs, metaphor creation tutorial
6. **Landing page** — screenshots, pricing, install instructions

## Current State (July 15, 2026)

- ✅ 13,258 lines Python, 4,024 lines JS
- ✅ 333 tests passing
- ✅ 61 commits, 71 kanban tasks done
- ✅ Three.js migration started (3D rendering)
- ✅ systemd service running
- ❌ Visual quality: 3-5/10 (still not real enough)
- ❌ No real data sources (only mock + psutil)
- ❌ No alerting
- ❌ No landing page
- ❌ No real metrics in detail panel

## PO Directives for Dev Agent

1. **Visual quality is P0** — nothing else matters if it looks bad. The 3D city must look like a city, not blocks.
2. **Real data sources are P1** — mock data is fine for development, but the product needs Docker/K8s integration to be sellable.
3. **Don't build features nobody asked for** — no orchestra metaphor, no ship metaphor, no solar system. Focus on city, space station, garden. Three metaphors is enough for MVP.
4. **Screenshot every change** — if the dev agent can't prove it looks good with a screenshot, it didn't happen.
5. **Be honest in reviews** — if the visual is 3/10, say 3/10. Don't sugarcoat.
