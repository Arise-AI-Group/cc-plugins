---
name: diagrams
description: This skill should be used when the user asks to "create a diagram", "generate flowchart", "make architecture diagram", "draw sequence diagram", "create ASCII diagram". Generates diagrams in Draw.io, Mermaid, and ASCII formats.
---

# Generate Diagram Directive

## When to Use This Directive

This directive applies when the user requests any diagram generation. The default output format is `.drawio` unless the user explicitly requests another format (mermaid, ASCII, etc.).

**Trigger phrases:** "generate diagram", "create a diagram", "make a flowchart", "visualize this process", "draw this out", etc.

## Tools Available

| Tool | Purpose | Input |
|------|---------|-------|
| `tool/generate_drawio.py` | Generate Draw.io XML | JSON file or stdin |
| `tool/generate_mermaid.py` | Generate Mermaid syntax | JSON file or stdin |
| `tool/migrate_ascii_to_mermaid.py` | Convert ASCII to Mermaid | Markdown file/directory |

## Goal

Generate diagrams from structured input or natural language descriptions, outputting to Draw.io, Mermaid, or other formats.

## Inputs

- **Diagram Type**: The kind of diagram (flowchart, process, hierarchy, swimlane, architecture, etc.)
- **Title**: Name for the diagram/file
- **Content**: Structured description of nodes, groups, and connections (or natural language)
- **Style Preferences** (optional): Color scheme, rounded vs sharp corners, etc.

## Process

### For Structured JSON Input

1. Validate JSON against schema (nodes, connections, optional groups)
2. Run appropriate tool:
   - Draw.io: `./run tool/generate_drawio.py input.json --output diagram.drawio`
   - Mermaid: `./run tool/generate_mermaid.py input.json --output diagram.md`
3. Return file path

### For Natural Language Input

1. Parse user description to identify:
   - Diagram type (flowchart, swimlane, hierarchy)
   - Nodes (steps, actions, decisions)
   - Groups/phases (if applicable)
   - Connections and their labels
2. Generate JSON structure matching the schema
3. Either pass to tool OR generate XML directly using patterns below

## JSON Input Schema

```json
{
  "type": "flowchart|swimlane",
  "title": "Diagram Title",
  "direction": "TD|LR",
  "groups": [
    {"id": "g1", "label": "Phase 1", "color": "blue"}
  ],
  "nodes": [
    {"id": "n1", "label": "Step 1", "group": "g1", "shape": "rectangle|diamond|ellipse"}
  ],
  "connections": [
    {"from": "n1", "to": "n2", "label": "Yes", "style": "solid|dashed"}
  ]
}
```

## Outputs

- `.drawio` file in the workspace that opens directly in Draw.io desktop or web app
- `.md` file with Mermaid code block for Markdown embedding

## Edge Cases

- If no color scheme specified, use the default palette (blue, green, orange, red)
- If layout is ambiguous, default to top-to-bottom flow
- For large diagrams (>20 nodes), increase canvas size accordingly
- Escape special XML characters in node labels (`&`, `<`, `>`, `"`, `'`)

---

## Draw.io XML Structure

Draw.io files are XML with this structure:

```xml
<mxfile host="Electron" agent="..." version="...">
  <diagram name="Diagram Name" id="unique-id">
    <mxGraphModel dx="1306" dy="898" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1200" pageHeight="800" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- All diagram elements go here -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### Cell Types

**1. Basic Shape (Rectangle/Box)**
```xml
<mxCell id="unique-id" value="Label Text" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#fff;strokeColor=#6c8ebf;" parent="1" vertex="1">
  <mxGeometry x="20" y="45" width="200" height="40" as="geometry" />
</mxCell>
```

**2. Swimlane/Group Container**
```xml
<mxCell id="group-id" value="GROUP TITLE" style="swimlane;horizontal=1;startSize=30;fillColor=#dae8fc;strokeColor=#6c8ebf;rounded=1;fontStyle=1;fontSize=14;" parent="1" vertex="1">
  <mxGeometry x="40" y="40" width="240" height="200" as="geometry" />
</mxCell>
<!-- Child elements use parent="group-id" and relative positioning -->
```

**3. Connector/Arrow**
```xml
<mxCell id="arrow-id" style="edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2;strokeColor=#666;" parent="1" source="source-id" target="target-id" edge="1">
  <mxGeometry relative="1" as="geometry" />
</mxCell>
```

**4. Labeled Arrow**
```xml
<mxCell id="labeled-arrow" value="Arrow Label" style="edgeStyle=orthogonalEdgeStyle;rounded=1;..." parent="1" source="source-id" target="target-id" edge="1">
  <mxGeometry relative="1" as="geometry" />
