# Visual Guidelines — Making Metaphors Look Real

## The Problem

Current renderers produce flat colored rectangles. That's a diagram, not a visualization. Virtual Office works because it feels like a *place* — you want to be there. Three.js demos work because they have *depth, light, and motion*.

## Core Principle

> **Every metaphor should feel like a place you could visit.**

Not "colored boxes representing services" but "a building in a city where someone is working."

---

## Visual Anatomy of a Good Metaphor

### 1. Depth Through Layering (4+ layers minimum)

```
Layer 0: Sky / Background gradient
Layer 1: Far buildings / distant elements
Layer 2: Ground / roads / terrain
Layer 3: Main entities (buildings, ships, plants)
Layer 4: Foreground details (rain, particles, UI)
Layer 5: HUD overlay (tooltips, labels)
```

Virtual Office does this: background wall → floor → furniture → agents → lighting → UI.

### 2. Ambient Lighting

Every scene needs a light source that creates mood:
- **Cyberpunk city:** Neon signs + window glow + moonlight
- **Space station:** Emergency lights + control panel glow + starlight
- **Garden:** Sun position (time-based) + dew drops + fireflies at night
- **Factory:** Overhead fluorescents + welding sparks + molten metal glow

Light creates emotion. Cold blue = calm. Warm orange = busy. Red = urgent.

### 3. Animated Micro-Details

Static scenes are boring. Add constant subtle motion:
- **City:** Blinking neon signs, flickering windows, rain drops, steam vents, car headlights
- **Space:** Rotating radar dish, blinking status lights, floating debris, docking clamps
- **Garden:** Swaying leaves, drifting petals, buzzing bees, flowing water
- **Factory:** Spinning gears, conveyor belt motion, steam puffs, sparks

These don't convey data — they make the scene *alive*.

### 4. Environmental Context

Entities don't exist in a vacuum:
- **City:** Roads between buildings, sidewalks, streetlights, parked cars, trash cans
- **Space:** Vacuum between modules, airlocks, docking ports, solar panels
- **Garden:** Soil between plants, pathways, fence, garden tools, water feature
- **Factory:** Floor between stations, pipes, cables, safety signs, fire extinguishers

### 5. Architectural Detail

Buildings/machines/plants need *structure*, not just boxes:

```
BAD:  ┌─────────┐
      │  ▓▓▓▓▓  │  ← Colored rectangle
      │  ▓▓▓▓▓  │
      └─────────┘

GOOD: ┌─┬─────┬─┐  ← Windows with frames
      │█│ ░░░ │█│  ← Ventilation unit
      ├─┼─────┼─┤  ← Floor separator
      │█│ ░░░ │█│  ← Different window pattern
      │█│ ░░░ │█│
      └─┴─────┴─┘  ← Foundation with details
         ║║║        ← Pipes/utility connections
```

### 6. Color Strategy

Not every pixel should be saturated. Use a **60-30-10** rule:
- **60% dark/neutral** (backgrounds, ground, inactive elements)
- **30% mid-tone** (building walls, structural elements)
- **10% bright/accent** (neon, windows, alerts, active states)

Virtual Office: 60% dark wood/shadows, 30% furniture/walls, 10% lamp glow/agent colors.

### 7. Typography

Labels need to be readable and styled:
- **Font:** Monospace or pixel font for cyberpunk, serif for garden, sans-serif for space
- **Size:** Small (8px) for details, Medium (12px) for labels, Large (16px) for titles
- **Color:** Bright on dark background, with subtle glow/shadow for readability
- **Animation:** Subtle pulse for active, static for idle

---

## City Metaphor — Specific Guidelines

### Building Anatomy

```
      ╔═══╗ ← Antenna/satellite dish
    ┌─╨───╨─┐ ← Roof mechanicals (HVAC units)
    │ ░░░░░ │ ← Penthouse (different color)
    ├───────┤ ← Floor line
    │ ▓ ▓ ▓ │ ← Windows (lit = active, dark = idle)
    │ ▓ ▓ ▓ │
    ├───────┤
    │ ▓ ▓ ▓ │
    │ ▓ ▓ ▓ │
    ├───────┤
    │ ENTRY │ ← Ground floor (entrance, awning)
    └───┬───┘
    ════╧════ ← Sidewalk with details
```

### Window Patterns
- **Healthy:** Warm yellow (#fbbf24) glow, some flickering
- **Warning:** Orange pulsing, some dark
- **Critical:** Red strobe, sparks
- **Stopped:** All dark, maybe one security light

### Road System
- Roads between building blocks
- Lane markings (dashed center line)
- Crosswalks at intersections
- Moving car headlights (small dots)
- Traffic lights at intersections

### Neon Signs
- Building names in glowing text
- Color matches state
- Subtle flicker animation
- Reflection on wet ground

### Atmospheric Effects
- Rain (vertical lines, semi-transparent)
- Fog (gradient from bottom, reduces visibility)
- Steam (from vents, rising)
- Haze (city glow in the sky)

---

## Implementation Priority

1. **Buildings with architectural detail** (not rectangles)
2. **Proper road network** (not flat ground)
3. **Window lighting patterns** (not uniform color)
4. **Neon signs with text** (not just color)
5. **Rain/atmospheric effects** (subtle, not overwhelming)
6. **Moving traffic particles** (car headlights)
7. **Ground reflections** (wet road effect)
8. **Sky gradient with stars** (depth)

---

## Reference Images

Study these for inspiration:
- **Blade Runner 2049** — cyberpunk city lighting
- **Akira** — Neo-Tokyo at night
- **SimCity 2000** — isometric city detail
- **VA-11 Hall-A** — pixel art cyberpunk bar
- **The Owl House** — fantasy lighting techniques

---

## Anti-Patterns (What NOT to Do)

❌ Colored rectangles as buildings
❌ Uniform window patterns (all same color)
❌ No ground detail (just flat background)
❌ No atmospheric effects
❌ No animation (static scene)
❌ Labels that overlap entities
❌ Colors that clash (neon green next to neon pink)
❌ Too many bright colors (no visual hierarchy)
❌ No depth (everything on same plane)

---

## Color Palettes

### Cyberpunk City
```
Background:    #0a0a1a (deep space blue)
Ground:        #0d0d22 (dark navy)
Road:          #111128 (slightly lighter)
Building wall: #1a1a3e (dark purple-blue)
Window lit:    #fbbf24 (warm yellow)
Window dark:   #1a1a2e (near black)
Neon pink:     #ff00ff
Neon cyan:     #00ffff
Neon yellow:   #ffff00
Healthy:       #4ade80 (green)
Warning:       #fbbf24 (amber)
Critical:      #ef4444 (red)
```

### Space Station
```
Background:    #000011 (deep space)
Module:        #2a2a3e (dark metal)
Panel lit:     #44aaff (cool blue)
Panel warning: #ff8800 (orange)
Panel critical:#ff2222 (red)
Stars:         #ffffff (white, varying opacity)
Corridor:      #1a1a2e (dark interior)
Docking:       #00ff88 (green ring)
```

### Garden
```
Background:    #87ceeb (sky blue) → #1a0a2e (night)
Soil:          #3d2817 (rich brown)
Grass:         #228b22 (forest green)
Leaf healthy:  #4ade80 (bright green)
Leaf warning:  #fbbf24 (yellow)
Leaf dead:     #8b4513 (brown)
Flower:        #ff69b4 (pink)
Water:         #4488ff (blue, animated)
Sun:           #ffd700 (gold)
```
