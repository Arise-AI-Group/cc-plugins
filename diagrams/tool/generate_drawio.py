#!/usr/bin/env python3
"""
Generate Draw.io diagrams from structured JSON input.

Usage:
    ./run tool/generate_drawio.py input.json --output diagram.drawio
    ./run tool/generate_drawio.py input.json --style dark-modern --output diagram.drawio
    ./run tool/generate_drawio.py --stdin < input.json
    ./run tool/generate_drawio.py input.json --validate
    ./run tool/generate_drawio.py --list-styles

Input JSON Schema:
{
  "style": "classic|dark-modern",
  "type": "flowchart|swimlane",
  "title": "Diagram Title",
  "direction": "TD|LR",
  "groups": [{"id": "g1", "label": "Phase 1", "color": "blue"}],
  "nodes": [{"id": "n1", "label": "Step", "group": "g1", "shape": "rectangle|diamond|ellipse|cylinder|cloud|document|hexagon|actor|process|parallelogram|callout|task|event|gateway"}],
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


# Resolve styles directory relative to this script
STYLES_DIR = Path(__file__).resolve().parent.parent / "styles"

# Fallback palette used when no style file is loaded
FALLBACK_PALETTE = {
    "blue": {"fill": "#dae8fc", "stroke": "#6c8ebf", "font": "#333333"},
    "green": {"fill": "#d5e8d4", "stroke": "#82b366", "font": "#333333"},
    "orange": {"fill": "#ffe6cc", "stroke": "#d79b00", "font": "#333333"},
    "red": {"fill": "#f8cecc", "stroke": "#b85450", "font": "#333333"},
    "purple": {"fill": "#e1d5e7", "stroke": "#9673a6", "font": "#333333"},
    "gray": {"fill": "#f5f5f5", "stroke": "#666666", "font": "#333333"},
    "white": {"fill": "#ffffff", "stroke": "#666666", "font": "#333333"},
}

FALLBACK_STYLE = {
    "name": "Classic",
    "canvas": {"background": "#ffffff", "shadow": False},
    "palette": FALLBACK_PALETTE,
    "defaults": {
        "node_font_size": 12,
        "group_font_size": 14,
        "edge_color": "#666666",
        "edge_width": 2,
        "rounded": True,
    },
}

# Layout constants
GRID_SIZE = 10
NODE_WIDTH = 200
NODE_HEIGHT = 40
GROUP_WIDTH = 280
GROUP_HEIGHT = 200
GROUP_HEADER_HEIGHT = 30
GROUP_GAP = 60
NODE_GAP = 20
# Extra vertical space for shapes with labels below (event, gateway, actor)
LABEL_BELOW_PADDING = 25
CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 800

# Supported shapes
VALID_SHAPES = {
    "rectangle", "diamond", "ellipse", "cylinder",
    "cloud", "document", "hexagon", "actor",
    "callout", "process", "parallelogram",
    "task", "event", "gateway",
}

# Per-shape dimension overrides (shapes that look bad at default 200x40)
SHAPE_DIMENSIONS = {
    "actor":    {"width": 40, "height": 60},
    "cloud":    {"width": 200, "height": 80},
    "document": {"width": 200, "height": 60},
    "hexagon":  {"width": 120, "height": 60},
    "task":     {"width": 120, "height": 80},
    "event":    {"width": 50, "height": 50},
    "gateway":  {"width": 50, "height": 50},
}

# Valid BPMN markers/symbols for stencil shapes
VALID_TASK_MARKERS = {"script", "send", "manual", "service", "user", "abstract"}
VALID_EVENT_SYMBOLS = {"message", "timer", "error", "conditional", "terminate", "general"}
VALID_EVENT_OUTLINES = {"standard", "boundInt", "end", "throwing"}
VALID_GATEWAY_TYPES = {"exclusive", "parallel", "inclusive"}

# Shapes that render labels below the shape (need extra vertical spacing)
SHAPES_WITH_BOTTOM_LABEL = {"event", "gateway", "actor"}

# Active style (set by load_style)
_active_style: Dict[str, Any] = FALLBACK_STYLE


def load_style(name: str) -> Dict[str, Any]:
    """Load a style definition from the styles directory."""
    global _active_style

    style_path = STYLES_DIR / f"{name}.json"
    if not style_path.exists():
        available = list_styles()
        print(f"Style '{name}' not found. Available: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    with open(style_path, "r", encoding="utf-8") as f:
        _active_style = json.load(f)

    return _active_style


def list_styles() -> List[str]:
    """List available style names."""
    if not STYLES_DIR.exists():
        return []
    return sorted(p.stem for p in STYLES_DIR.glob("*.json"))


def escape_xml(text: str) -> str:
    """Escape special XML characters."""
    return html.escape(str(text), quote=True)


def generate_id() -> str:
    """Generate a unique cell ID."""
    return str(uuid.uuid4())[:8]


def get_color(color_name: str) -> Dict[str, str]:
    """Get color values from active style palette."""
    palette = _active_style.get("palette", FALLBACK_PALETTE)
    return palette.get(color_name.lower(), palette.get("blue", FALLBACK_PALETTE["blue"]))


def build_node_style(shape: str = "rectangle", color: str = "white",
                     rounded: Optional[bool] = None, node_data: Optional[Dict] = None) -> str:
    """Build style string for a node."""
    colors = get_color(color)
    defaults = _active_style.get("defaults", {})

    if rounded is None:
        rounded = defaults.get("rounded", True)

    font_color = colors.get("font", "#333333")
    font_size = defaults.get("node_font_size", 12)
    font_style = defaults.get("node_font_style", 0)
    stroke_width = defaults.get("node_stroke_width", 1)
    node_shadow = defaults.get("node_shadow", False)
    arc_size = defaults.get("arc_size", 0)

    base_style = (
        f"whiteSpace=wrap;html=1;"
        f"fillColor={colors['fill']};strokeColor={colors['stroke']};"
        f"fontColor={font_color};fontSize={font_size};"
        f"strokeWidth={stroke_width};"
    )
    if font_style:
        base_style += f"fontStyle={font_style};"
    if node_shadow:
        base_style += "shadow=1;"

    # BPMN stencil shapes
    if shape == "task":
        return _build_bpmn_task_style(color, node_data)
    elif shape == "event":
        return _build_bpmn_event_style(color, node_data)
    elif shape == "gateway":
        return _build_bpmn_gateway_style(color, node_data)
    elif shape == "diamond":
        return f"rhombus;{base_style}"
    elif shape == "ellipse":
        return f"ellipse;{base_style}"
    elif shape == "cylinder":
        return (
            f"shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=15;"
            f"{base_style}"
        )
    elif shape == "cloud":
        return f"shape=cloud;{base_style}"
    elif shape == "document":
        return f"shape=document;{base_style}"
    elif shape == "hexagon":
        return f"shape=hexagon;perimeter=hexagonPerimeter2;size=0.25;{base_style}"
    elif shape == "actor":
        return f"shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;{base_style}"
    elif shape == "callout":
        return f"shape=callout;perimeter=calloutPerimeter;size=30;position=0.5;{base_style}"
    elif shape == "process":
        return f"shape=process;size=0.1;{base_style}"
    elif shape == "parallelogram":
        return f"shape=parallelogram;perimeter=parallelogramPerimeter;size=0.15;{base_style}"
    else:  # rectangle
        rounded_val = "1" if rounded else "0"
        arc = f"arcSize={arc_size};" if arc_size and rounded else ""
        return f"rounded={rounded_val};{arc}{base_style}"


def _build_bpmn_task_style(color: str = "white", node_data: Optional[Dict] = None) -> str:
    """Build style for mxgraph.bpmn.task shapes."""
    colors = get_color(color)
    marker = (node_data or {}).get("marker", "abstract")
    return (
        f"shape=mxgraph.bpmn.task;rectStyle=rounded;size=10;"
        f"taskMarker={marker};"
        f"html=1;whiteSpace=wrap;"
        f"fillColor={colors['fill']};strokeColor={colors['stroke']};"
        f"fontColor={colors.get('font', '#333333')};"
    )


def _build_bpmn_event_style(color: str = "white", node_data: Optional[Dict] = None) -> str:
    """Build style for mxgraph.bpmn.event shapes."""
    colors = get_color(color)
    data = node_data or {}
    symbol = data.get("symbol", "general")
    outline = data.get("outline", "standard")
    return (
        f"shape=mxgraph.bpmn.event;html=1;"
        f"verticalLabelPosition=bottom;verticalAlign=top;align=center;"
        f"perimeter=ellipsePerimeter;outlineConnect=0;aspect=fixed;"
        f"outline={outline};symbol={symbol};"
        f"fillColor={colors['fill']};strokeColor={colors['stroke']};"
        f"fontColor={colors.get('font', '#333333')};"
    )


def _build_bpmn_gateway_style(color: str = "white", node_data: Optional[Dict] = None) -> str:
    """Build style for mxgraph.bpmn.gateway2 shapes."""
    colors = get_color(color)
    gw_type = (node_data or {}).get("gateway_type", "exclusive")
    return (
        f"shape=mxgraph.bpmn.gateway2;html=1;"
        f"verticalLabelPosition=bottom;verticalAlign=top;align=center;"
        f"perimeter=rhombusPerimeter;outlineConnect=0;"
        f"outline=none;symbol=none;gwType={gw_type};"
        f"fillColor={colors['fill']};strokeColor={colors['stroke']};"
        f"fontColor={colors.get('font', '#333333')};"
    )


def build_group_style(color: str = "blue") -> str:
    """Build style string for a swimlane/group."""
    colors = get_color(color)
    defaults = _active_style.get("defaults", {})
    font_color = colors.get("font", "#333333")
    font_size = defaults.get("group_font_size", 14)
    stroke_width = defaults.get("node_stroke_width", 1)
    node_shadow = defaults.get("node_shadow", False)

    shadow_str = "shadow=1;" if node_shadow else ""
    return (
        f"swimlane;horizontal=1;startSize={GROUP_HEADER_HEIGHT};"
        f"fillColor={colors['fill']};strokeColor={colors['stroke']};"
        f"fontColor={font_color};strokeWidth={stroke_width};"
        f"rounded=1;fontStyle=1;fontSize={font_size};{shadow_str}"
    )


def build_edge_style(style: str = "solid") -> str:
    """Build style string for a connector."""
    defaults = _active_style.get("defaults", {})
    edge_color = defaults.get("edge_color", "#666666")
    edge_width = defaults.get("edge_width", 2)
    label_color = defaults.get("edge_label_color", "")
    label_bg = defaults.get("edge_label_bg", "")

    base = (
        f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
        f"jettySize=auto;html=1;"
        f"strokeWidth={edge_width};strokeColor={edge_color};"
    )
    if label_color:
        base += f"fontColor={label_color};"
    if label_bg:
        base += f"labelBackgroundColor={label_bg};"

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
        # Swimlane layout — two passes: position nodes, then equalize group heights
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
                shape = node.get("shape", "rectangle")
                dims = SHAPE_DIMENSIONS.get(shape, {})
                nw = dims.get("width", NODE_WIDTH)
                nh = dims.get("height", NODE_HEIGHT)

                # Center node horizontally within group
                node_x = max(20, (GROUP_WIDTH - nw) // 2)

                positions[node["id"]] = {
                    "x": node_x,
                    "y": node_y,
                    "width": nw,
                    "height": nh,
                }

                # Extra padding for shapes with labels below the shape
                extra = LABEL_BELOW_PADDING if shape in SHAPES_WITH_BOTTOM_LABEL else 0
                node_y += nh + NODE_GAP + extra

            # Calculate required group height based on content
            if group_nodes:
                positions[gid]["height"] = max(
                    GROUP_HEIGHT,
                    node_y + NODE_GAP
                )

            group_x += GROUP_WIDTH + GROUP_GAP

        # Second pass: equalize all group heights to the tallest
        max_group_height = max(
            positions[g["id"]]["height"] for g in groups
        )
        for group in groups:
            positions[group["id"]]["height"] = max_group_height
    else:
        # Simple flowchart layout
        if direction == "LR":
            # Left to right — center nodes vertically on a common baseline
            # First pass: find the tallest node to determine baseline
            max_h = NODE_HEIGHT
            for node in nodes:
                dims = SHAPE_DIMENSIONS.get(node.get("shape", "rectangle"), {})
                nh = dims.get("height", NODE_HEIGHT)
                if nh > max_h:
                    max_h = nh
            baseline_y = 100

            node_x = 40
            for node in nodes:
                shape = node.get("shape", "rectangle")
                dims = SHAPE_DIMENSIONS.get(shape, {})
                nw = dims.get("width", NODE_WIDTH)
                nh = dims.get("height", NODE_HEIGHT)
                # Center vertically relative to tallest node
                node_y = baseline_y + (max_h - nh) // 2
                # Shapes with bottom labels need space below
                extra = LABEL_BELOW_PADDING if shape in SHAPES_WITH_BOTTOM_LABEL else 0
                positions[node["id"]] = {
                    "x": node_x,
                    "y": node_y,
                    "width": nw,
                    "height": nh,
                }
                node_x += nw + GROUP_GAP
        else:
            # Top to bottom (default) — center nodes horizontally
            # First pass: find widest node
            max_w = NODE_WIDTH
            for node in nodes:
                dims = SHAPE_DIMENSIONS.get(node.get("shape", "rectangle"), {})
                nw = dims.get("width", NODE_WIDTH)
                if nw > max_w:
                    max_w = nw
            center_x = 100 + max_w // 2

            node_y = 40
            for node in nodes:
                shape = node.get("shape", "rectangle")
                dims = SHAPE_DIMENSIONS.get(shape, {})
                nw = dims.get("width", NODE_WIDTH)
                nh = dims.get("height", NODE_HEIGHT)
                # Center horizontally relative to widest node
                node_x = center_x - nw // 2
                positions[node["id"]] = {
                    "x": node_x,
                    "y": node_y,
                    "width": nw,
                    "height": nh,
                }
                extra = LABEL_BELOW_PADDING if shape in SHAPES_WITH_BOTTOM_LABEL else 0
                node_y += nh + GROUP_GAP + extra

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

    # Detect backward cross-group connections — need extra space below for routing
    groups_list = data.get("groups", [])
    nodes_list = data.get("nodes", [])
    if groups_list:
        _node_grp = {n["id"]: n["group"] for n in nodes_list if n.get("group")}
        _grp_ord = {g["id"]: i for i, g in enumerate(groups_list)}
        for conn in data.get("connections", []):
            sg = _node_grp.get(conn.get("from"))
            tg = _node_grp.get(conn.get("to"))
            if sg and tg and sg != tg and _grp_ord.get(sg, 0) > _grp_ord.get(tg, 0):
                canvas_height += 80  # Space for backward-routing below swimlanes
                break

    # Canvas settings from style
    canvas = _active_style.get("canvas", {})
    background = canvas.get("background", "#ffffff")
    shadow = "1" if canvas.get("shadow", False) else "0"

    # Background attribute (only emit if non-white)
    bg_attr = ""
    if background.lower() != "#ffffff":
        bg_attr = f' background="{background}"'

    cells = []

    # Root cells (required)
    cells.append('<mxCell id="0" />')
    cells.append(f'<mxCell id="1" parent="0" />')

    # If dark background, add a background rectangle so it renders in Draw.io
    if background.lower() != "#ffffff":
        bg_id = generate_id()
        cells.append(
            f'<mxCell id="{bg_id}" value="" '
            f'style="rounded=0;whiteSpace=wrap;html=1;fillColor={background};strokeColor=none;opacity=100;" '
            f'parent="1" vertex="1">\n'
            f'  <mxGeometry x="0" y="0" width="{int(canvas_width)}" height="{int(canvas_height)}" as="geometry" />\n'
            f'</mxCell>'
        )

    # ID mapping for connections
    id_map = {}

    # Build group color map so nodes can inherit their parent group's color
    group_color_map = {}
    for group in data.get("groups", []):
        group_color_map[group["id"]] = group.get("color", "blue")

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
        # Inherit color from parent group if node doesn't specify its own
        color = node.get("color")
        if color is None and node.get("group"):
            color = group_color_map.get(node["group"], "white")
        elif color is None:
            color = "white"
        style = build_node_style(shape, color, node_data=node)
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

    # Build node-to-group mapping for smart edge routing
    node_group_map = {}
    for node in data.get("nodes", []):
        if node.get("group"):
            node_group_map[node["id"]] = node["group"]

    group_order = {g["id"]: i for i, g in enumerate(data.get("groups", []))}

    # Generate connections with smart routing
    for conn in data.get("connections", []):
        source_id = id_map.get(conn["from"])
        target_id = id_map.get(conn["to"])

        if not source_id or not target_id:
            continue

        cell_id = generate_id()
        style = build_edge_style(conn.get("style", "solid"))
        label = escape_xml(conn.get("label", ""))
        value_attr = f'value="{label}" ' if label else ""

        source_group = node_group_map.get(conn["from"])
        target_group = node_group_map.get(conn["to"])
        waypoints = None
        edge_parent = "1"

        if source_group and target_group:
            if source_group == target_group:
                # Intra-group: use group as edge parent for obstacle avoidance
                edge_parent = id_map[source_group]

                # Detect connections that skip over intermediate nodes
                src_pos = positions[conn["from"]]
                tgt_pos = positions[conn["to"]]
                y_lo = min(src_pos["y"], tgt_pos["y"])
                y_hi = max(src_pos["y"], tgt_pos["y"])

                has_obstacle = False
                for n in data.get("nodes", []):
                    if (n.get("group") == source_group
                            and n["id"] != conn["from"]
                            and n["id"] != conn["to"]):
                        ny = positions[n["id"]]["y"]
                        if y_lo < ny < y_hi:
                            has_obstacle = True
                            break

                if has_obstacle:
                    # Route to the right side of the group to bypass obstacles
                    route_x = GROUP_WIDTH - 15
                    style += (
                        "exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                        "entryX=1;entryY=0.5;entryDx=0;entryDy=0;"
                    )
                    waypoints = [
                        (route_x, src_pos["y"] + src_pos["height"] // 2),
                        (route_x, tgt_pos["y"] + tgt_pos["height"] // 2),
                    ]
            else:
                src_idx = group_order.get(source_group, 0)
                tgt_idx = group_order.get(target_group, 0)

                if src_idx < tgt_idx:
                    # Forward cross-group: exit right side, enter left side
                    style += (
                        "exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                        "entryX=0;entryY=0.5;entryDx=0;entryDy=0;"
                    )
                else:
                    # Backward cross-group: route below swimlanes, enter from left
                    style += (
                        "exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                        "entryX=0;entryY=0.5;entryDx=0;entryDy=0;"
                    )
                    max_bottom = max(
                        positions[g["id"]]["y"] + positions[g["id"]]["height"]
                        for g in data.get("groups", [])
                    )
                    route_y = max_bottom + 40

                    src_gpos = positions[source_group]
                    src_npos = positions[conn["from"]]
                    tgt_gpos = positions[target_group]
                    tgt_npos = positions[conn["to"]]

                    src_abs_x = src_gpos["x"] + src_npos["x"] + src_npos["width"] // 2
                    tgt_left_x = tgt_gpos["x"] - 20  # Left of target group
                    tgt_abs_y = tgt_gpos["y"] + tgt_npos["y"] + tgt_npos["height"] // 2

                    waypoints = [
                        (src_abs_x, route_y),       # Below source
                        (tgt_left_x, route_y),      # Below target group
                        (tgt_left_x, tgt_abs_y),    # Up to target's Y level
                    ]

        if waypoints:
            points_xml = "\n".join(
                f'          <mxPoint x="{x}" y="{y}" />'
                for x, y in waypoints
            )
            cells.append(
                f'<mxCell id="{cell_id}" {value_attr}style="{style}" '
                f'parent="{edge_parent}" source="{source_id}" target="{target_id}" edge="1">\n'
                f'  <mxGeometry relative="1" as="geometry">\n'
                f'    <Array as="points">\n{points_xml}\n'
                f'    </Array>\n'
                f'  </mxGeometry>\n'
                f'</mxCell>'
            )
        else:
            cells.append(
                f'<mxCell id="{cell_id}" {value_attr}style="{style}" '
                f'parent="{edge_parent}" source="{source_id}" target="{target_id}" edge="1">\n'
                f'  <mxGeometry relative="1" as="geometry" />\n'
                f'</mxCell>'
            )

    # Assemble full XML
    cells_xml = "\n        ".join(cells)

    xml = f'''<mxfile host="Electron" modified="{generate_id()}" agent="agentic-diagrams" version="1.0.0">
  <diagram name="{title}" id="{diagram_id}">
    <mxGraphModel dx="1306" dy="898" grid="1" gridSize="{GRID_SIZE}" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{int(canvas_width)}" pageHeight="{int(canvas_height)}" math="0" shadow="{shadow}"{bg_attr}>
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

            shape = node.get("shape", "rectangle")
            nid = node.get("id", i)
            if shape not in VALID_SHAPES:
                errors.append(f"Node '{nid}' has unknown shape: '{shape}'")

            # Validate BPMN stencil shape fields
            if shape == "task":
                marker = node.get("marker", "abstract")
                if marker not in VALID_TASK_MARKERS:
                    errors.append(f"Node '{nid}' has unknown task marker: '{marker}'")
            elif shape == "event":
                symbol = node.get("symbol", "general")
                if symbol not in VALID_EVENT_SYMBOLS:
                    errors.append(f"Node '{nid}' has unknown event symbol: '{symbol}'")
                outline = node.get("outline", "standard")
                if outline not in VALID_EVENT_OUTLINES:
                    errors.append(f"Node '{nid}' has unknown event outline: '{outline}'")
            elif shape == "gateway":
                gw_type = node.get("gateway_type", "exclusive")
                if gw_type not in VALID_GATEWAY_TYPES:
                    errors.append(f"Node '{nid}' has unknown gateway type: '{gw_type}'")

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
        "--style", "-s",
        default=None,
        help="Style preset name (default: classic). Use --list-styles to see available styles."
    )
    parser.add_argument(
        "--list-styles",
        action="store_true",
        help="List available style presets and exit"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate input only, don't generate output"
    )

    args = parser.parse_args()

    # List styles mode
    if args.list_styles:
        styles = list_styles()
        if not styles:
            print("No styles found", file=sys.stderr)
            sys.exit(1)
        for name in styles:
            style_path = STYLES_DIR / f"{name}.json"
            with open(style_path, "r", encoding="utf-8") as f:
                info = json.load(f)
            desc = info.get("description", "")
            print(f"  {name}: {desc}", file=sys.stderr)
        print(json.dumps({"styles": styles}))
        return

    # Read input
    if args.stdin:
        data = json.load(sys.stdin)
    elif args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        parser.error("Either input file or --stdin required")
        return

    # Load style: CLI flag > JSON field > default
    style_name = args.style or data.get("style", "classic")
    load_style(style_name)

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

    print(f"Generated: {output_path} (style: {style_name})", file=sys.stderr)
    print(json.dumps({
        "output": str(output_path),
        "style": style_name,
        "nodes": len(data.get("nodes", [])),
        "groups": len(data.get("groups", [])),
        "connections": len(data.get("connections", []))
    }))


if __name__ == "__main__":
    main()
