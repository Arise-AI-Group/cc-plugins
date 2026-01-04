#!/usr/bin/env python3
"""
Central test runner for cc-plugins.

Usage:
    # Run all Level 1 (dry) tests
    python tests/run_tests.py --level 1

    # Run all Level 2 (read-only) tests
    python tests/run_tests.py --level 2

    # Run all Level 3 (write) tests
    python tests/run_tests.py --level 3

    # Run all tests for a specific plugin
    python tests/run_tests.py --plugin slack

    # Run specific test level for a plugin
    python tests/run_tests.py --plugin notion --level 2

    # Run with coverage
    python tests/run_tests.py --level 1 --coverage

    # Run and stop on first failure
    python tests/run_tests.py --level 1 --fail-fast
"""
import argparse
import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

PLUGINS = [
    "slack",
    "notion",
    "n8n",
    "infrastructure",
    "leads",
    "diagrams",
    "sop",
    "md-export",
    "proposal",
    "demo-deploy",
    "client-onboarding",
    "ssh",
    "core",
]


def run_tests(
    level: int = 1,
    plugin: str = None,
    verbose: bool = True,
    coverage: bool = False,
    fail_fast: bool = False,
    extra_args: list = None,
) -> int:
    """Run tests with specified options."""

    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]

    # Add verbosity
    if verbose:
        cmd.append("-v")

    # Add test level
    cmd.extend(["--test-level", str(level)])

    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term-missing"])

    # Add fail-fast
    if fail_fast:
        cmd.append("-x")

    # Select test paths
    test_paths = []
    if plugin:
        if plugin not in PLUGINS:
            print(f"Unknown plugin: {plugin}")
            print(f"Available plugins: {', '.join(PLUGINS)}")
            return 1

        test_path = PROJECT_ROOT / plugin / "tests"
        if not test_path.exists():
            print(f"No tests directory found for plugin: {plugin}")
            print(f"Expected path: {test_path}")
            return 1

        test_paths.append(str(test_path))
    else:
        # Run all tests - central tests first
        central_tests = PROJECT_ROOT / "tests"
        if central_tests.exists():
            # Only add if there are test files
            if list(central_tests.glob("test_*.py")):
                test_paths.append(str(central_tests))

        # Then plugin tests
        for p in PLUGINS:
            test_path = PROJECT_ROOT / p / "tests"
            if test_path.exists():
                test_paths.append(str(test_path))

    if not test_paths:
        print("No test directories found!")
        return 1

    cmd.extend(test_paths)

    # Add any extra arguments
    if extra_args:
        cmd.extend(extra_args)

    # Print command
    print(f"Running: {' '.join(cmd)}")
    print()

    # Run pytest
    os.chdir(PROJECT_ROOT)
    result = subprocess.run(cmd)

    return result.returncode


def list_plugins():
    """List all available plugins and their test status."""
    print("Available plugins:")
    print("-" * 50)
    for plugin in PLUGINS:
        test_path = PROJECT_ROOT / plugin / "tests"
        if test_path.exists():
            test_files = list(test_path.glob("test_*.py"))
            status = f"{len(test_files)} test file(s)"
        else:
            status = "no tests"
        print(f"  {plugin:<20} {status}")


def main():
    parser = argparse.ArgumentParser(
        description="Run cc-plugins tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--level", "-l",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help="Maximum test level: 1=dry, 2=read-only, 3=write (default: 1)"
    )

    parser.add_argument(
        "--plugin", "-p",
        choices=PLUGINS,
        help="Run tests for a specific plugin only"
    )

    parser.add_argument(
        "--list-plugins",
        action="store_true",
        help="List all available plugins"
    )

    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generate coverage report"
    )

    parser.add_argument(
        "--fail-fast", "-x",
        action="store_true",
        help="Stop on first failure"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce output verbosity"
    )

    parser.add_argument(
        "extra_args",
        nargs="*",
        help="Additional arguments to pass to pytest"
    )

    args = parser.parse_args()

    if args.list_plugins:
        list_plugins()
        return 0

    return run_tests(
        level=args.level,
        plugin=args.plugin,
        verbose=not args.quiet,
        coverage=args.coverage,
        fail_fast=args.fail_fast,
        extra_args=args.extra_args,
    )


if __name__ == "__main__":
    sys.exit(main())
