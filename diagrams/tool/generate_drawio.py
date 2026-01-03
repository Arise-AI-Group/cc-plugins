#!/usr/bin/env python3
"""
Generate Draw.io diagrams from structured JSON input.

Usage:
    ./run tool/generate_drawio.py input.json --output diagram.drawio
    ./run tool/generate_drawio.py --stdin < input.json
    ./run tool/generate_drawio.py input.json --validate

Input JSON Schema:
{
  "type": "flowchart|swimlane",
  "title": "Diagram Title",
  "direction": "TD|LR",
  "groups": [{"id": "g1", "label": "Phase 1", "color": "blue"}],
  "nodes": [{"id": "n1", "label": "Step", "group": "g1", "shape": "rectangle|diamond|ellipse"}],
  "connections": [{"from": "n1", "to": "n2", "label": "Yes", "style": "solid|dashed"}]
}
"""

import sys
import json
import argparse
import uuid
import html
from pathlib import Path
from typing import Dict, List, Any, Optional


# Color palette matching extras/runbooks/generate_diagram.md
COLOR_PALETTE = {
    "blue": {"fill": "#dae8fc", "stroke": "#6c8ebf"},
    "green": {"fill": "#d5e8d4", "stroke": "#82b366"},
    "orange": {"fill": "#ffe6cc", "stroke": "#d79b00"},
    "red": {"fill": "#f8cecc", "stroke": "#b85450"},
    "purple": {"fill": "#e1d5e7", "stroke": "#9673a6"},
    "gray": {"fill": "#f5f5f5", "stroke": "#666666"},
    "white": {"fill": "#ffffff", "stroke": "#666666"},
}

# Layout constants
GRID_SIZE = 10
NODE_WIDTH = 200
NODE_HEIGHT = 40
GROUP_WIDTH = 240
GROUP_HEIGHT = 200
GROUP_HEADER_HEIGHT = 30
GROUP_GAP = 40
NODE_GAP = 10
CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 800


def escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return html.escape(str(text), quote=True)


def generate_id() -> str:
    """Generate a unique cell ID."""
    return str(uuid.uuid4())[:8]


def get_color(color_name: str) -> Dict[str, str]:
    """Get color values from palette."""
    return COLOR_PALETTE.get(color_name.lower(), COLOR_PALETTE["blue"])


def build_node_style(shape: str = "rectangle", color: str = "white", rounded: bool = True) -> str:
    """Build style string for a node."""
    colors = get_color(color)

    base_style = f"whiteSpace=wrap;html=1;fillColor={colors['fill']};strokeColor={colors['stroke']};"

    if shape == "diamond":
        return f"rhombus;{base_style}"
    elif shape == "ellipse":
        return f"ellipse;{base_style}"
    else:  # rectangle
        rounded_val = "1" if rounded else "0"
        return f"rounded={rounded_val};{base_style}"


def build_group_style(color: str = "blue") -> str:
    """Build style string for a swimlane/group."""
    colors = get_color(color)
    return (
        f"swimlane;horizontal=1;startSize={GROUP_HEADER_HEIGHT};"
        f"fillColor={colors['fill']};strokeColor={colors['stroke']};"
        f"rounded=1;fontStyle=1;fontSize=14;"
    )


def build_edge_style(style: str = "solid") -> str:
    """Build style string for a connector."""
    base = "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2;strokeColor=#666;"

    if style == "dashed":
        return f"{base}dashed=1;dashPattern=8 8;"
    return base


