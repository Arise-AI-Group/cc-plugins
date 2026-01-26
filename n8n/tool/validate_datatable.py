#!/usr/bin/env python3
"""
Data Table Node Validator

Validates Data Table node configurations in n8n workflow JSON files.
Reports missing required properties, invalid operations, and common mistakes.

Usage:
    ./run tool/validate_datatable.py <workflow.json>
    ./run tool/validate_datatable.py <workflow.json> --strict
    ./run tool/validate_datatable.py <workflow.json> --json
    ./run tool/validate_datatable.py <workflow.json> --suggestions

Examples:
    ./run tool/validate_datatable.py workflows/my_workflow.json
    ./run tool/validate_datatable.py templates/datatable-crud.json --strict
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of validating a single Data Table node."""
    node_name: str
    node_id: str
    resource: str
    operation: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


# Required properties by (resource, operation) combination
REQUIRED_PROPERTIES: Dict[Tuple[str, str], List[str]] = {
    # Row operations
    ("row", "insert"): ["dataTableId", "columns"],
    ("row", "get"): ["dataTableId"],
    ("row", "update"): ["dataTableId", "columns"],
    ("row", "upsert"): ["dataTableId", "columns"],
    ("row", "deleteRows"): ["dataTableId"],
    ("row", "rowExists"): ["dataTableId", "filters"],
    ("row", "rowNotExists"): ["dataTableId", "filters"],
    # Table operations
    ("table", "create"): ["tableName"],
    ("table", "list"): [],
    ("table", "update"): ["dataTableId", "newName"],
    ("table", "delete"): ["dataTableId"],
}

# Valid filter conditions
VALID_FILTER_CONDITIONS = [
    "eq", "ne", "gt", "gte", "lt", "lte",
    "contains", "isEmpty", "isNotEmpty", "isTrue", "isFalse"
]

# Conditions that don't require a keyValue
NO_VALUE_CONDITIONS = ["isEmpty", "isNotEmpty", "isTrue", "isFalse"]

# Valid column types for table creation
VALID_COLUMN_TYPES = ["string", "number", "boolean", "date"]

# Valid dataTableId modes
VALID_ID_MODES = ["list", "name", "id"]

# Default operations per resource
DEFAULT_OPERATIONS = {
    "row": "insert",
    "table": "list"
}


