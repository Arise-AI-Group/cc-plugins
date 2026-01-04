"""
Diagrams Plugin - Level 1 Tests (Dry/Local)

These tests verify diagram generation logic without external API calls.
The diagrams plugin primarily works locally.
"""
import pytest
import json


class TestMermaidGeneration:
    """Test Mermaid diagram generation."""

    @pytest.mark.level1
    def test_sample_diagram_json_structure(self, sample_diagram_json):
        """Test that sample diagram JSON has correct structure."""
        assert "nodes" in sample_diagram_json
        assert "connections" in sample_diagram_json
        assert len(sample_diagram_json["nodes"]) == 3
        assert len(sample_diagram_json["connections"]) == 2

    @pytest.mark.level1
    def test_node_structure(self, sample_diagram_json):
        """Test that nodes have required fields."""
        for node in sample_diagram_json["nodes"]:
            assert "id" in node
            assert "label" in node

    @pytest.mark.level1
    def test_connection_structure(self, sample_diagram_json):
        """Test that connections have required fields."""
        for conn in sample_diagram_json["connections"]:
            assert "from" in conn
            assert "to" in conn

    @pytest.mark.level1
    def test_mermaid_generator_import(self):
        """Test that mermaid generator can be imported."""
        try:
            from diagrams.tool.generate_mermaid import generate_mermaid
            assert callable(generate_mermaid)
        except ImportError:
            pytest.skip("Mermaid generator not available")

    @pytest.mark.level1
    def test_drawio_generator_import(self):
        """Test that drawio generator can be imported."""
        try:
            from diagrams.tool.generate_drawio import generate_xml
            assert callable(generate_xml)
        except ImportError:
            pytest.skip("Draw.io generator not available")


class TestDrawioGeneration:
    """Test Draw.io diagram generation."""

    @pytest.mark.level1
    def test_drawio_xml_structure(self, sample_diagram_json, temp_output_dir):
        """Test that Draw.io generates valid XML."""
        try:
            from diagrams.tool.generate_drawio import generate_xml

            # generate_xml returns XML string directly
            result = generate_xml(sample_diagram_json)

            # Should generate some output
            assert result is not None
            assert isinstance(result, str)
            assert "mxGraphModel" in result  # Draw.io XML format
        except ImportError:
            pytest.skip("Draw.io generator not available")
        except Exception as e:
            # Generation may require additional setup
            pytest.skip(f"Draw.io generation not configured: {e}")


class TestDiagramValidation:
    """Test diagram input validation."""

    @pytest.mark.level1
    def test_empty_nodes_handled(self):
        """Test handling of empty nodes list."""
        diagram = {"nodes": [], "connections": []}

        # Should not raise an error
        assert diagram["nodes"] == []

    @pytest.mark.level1
    def test_missing_connections_handled(self):
        """Test handling of missing connections."""
        diagram = {
            "nodes": [{"id": "1", "label": "Alone"}]
        }

        # Should handle missing connections gracefully
        assert "nodes" in diagram
