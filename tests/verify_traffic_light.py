"""Quick visual test for traffic light metaphor."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.metaphors.traffic_light import TrafficLightRenderer
import json

# Create sample entities representing a realistic intersection
entities = [
    {
        "id": "main-1st",
        "type": "cluster",
        "name": "Main St & 1st Ave",
        "state": "healthy",
        "parent": None,
        "children": ["main-st", "1st-ave"],
        "metrics": {}
    },
    {
        "id": "main-st",
        "type": "node",
        "name": "Main Street",
        "state": "running",
        "parent": "main-1st",
        "children": ["north-light", "south-light"],
        "metrics": {}
    },
    {
        "id": "1st-ave",
        "type": "node",
        "name": "1st Avenue",
        "state": "running",
        "parent": "main-1st",
        "children": ["east-light", "west-light"],
        "metrics": {}
    },
    {
        "id": "north-light",
        "type": "service",
        "name": "North Signal",
        "state": "healthy",
        "parent": "main-st",
        "children": ["north-red", "north-yellow", "north-green"],
        "metrics": {"cpu": 85}
    },
    {
        "id": "south-light",
        "type": "service",
        "name": "South Signal",
        "state": "critical",
        "parent": "main-st",
        "children": ["south-red", "south-yellow", "south-green"],
        "metrics": {"cpu": 95}
    },
    {
        "id": "east-light",
        "type": "service",
        "name": "East Signal",
        "state": "idle",
        "parent": "1st-ave",
        "children": ["east-red", "east-yellow", "east-green"],
        "metrics": {"cpu": 45}
    },
    {
        "id": "west-light",
        "type": "service",
        "name": "West Signal",
        "state": "warning",
        "parent": "1st-ave",
        "children": ["west-red", "west-yellow", "west-green"],
        "metrics": {"cpu": 70}
    },
    # Container lamps for north light
    {"id": "north-red", "type": "container", "name": "Red", "state": "critical", "parent": "north-light", "children": [], "metrics": {}},
    {"id": "north-yellow", "type": "container", "name": "Yellow", "state": "warning", "parent": "north-light", "children": [], "metrics": {}},
    {"id": "north-green", "type": "container", "name": "Green", "state": "healthy", "parent": "north-light", "children": [], "metrics": {}},
    # Container lamps for south light
    {"id": "south-red", "type": "container", "name": "Red", "state": "critical", "parent": "south-light", "children": [], "metrics": {}},
    {"id": "south-yellow", "type": "container", "name": "Yellow", "state": "warning", "parent": "south-light", "children": [], "metrics": {}},
    {"id": "south-green", "type": "container", "name": "Green", "state": "healthy", "parent": "south-light", "children": [], "metrics": {}},
    # Container lamps for east light
    {"id": "east-red", "type": "container", "name": "Red", "state": "critical", "parent": "east-light", "children": [], "metrics": {}},
    {"id": "east-yellow", "type": "container", "name": "Yellow", "state": "warning", "parent": "east-light", "children": [], "metrics": {}},
    {"id": "east-green", "type": "container", "name": "Green", "state": "healthy", "parent": "east-light", "children": [], "metrics": {}},
    # Container lamps for west light
    {"id": "west-red", "type": "container", "name": "Red", "state": "critical", "parent": "west-light", "children": [], "metrics": {}},
    {"id": "west-yellow", "type": "container", "name": "Yellow", "state": "warning", "parent": "west-light", "children": [], "metrics": {}},
    {"id": "west-green", "type": "container", "name": "Green", "state": "healthy", "parent": "west-light", "children": [], "metrics": {}},
]

renderer = TrafficLightRenderer()
print(f"Renderer: {renderer.name}")
print(f"Description: {renderer.description}")
print(f"Config: {json.dumps(renderer.config(), indent=2)}")

# Test layout computation
layout = renderer.compute_layout(entities, 800, 600)
print(f"\nLayout computed for {len(entities)} entities:")
for eid, pos in layout.items():
    entity = next(e for e in entities if e["id"] == eid)
    print(f"  {eid} ({entity['type']:9s}): x={pos['x']:6.1f} y={pos['y']:6.1f} w={pos['w']:6.1f} h={pos['h']:6.1f}")

# Test tooltip
tooltip = renderer.get_tooltip(entities[0], 0, 0)
print(f"\nTooltip for {entities[0]['name']}:")
print(tooltip)

# Test hit detection
pos = layout["north-light"]
cx, cy = pos["x"] + pos["w"]/2, pos["y"] + pos["h"]/2
hit = renderer.hit_test(entities[3], int(cx), int(cy))
print(f"\nHit test at center of north-light: {hit}")

print("\n✓ All basic functionality working")