class DataTableValidator:
    """Validates Data Table nodes in n8n workflow JSON."""

    def __init__(self, strict: bool = False):
        """
        Initialize validator.

        Args:
            strict: If True, treat warnings as errors
        """
        self.strict = strict

    def validate_workflow(self, workflow: Dict) -> List[ValidationResult]:
        """
        Validate all Data Table nodes in a workflow.

        Args:
            workflow: Parsed workflow JSON

        Returns:
            List of ValidationResult for each Data Table node
        """
        results = []
        nodes = workflow.get("nodes", [])

        for node in nodes:
            node_type = node.get("type", "")
            if node_type == "n8n-nodes-base.dataTable":
                results.append(self.validate_node(node))

        return results

    def validate_node(self, node: Dict) -> ValidationResult:
        """
        Validate a single Data Table node.

        Args:
            node: Node configuration dict

        Returns:
            ValidationResult with errors, warnings, and suggestions
        """
        params = node.get("parameters", {})
        resource = params.get("resource", "row")
        operation = params.get("operation", DEFAULT_OPERATIONS.get(resource, "insert"))

        result = ValidationResult(
            node_name=node.get("name", "Unnamed"),
            node_id=node.get("id", "unknown"),
            resource=resource,
            operation=operation
        )

        # Validate resource/operation combination
        key = (resource, operation)
        if key not in REQUIRED_PROPERTIES:
            result.errors.append(
                f"Invalid resource/operation: {resource}/{operation}. "
                f"Valid operations for '{resource}': {self._get_valid_operations(resource)}"
            )
            return result

        # Check required properties
        required = REQUIRED_PROPERTIES[key]
        for prop in required:
            if prop not in params:
                result.errors.append(f"Missing required property: '{prop}'")
            elif params[prop] is None or params[prop] == "":
                result.errors.append(f"Required property '{prop}' is empty")
            else:
                # Validate property structure
                self._validate_property(prop, params[prop], resource, operation, result)

        # Operation-specific validations
        self._validate_operation_specific(params, resource, operation, result)

        # Check typeVersion
        type_version = node.get("typeVersion")
        if type_version is None:
            result.warnings.append("Missing typeVersion - should be 1.1")
        elif type_version < 1.1:
            result.warnings.append(f"Outdated typeVersion {type_version} - recommend 1.1")

        # Add suggestions for common patterns
        self._add_suggestions(params, resource, operation, result)

        return result

    def _validate_property(
        self,
        prop: str,
        value: Any,
        resource: str,
        operation: str,
        result: ValidationResult
    ) -> None:
        """Validate individual property structures."""

        if prop == "dataTableId":
            self._validate_data_table_id(value, result)

        elif prop == "columns" and resource == "row":
            self._validate_row_columns(value, result)

        elif prop == "columns" and resource == "table":
            self._validate_table_columns(value, result)

        elif prop == "filters":
            self._validate_filters(value, operation, result)

        elif prop == "tableName":
            if not isinstance(value, str) or not value.strip():
                result.errors.append("tableName must be a non-empty string")

        elif prop == "newName":
            if not isinstance(value, str) or not value.strip():
                result.errors.append("newName must be a non-empty string")

    def _validate_data_table_id(self, value: Any, result: ValidationResult) -> None:
        """Validate dataTableId property structure."""
        if not isinstance(value, dict):
            result.errors.append(
                "dataTableId must be object with 'mode' and 'value'. "
                "Example: {\"mode\": \"name\", \"value\": \"my_table\"}"
            )
            return

        mode = value.get("mode")
        table_value = value.get("value")

        if mode not in VALID_ID_MODES:
            result.errors.append(
                f"dataTableId.mode must be one of: {', '.join(VALID_ID_MODES)}. "
                f"Got: '{mode}'"
            )

        if mode in ["name", "id"] and not table_value:
            result.errors.append(
                f"dataTableId.value is required when mode is '{mode}'"
            )

    def _validate_row_columns(self, value: Any, result: ValidationResult) -> None:
        """Validate columns property for row operations (resourceMapper)."""
        if not isinstance(value, dict):
            result.errors.append(
                "columns must be object with 'mappingMode' and 'value'. "
                "Example: {\"mappingMode\": \"defineBelow\", \"value\": {\"field\": \"value\"}}"
            )
            return

        mapping_mode = value.get("mappingMode")
        columns_value = value.get("value")

        if mapping_mode == "defineBelow":
            if columns_value is None:
                result.errors.append(
                    "columns.value is required when mappingMode is 'defineBelow'"
                )
            elif not isinstance(columns_value, dict):
                result.errors.append(
                    "columns.value must be an object mapping column names to values"
                )
            elif len(columns_value) == 0:
                result.warnings.append(
                    "columns.value is empty - no data will be written"
                )

    def _validate_table_columns(self, value: Any, result: ValidationResult) -> None:
        """Validate columns property for table creation (fixedCollection)."""
        if not isinstance(value, dict):
            result.warnings.append(
                "columns should be object with 'column' array for table creation"
            )
            return

        columns = value.get("column", [])
        if not isinstance(columns, list):
            result.errors.append("columns.column must be an array")
            return

        for i, col in enumerate(columns):
            col_num = i + 1
            if not isinstance(col, dict):
                result.errors.append(f"Column {col_num}: must be an object")
                continue

            name = col.get("name")
            col_type = col.get("type")

            if not name:
                result.errors.append(f"Column {col_num}: missing 'name'")
            elif not isinstance(name, str):
                result.errors.append(f"Column {col_num}: 'name' must be a string")

            if not col_type:
                result.errors.append(f"Column {col_num}: missing 'type'")
            elif col_type not in VALID_COLUMN_TYPES:
                result.errors.append(
                    f"Column {col_num}: invalid type '{col_type}'. "
                    f"Valid types: {', '.join(VALID_COLUMN_TYPES)}"
                )

    def _validate_filters(
        self,
        value: Any,
        operation: str,
        result: ValidationResult
    ) -> None:
        """Validate filters property structure."""
        if not isinstance(value, dict):
            result.errors.append(
                "filters must be object with 'conditions' array. "
                "Example: {\"conditions\": [{\"keyName\": \"id\", \"condition\": \"eq\", \"keyValue\": \"123\"}]}"
            )
            return

        conditions = value.get("conditions", [])
        if not isinstance(conditions, list):
            result.errors.append("filters.conditions must be an array")
            return

        # rowExists and rowNotExists require at least one condition
        if operation in ["rowExists", "rowNotExists"] and len(conditions) < 1:
            result.errors.append(
                f"'{operation}' requires at least one filter condition"
            )

        for i, cond in enumerate(conditions):
            cond_num = i + 1
            if not isinstance(cond, dict):
                result.errors.append(f"Filter {cond_num}: must be an object")
                continue

            key_name = cond.get("keyName")
            condition = cond.get("condition")
            key_value = cond.get("keyValue")

            if not key_name:
                result.errors.append(f"Filter {cond_num}: missing 'keyName'")

            if not condition:
                result.errors.append(f"Filter {cond_num}: missing 'condition'")
            elif condition not in VALID_FILTER_CONDITIONS:
                result.errors.append(
                    f"Filter {cond_num}: invalid condition '{condition}'. "
                    f"Valid: {', '.join(VALID_FILTER_CONDITIONS)}"
                )

            # Check if keyValue is needed
            if condition and condition not in NO_VALUE_CONDITIONS:
                if key_value is None or key_value == "":
                    result.warnings.append(
                        f"Filter {cond_num}: 'keyValue' is empty for condition '{condition}'"
                    )

    def _validate_operation_specific(
        self,
        params: Dict,
        resource: str,
        operation: str,
        result: ValidationResult
    ) -> None:
        """Validate operation-specific requirements."""

        # Check matchType for operations that use it
        if operation in ["get", "update", "upsert", "deleteRows", "rowExists", "rowNotExists"]:
            match_type = params.get("matchType")
            if match_type and match_type not in ["anyCondition", "allConditions"]:
                result.errors.append(
                    f"matchType must be 'anyCondition' or 'allConditions'. Got: '{match_type}'"
                )

        # Check limit when returnAll is false
        if operation == "get":
            return_all = params.get("returnAll", False)
            limit = params.get("limit")
            if not return_all and limit is None:
                result.warnings.append(
                    "returnAll is false but no limit specified - defaults to 50"
                )

    def _add_suggestions(
        self,
        params: Dict,
        resource: str,
        operation: str,
        result: ValidationResult
    ) -> None:
        """Add helpful suggestions based on operation."""

        if operation == "insert":
            options = params.get("options", {})
            if not options.get("optimizeBulk"):
                result.suggestions.append(
                    "Set options.optimizeBulk: true for 5x faster batch inserts "
                    "(won't return inserted data)"
                )

        if operation in ["update", "deleteRows", "upsert"]:
            options = params.get("options", {})
            if not options.get("dryRun"):
                result.suggestions.append(
                    "Consider options.dryRun: true for testing destructive operations"
                )

        if operation in ["rowExists", "rowNotExists"]:
            result.suggestions.append(
                f"'{operation}' routes items: Output 0 = condition {'met' if operation == 'rowExists' else 'NOT met'}, "
                f"Output 1 = condition {'NOT met' if operation == 'rowExists' else 'met'}"
            )

    def _get_valid_operations(self, resource: str) -> str:
        """Get comma-separated list of valid operations for a resource."""
        ops = [op for (res, op) in REQUIRED_PROPERTIES.keys() if res == resource]
        return ", ".join(ops)


