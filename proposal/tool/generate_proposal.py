#!/usr/bin/env python3
"""
Validate and output proposal JSON for Google Slides text replacement.

This script validates a proposal JSON structure and outputs it.
The LLM orchestrator generates the content, this script ensures it's valid.

Usage:
    echo '<json>' | python generate_proposal.py
    # or
    python generate_proposal.py < proposal.json

Output:
    Validated JSON object printed to stdout, or error message to stderr
"""

import sys
import json


REQUIRED_FIELDS = [
    "proposal_title",
    "proposal_subtitle",
    "overview",
    "problem1",
    "problem2",
    "problem3",
    "problem4",
    "objective",
    "proposed_solution",
    "process_step1_title",
    "process_step1_desc",
    "process_step2_title",
    "process_step2_desc",
    "process_step3_title",
    "process_step3_desc",
    "deliverables",
    "benefit_metric1_title",
    "benefit_metric1_value",
    "benefit_metric1_desc",
    "benefit_metric2_title",
    "benefit_metric2_value",
    "benefit_metric2_desc",
    "benefit_metric3_title",
    "benefit_metric3_value",
    "benefit_metric3_desc"
]

METRIC_VALUE_FIELDS = [
    "benefit_metric1_value",
    "benefit_metric2_value",
    "benefit_metric3_value"
]


def validate_proposal(proposal: dict) -> tuple[bool, list[str]]:
    """
    Validate that all required fields are present and meet constraints.

    Returns:
        (is_valid, list of error messages)
    """
    errors = []

    # Check for missing fields
    for field in REQUIRED_FIELDS:
        if field not in proposal:
            errors.append(f"Missing field: {field}")
        elif not proposal[field]:
            errors.append(f"Empty field: {field}")

    # Check metric value lengths (max 6 chars)
    for field in METRIC_VALUE_FIELDS:
        if field in proposal and len(str(proposal[field])) > 6:
            errors.append(f"{field} exceeds 6 characters: '{proposal[field]}'")

    # Check for extra fields
    extra_fields = set(proposal.keys()) - set(REQUIRED_FIELDS)
    if extra_fields:
        errors.append(f"Unexpected fields: {extra_fields}")

    return len(errors) == 0, errors


def main():
    # Read JSON from stdin
    try:
        input_text = sys.stdin.read().strip()
        if not input_text:
            print("Error: No input provided. Pipe JSON to stdin.", file=sys.stderr)
            sys.exit(1)

        proposal = json.loads(input_text)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}", file=sys.stderr)
        sys.exit(1)

    # Validate
    is_valid, errors = validate_proposal(proposal)

    if not is_valid:
        print("Validation errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    # Output validated JSON
    print(json.dumps(proposal, indent=2))


if __name__ == "__main__":
    main()
