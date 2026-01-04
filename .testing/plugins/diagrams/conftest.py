"""
Diagrams plugin test fixtures.

Note: Diagrams plugin primarily generates local files, so most tests
are Level 1 (no external API calls required).
"""
import os
import sys
import pytest
from pathlib import Path
import tempfile
import json

# .testing/plugins/diagrams/conftest.py -> project root is 4 levels up
TESTING_ROOT = Path(__file__).parent.parent.parent  # .testing/
PROJECT_ROOT = TESTING_ROOT.parent  # cc-plugins/

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TESTING_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTING_ROOT))


@pytest.fixture
def sample_diagram_json():
    """Sample diagram JSON for testing generation."""
    return {
        "nodes": [
            {"id": "1", "label": "Start", "type": "rectangle"},
            {"id": "2", "label": "Process", "type": "rectangle"},
            {"id": "3", "label": "End", "type": "rectangle"}
        ],
        "connections": [
            {"from": "1", "to": "2"},
            {"from": "2", "to": "3"}
        ]
    }


@pytest.fixture
def temp_output_dir():
    """Temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_mermaid_output():
    """Expected Mermaid output structure."""
    return """flowchart TD
    1[Start] --> 2[Process]
    2[Process] --> 3[End]
"""
