#!/usr/bin/env python3
"""
Generate Mermaid diagrams from structured JSON input.

Usage:
    ./run tool/generate_mermaid.py input.json --output diagram.md
    ./run tool/generate_mermaid.py --stdin < input.json
    ./run tool/generate_mermaid.py input.json --raw

Input JSON Schema:
{
  "type": "flowchart|swimlane",
  "title": "Diagram Title",
  "direction": "TD|LR",
  "groups": [{"id": "g1", "label": "Phase 1"}],
  "nodes": [{"id": "n1", "label": "Step", "group": "g1", "shape": "rectangle|diamond|ellipse"}],
  "connections": [{"from": "n1", "to": "n2", "label": "Yes", "style": "solid|dashed"}]
}
"""

import sys
import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Any


def sanitize_id(id_str: str) -> str:
    """Sanitize ID for Mermaid (alphanumeric and underscores only)."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", str(id_str))


def escape_label(text: str) -> str:
    """Escape special characters in labels for Mermaid."""
    # Mermaid uses quotes for labels with special chars
    text = str(text)
    if any(c in text for c in ['[', ']', '(', ')', '{', '}', '"', '<', '>']):
        # Use quotes and escape internal quotes
        text = text.replace('"', "'")
        return f'"{text}"'
    return text


def format_node(node: Dict[str, Any]) -> str:
    """Format a node with its shape."""
    nid = sanitize_id(node["id"])
    label = escape_label(node.get("label", node["id"]))
    shape = node.get("shape", "rectangle")

    if shape == "diamond":
        return f"{nid}{{{label}}}"
    elif shape == "ellipse":
        return f"{nid}([{label}])"
    else:  # rectangle
        return f"{nid}[{label}]"


def format_connection(conn: Dict[str, Any], nodes_defined: set) -> tuple:
    """Format a connection. Returns (line, source_node_def, target_node_def)."""
    source = sanitize_id(conn["from"])
    target = sanitize_id(conn["to"])
    label = conn.get("label", "")
    style = conn.get("style", "solid")

    # Arrow style
    if style == "dashed":
        arrow = "-.->"
    else:
        arrow = "-->"

    # Add label if present
    if label:
        arrow = f"{arrow}|{escape_label(label)}|"

    return f"    {source} {arrow} {target}"


def generate_mermaid(data: Dict[str, Any]) -> str:
    """Generate Mermaid syntax from structured data."""
    direction = data.get("direction", "TD")
    groups = data.get("groups", [])
    nodes = data.get("nodes", [])
    connections = data.get("connections", [])

    lines = []

    # Diagram type declaration
    lines.append(f"flowchart {direction}")

    # Track which nodes have been defined
    nodes_defined = set()

    if groups:
        # Swimlane/subgraph layout
        for group in groups:
            gid = sanitize_id(group["id"])
            label = escape_label(group.get("label", group["id"]))

            lines.append(f"    subgraph {gid}[{label}]")

            # Add nodes in this group
            group_nodes = [n for n in nodes if n.get("group") == group["id"]]
            for node in group_nodes:
                node_def = format_node(node)
                lines.append(f"        {node_def}")
                nodes_defined.add(node["id"])

            lines.append("    end")
            lines.append("")

        # Add any ungrouped nodes
        ungrouped = [n for n in nodes if not n.get("group")]
        for node in ungrouped:
            node_def = format_node(node)
            lines.append(f"    {node_def}")
            nodes_defined.add(node["id"])
    else:
        # Simple flowchart - define nodes first
        for node in nodes:
            node_def = format_node(node)
            lines.append(f"    {node_def}")
            nodes_defined.add(node["id"])

    # Add blank line before connections
    if connections:
        lines.append("")

    # Add connections
    for conn in connections:
        line = format_connection(conn, nodes_defined)
        lines.append(line)

    return "\n".join(lines)


def validate_schema(data: Dict[str, Any]) -> List[str]:
    """Validate input JSON against schema. Returns list of errors."""
    errors = []

    if not isinstance(data, dict):
        return ["Input must be a JSON object"]

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

    # Validate connections
    connections = data.get("connections", [])
    if not isinstance(connections, list):
        errors.append("'connections' must be an array")
    else:
        all_ids = set(n.get("id") for n in nodes)
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
        description="Generate Mermaid diagrams from JSON input"
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
        help="Output file path (default: diagrams/<title>.md)"
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw Mermaid syntax (no markdown fence)"
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

    # Generate Mermaid
    mermaid = generate_mermaid(data)

    # Wrap in markdown if not raw
    if not args.raw:
        title = data.get("title", "Diagram")
        output_content = f"# {title}\n\n```mermaid\n{mermaid}\n```\n"
    else:
        output_content = mermaid

    # Determine output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_content)
        print(f"Generated: {output_path}", file=sys.stderr)
        print(json.dumps({
            "output": str(output_path),
            "nodes": len(data.get("nodes", [])),
            "connections": len(data.get("connections", []))
        }))
    else:
        # Print to stdout
        print(output_content)


if __name__ == "__main__":
    main()
