#!/usr/bin/env python3
"""Test runner script for NAS Media Catalog.

This script provides convenient commands to run different types of tests:
- Unit tests: Fast, no external dependencies
- Integration tests: Require Fritz Box/UPnP server on network
- All tests: Complete test suite
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd: list[str]) -> int:
    """Run a command and return the exit code."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    """Main test runner."""
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py [unit|integration|e2e|all]")
        print()
        print("Test types:")
        print("  unit        - Fast unit tests (no external dependencies)")
        print("  integration - Integration tests (mocked dependencies)")
        print("  e2e         - End-to-end tests (requires Fritz Box/UPnP server)")
        print("  all         - All tests")
        print()
        print("Examples:")
        print("  python run_tests.py unit")
        print("  python run_tests.py integration")
        print("  uv run python run_tests.py unit")
        sys.exit(1)

    test_type = sys.argv[1].lower()

    if test_type == "unit":
        return run_command(["uv", "run", "pytest", "test/unit/"])
    elif test_type == "integration":
        return run_command(["uv", "run", "pytest", "test/integration/"])
    elif test_type == "e2e":
        return run_command(["uv", "run", "pytest", "test/e2e/"])
    elif test_type == "all":
        return run_command(["uv", "run", "pytest"])
    else:
        print(f"Unknown test type: {test_type}")
        print("Valid types: unit, integration, e2e, all")
        return 1


if __name__ == "__main__":
    sys.exit(main())