def format_results(
    results: List[ValidationResult],
    show_suggestions: bool = False
) -> str:
    """Format validation results for human-readable output."""
    if not results:
        return "No Data Table nodes found in workflow."

    lines = []
    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)

    for r in results:
        lines.append(f"\n{r.node_name} ({r.resource}/{r.operation})")
        lines.append("-" * 50)

        if r.errors:
            for e in r.errors:
                lines.append(f"  ERROR: {e}")

        if r.warnings:
            for w in r.warnings:
                lines.append(f"  WARNING: {w}")

        if show_suggestions and r.suggestions:
            for s in r.suggestions:
                lines.append(f"  TIP: {s}")

        if not r.errors and not r.warnings:
            lines.append("  OK")

    # Summary
    lines.append("")
    lines.append("=" * 50)
    lines.append(f"Summary: {len(results)} Data Table node(s)")
    lines.append(f"  Errors: {total_errors}")
    lines.append(f"  Warnings: {total_warnings}")

    if total_errors > 0:
        lines.append("\nValidation FAILED - fix errors before deploying")
    else:
        lines.append("\nValidation PASSED")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Validate Data Table nodes in n8n workflow JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    ./run tool/validate_datatable.py workflows/my_workflow.json
    ./run tool/validate_datatable.py templates/datatable-crud.json --strict
    ./run tool/validate_datatable.py workflows/*.json --json
        """
    )
    parser.add_argument(
        "workflow",
        help="Path to workflow JSON file"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (exit 1 if any warnings)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--suggestions",
        action="store_true",
        help="Include optimization suggestions in output"
    )

    args = parser.parse_args()

    # Load workflow
    workflow_path = Path(args.workflow)
    if not workflow_path.exists():
        print(f"Error: File not found: {workflow_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(workflow_path) as f:
            workflow = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {workflow_path}: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate
    validator = DataTableValidator(strict=args.strict)
    results = validator.validate_workflow(workflow)

    # Output
    if args.json:
        output = {
            "file": str(workflow_path),
            "nodes": [
                {
                    "name": r.node_name,
                    "id": r.node_id,
                    "resource": r.resource,
                    "operation": r.operation,
                    "valid": r.is_valid,
                    "errors": r.errors,
                    "warnings": r.warnings,
                    "suggestions": r.suggestions if args.suggestions else []
                }
                for r in results
            ],
            "summary": {
                "total_nodes": len(results),
                "errors": sum(len(r.errors) for r in results),
                "warnings": sum(len(r.warnings) for r in results),
                "valid": all(r.is_valid for r in results) if results else True
            }
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_results(results, show_suggestions=args.suggestions))

    # Exit code
    has_errors = any(len(r.errors) > 0 for r in results)
    has_warnings = any(len(r.warnings) > 0 for r in results)

    if has_errors:
        sys.exit(1)
    elif args.strict and has_warnings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