def calculate_layout(data: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """Calculate positions for all elements."""
    positions = {}
    direction = data.get("direction", "TD")
    groups = data.get("groups", [])
    nodes = data.get("nodes", [])

    if groups:
        # Swimlane layout
        group_x = 40
        for i, group in enumerate(groups):
            gid = group["id"]
            positions[gid] = {
                "x": group_x,
                "y": 40,
                "width": GROUP_WIDTH,
                "height": GROUP_HEIGHT,
            }

            # Position nodes within this group
            group_nodes = [n for n in nodes if n.get("group") == gid]
            node_y = GROUP_HEADER_HEIGHT + NODE_GAP
            for node in group_nodes:
                positions[node["id"]] = {
                    "x": 20,  # Relative to group
                    "y": node_y,
                    "width": NODE_WIDTH,
                    "height": NODE_HEIGHT,
                }
                node_y += NODE_HEIGHT + NODE_GAP

            # Adjust group height based on content
            if group_nodes:
                positions[gid]["height"] = max(
                    GROUP_HEIGHT,
                    node_y + NODE_GAP
                )

            group_x += GROUP_WIDTH + GROUP_GAP
    else:
        # Simple flowchart layout
        if direction == "LR":
            # Left to right
            node_x = 40
            for node in nodes:
                positions[node["id"]] = {
                    "x": node_x,
                    "y": 100,
                    "width": NODE_WIDTH,
                    "height": NODE_HEIGHT,
                }
                node_x += NODE_WIDTH + GROUP_GAP
        else:
            # Top to bottom (default)
            node_y = 40
            for node in nodes:
                positions[node["id"]] = {
                    "x": 100,
                    "y": node_y,
                    "width": NODE_WIDTH,
                    "height": NODE_HEIGHT,
                }
                node_y += NODE_HEIGHT + GROUP_GAP

    return positions


def generate_xml(data: Dict[str, Any]) -> str:
    """Generate Draw.io XML from structured data."""
    title = escape_xml(data.get("title", "Diagram"))
    diagram_id = generate_id()

    positions = calculate_layout(data)

    # Calculate canvas size
    max_x = max((p.get("x", 0) + p.get("width", 0) for p in positions.values()), default=CANVAS_WIDTH)
    max_y = max((p.get("y", 0) + p.get("height", 0) for p in positions.values()), default=CANVAS_HEIGHT)
    canvas_width = max(CANVAS_WIDTH, max_x + 100)
    canvas_height = max(CANVAS_HEIGHT, max_y + 100)

    cells = []

    # Root cells (required)
    cells.append('<mxCell id="0" />')
    cells.append('<mxCell id="1" parent="0" />')

    # ID mapping for connections
    id_map = {}

    # Generate groups
    for group in data.get("groups", []):
        gid = group["id"]
        cell_id = generate_id()
        id_map[gid] = cell_id

        pos = positions[gid]
        style = build_group_style(group.get("color", "blue"))
        label = escape_xml(group.get("label", gid))

        cells.append(
            f'<mxCell id="{cell_id}" value="{label}" style="{style}" '
            f'parent="1" vertex="1">\n'
            f'  <mxGeometry x="{pos["x"]}" y="{pos["y"]}" '
            f'width="{pos["width"]}" height="{pos["height"]}" as="geometry" />\n'
            f'</mxCell>'
        )

    # Generate nodes
    for node in data.get("nodes", []):
        nid = node["id"]
        cell_id = generate_id()
        id_map[nid] = cell_id

        pos = positions[nid]
        shape = node.get("shape", "rectangle")
        color = node.get("color", "white")
        style = build_node_style(shape, color)
        label = escape_xml(node.get("label", nid))

        # Determine parent
        parent_id = "1"
        if node.get("group") and node["group"] in id_map:
            parent_id = id_map[node["group"]]

        cells.append(
            f'<mxCell id="{cell_id}" value="{label}" style="{style}" '
            f'parent="{parent_id}" vertex="1">\n'
            f'  <mxGeometry x="{pos["x"]}" y="{pos["y"]}" '
            f'width="{pos["width"]}" height="{pos["height"]}" as="geometry" />\n'
            f'</mxCell>'
        )

    # Generate connections
    for conn in data.get("connections", []):
        source_id = id_map.get(conn["from"])
        target_id = id_map.get(conn["to"])

        if not source_id or not target_id:
            continue

        cell_id = generate_id()
        style = build_edge_style(conn.get("style", "solid"))
        label = escape_xml(conn.get("label", ""))

        value_attr = f'value="{label}" ' if label else ""

        cells.append(
            f'<mxCell id="{cell_id}" {value_attr}style="{style}" '
            f'parent="1" source="{source_id}" target="{target_id}" edge="1">\n'
            f'  <mxGeometry relative="1" as="geometry" />\n'
            f'</mxCell>'
        )

    # Assemble full XML
    cells_xml = "\n        ".join(cells)

    xml = f'''<mxfile host="Electron" modified="{generate_id()}" agent="agentic-diagrams" version="1.0.0">
  <diagram name="{title}" id="{diagram_id}">
    <mxGraphModel dx="1306" dy="898" grid="1" gridSize="{GRID_SIZE}" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{int(canvas_width)}" pageHeight="{int(canvas_height)}" math="0" shadow="0">
      <root>
        {cells_xml}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>'''

    return xml


def validate_schema(data: Dict[str, Any]) -> List[str]:
    """Validate input JSON against schema. Returns list of errors."""
    errors = []

    if not isinstance(data, dict):
        return ["Input must be a JSON object"]

    # Check required fields
    if "nodes" not in data and "groups" not in data:
        errors.append("Input must have 'nodes' or 'groups'")

    # Validate nodes
    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        errors.append("'nodes' must be an array")
    else:
        node_ids = set()
        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                errors.append(f"Node {i} must be an object")
                continue
            if "id" not in node:
                errors.append(f"Node {i} missing 'id'")
            else:
                if node["id"] in node_ids:
                    errors.append(f"Duplicate node id: {node['id']}")
                node_ids.add(node["id"])

    # Validate groups
    groups = data.get("groups", [])
    if not isinstance(groups, list):
        errors.append("'groups' must be an array")
    else:
        group_ids = set()
        for i, group in enumerate(groups):
            if not isinstance(group, dict):
                errors.append(f"Group {i} must be an object")
                continue
            if "id" not in group:
                errors.append(f"Group {i} missing 'id'")
            else:
                if group["id"] in group_ids:
                    errors.append(f"Duplicate group id: {group['id']}")
                group_ids.add(group["id"])

    # Validate connections
    connections = data.get("connections", [])
    if not isinstance(connections, list):
        errors.append("'connections' must be an array")
    else:
        all_ids = set(n.get("id") for n in nodes) | set(g.get("id") for g in groups)
        for i, conn in enumerate(connections):
            if not isinstance(conn, dict):
                errors.append(f"Connection {i} must be an object")
                continue
            if "from" not in conn:
                errors.append(f"Connection {i} missing 'from'")
            elif conn["from"] not in all_ids:
                errors.append(f"Connection {i} 'from' references unknown id: {conn['from']}")
            if "to" not in conn:
                errors.append(f"Connection {i} missing 'to'")
            elif conn["to"] not in all_ids:
                errors.append(f"Connection {i} 'to' references unknown id: {conn['to']}")

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Generate Draw.io diagrams from JSON input"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to input JSON file"
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read JSON from stdin"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: diagrams/<title>.drawio)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate input only, don't generate output"
    )

    args = parser.parse_args()

    # Read input
    if args.stdin:
        data = json.load(sys.stdin)
    elif args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        parser.error("Either input file or --stdin required")
        return

    # Validate
    errors = validate_schema(data)
    if errors:
        print("Validation errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    if args.validate:
        print("Input is valid", file=sys.stderr)
        print(json.dumps({"valid": True, "nodes": len(data.get("nodes", [])), "connections": len(data.get("connections", []))}))
        return

    # Generate XML
    xml = generate_xml(data)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        title = data.get("title", "diagram").lower().replace(" ", "_")
        output_path = Path("diagrams") / f"{title}.drawio"

    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml)

    print(f"Generated: {output_path}", file=sys.stderr)
    print(json.dumps({
        "output": str(output_path),
        "nodes": len(data.get("nodes", [])),
        "groups": len(data.get("groups", [])),
        "connections": len(data.get("connections", []))
    }))


if __name__ == "__main__":
    main()