</mxCell>
```

**5. Arrow with Custom Path (for loops/cycles)**
```xml
<mxCell id="cycle-arrow" value="Cycle Label" style="edgeStyle=orthogonalEdgeStyle;rounded=1;dashed=1;dashPattern=8 8;" parent="1" source="source-id" target="target-id" edge="1">
  <mxGeometry relative="1" as="geometry">
    <Array as="points">
      <mxPoint x="1000" y="280" />
      <mxPoint x="160" y="280" />
    </Array>
  </mxGeometry>
</mxCell>
```

---

## Default Color Palette

| Purpose | Fill Color | Stroke Color | Use Case |
|---------|------------|--------------|----------|
| Blue | `#dae8fc` | `#6c8ebf` | Phase 1, Primary, Acquire |
| Green | `#d5e8d4` | `#82b366` | Phase 2, Success, Propose |
| Orange | `#ffe6cc` | `#d79b00` | Phase 3, Warning, Deliver |
| Red | `#f8cecc` | `#b85450` | Phase 4, Error, Close |
| Purple | `#e1d5e7` | `#9673a6` | Loops, Cycles, Special |
| Gray | `#f5f5f5` | `#666666` | Neutral, Connectors |
| White | `#ffffff` | (inherit) | Child nodes in groups |

---

## Common Style Properties

**Shapes:**
- `rounded=1` - Rounded corners
- `rounded=0` - Sharp corners
- `whiteSpace=wrap` - Text wrapping
- `html=1` - Enable HTML in labels
- `fontStyle=1` - Bold text
- `fontStyle=2` - Italic text
- `fontSize=14` - Font size

**Connectors:**
- `edgeStyle=orthogonalEdgeStyle` - Right-angle connections
- `edgeStyle=elbowEdgeStyle` - Single elbow
- `curved=1` - Curved lines
- `strokeWidth=2` - Line thickness
- `dashed=1;dashPattern=8 8` - Dashed line
- `endArrow=classic` - Arrow head (default)
- `endArrow=none` - No arrow head

**Swimlanes:**
- `swimlane` - Container type
- `horizontal=1` - Horizontal orientation
- `startSize=30` - Header height

---

## Layout Guidelines

**Positioning:**
- Grid size: 10px (align to grid)
- Standard node: 200w x 40h
- Group/swimlane: 240w x 200h
- Horizontal spacing between groups: 40px gap
- Vertical spacing within groups: 10px gap
- Canvas default: 1200w x 800h

**Hierarchy:**
- `id="0"` - Root (always present)
- `id="1"` - Default parent (always present, `parent="0"`)
- Groups: `parent="1"`
- Nodes in groups: `parent="group-id"`, positions relative to group
- Connectors: `parent="1"`, reference source/target by id

---

## Mermaid Syntax Reference

### Basic Flowchart
```mermaid
flowchart TD
    A[Start] --> B{Decision?}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E
```

### Shapes
- `[Text]` - Rectangle
- `{Text}` - Diamond (decision)
- `([Text])` - Rounded rectangle (start/end)
- `[[Text]]` - Subroutine
- `((Text))` - Circle

### Arrow Styles
- `-->` - Solid arrow
- `-.->` - Dashed arrow
- `-->|label|` - Labeled arrow

### Subgraphs (Swimlanes)
```mermaid
flowchart LR
    subgraph Phase1[Phase 1: Initiate]
        A[Step 1]
        B[Step 2]
    end
    subgraph Phase2[Phase 2: Execute]
        C[Step 3]
    end
    A --> B --> C
```

---

## Quick Generation Patterns

**Simple Flowchart (no groups):**
```json
{
  "type": "flowchart",
  "title": "Simple Flow",
  "nodes": [
    {"id": "start", "label": "Start", "shape": "ellipse"},
    {"id": "process", "label": "Process"},
    {"id": "end", "label": "End", "shape": "ellipse"}
  ],
  "connections": [
    {"from": "start", "to": "process"},
    {"from": "process", "to": "end"}
  ]
}
```

**Swimlane Process (with groups):**
```json
{
  "type": "swimlane",
  "title": "Business Process",
  "groups": [
    {"id": "phase1", "label": "PHASE 1", "color": "blue"},
    {"id": "phase2", "label": "PHASE 2", "color": "green"}
  ],
  "nodes": [
    {"id": "step1", "label": "Step 1", "group": "phase1"},
    {"id": "step2", "label": "Step 2", "group": "phase1"},
    {"id": "step3", "label": "Step 3", "group": "phase2"}
  ],
  "connections": [
    {"from": "step1", "to": "step2"},
    {"from": "step2", "to": "step3"}
  ]
}
```

---

## Learnings & Edge Cases

*(Updated as issues are discovered)*

- Draw.io expects `mxCell id="0"` and `mxCell id="1"` as the first two cells (mandatory root structure)
- Child elements in groups use coordinates relative to the group's origin, not the canvas
- Connector `source` and `target` must reference existing cell IDs
- For arrows that need to wrap around (like cycle/loop arrows), use explicit `<Array as="points">` waypoints

