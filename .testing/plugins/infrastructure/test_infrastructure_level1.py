"""
Infrastructure Plugin - Level 1 Tests (Dry/Mocked)
"""
import pytest


class TestCloudfareMockedOperations:
    """Test Cloudflare operations with mocked responses."""

    @pytest.mark.level1
    def test_list_zones_returns_list(self, mock_cloudflare_client):
        """Test that list_zones returns a list."""
        zones = mock_cloudflare_client.list_zones()

        assert isinstance(zones, list)

    @pytest.mark.level1
    def test_get_zone_returns_dict(self, mock_cloudflare_client):
        """Test that get_zone returns zone details."""
        zone = mock_cloudflare_client.get_zone("zone-001")

        assert isinstance(zone, dict)
        assert "id" in zone
        assert "name" in zone

    @pytest.mark.level1
    def test_list_dns_records_returns_list(self, mock_cloudflare_client):
        """Test that list_dns_records returns a list."""
        records = mock_cloudflare_client.list_dns_records("zone-001")

        assert isinstance(records, list)

    @pytest.mark.level1
    def test_create_dns_record_returns_dict(self, mock_cloudflare_client):
        """Test that create_dns_record returns record details."""
        record = mock_cloudflare_client.create_dns_record("zone-001", {})

        assert isinstance(record, dict)
        assert "id" in record

    @pytest.mark.level1
    def test_delete_dns_record_returns_bool(self, mock_cloudflare_client):
        """Test that delete_dns_record returns success."""
        result = mock_cloudflare_client.delete_dns_record("zone-001", "rec-001")

        assert result is True

    @pytest.mark.level1
    def test_list_tunnels_returns_list(self, mock_cloudflare_client):
        """Test that list_tunnels returns a list."""
        tunnels = mock_cloudflare_client.list_tunnels()

        assert isinstance(tunnels, list)


class TestDokployMockedOperations:
    """Test Dokploy operations with mocked responses."""

    @pytest.mark.level1
    def test_list_projects_returns_list(self, mock_dokploy_client):
        """Test that list_projects returns a list."""
        projects = mock_dokploy_client.list_projects()

        assert isinstance(projects, list)

    @pytest.mark.level1
    def test_create_compose_returns_dict(self, mock_dokploy_client):
        """Test that create_compose returns compose details."""
        compose = mock_dokploy_client.create_compose({})

        assert isinstance(compose, dict)
        assert "id" in compose

    @pytest.mark.level1
    def test_delete_compose_returns_bool(self, mock_dokploy_client):
        """Test that delete_compose returns success."""
        result = mock_dokploy_client.delete_compose("compose-001")

        assert result is True
