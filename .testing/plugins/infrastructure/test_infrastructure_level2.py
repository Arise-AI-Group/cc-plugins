"""
Infrastructure Plugin - Level 2 Tests (Read-Only)
"""
import pytest


@pytest.mark.level2
@pytest.mark.requires_credentials
class TestCloudflareReadOperations:
    """Read-only tests against real Cloudflare API."""

    def test_list_zones(self, cloudflare_client):
        """Test listing DNS zones."""
        zones = cloudflare_client.list_zones()

        assert isinstance(zones, list)
        # Should have at least one zone configured
        if zones:
            assert "id" in zones[0]
            assert "name" in zones[0]

    def test_get_zone(self, cloudflare_client, find_existing_zone):
        """Test getting a specific zone."""
        zone = find_existing_zone()
        if not zone:
            pytest.skip("No zones available for testing")

        result = cloudflare_client.get_zone(zone["id"])

        assert result["id"] == zone["id"]

    def test_list_dns_records(self, cloudflare_client, find_existing_zone):
        """Test listing DNS records."""
        zone = find_existing_zone()
        if not zone:
            pytest.skip("No zones available for testing")

        records = cloudflare_client.list_dns_records(zone["id"])

        assert isinstance(records, list)

    def test_list_tunnels(self, cloudflare_client):
        """Test listing Cloudflare tunnels."""
        tunnels = cloudflare_client.list_tunnels()

        assert isinstance(tunnels, list)


@pytest.mark.level2
@pytest.mark.requires_credentials
class TestDokployReadOperations:
    """Read-only tests against real Dokploy API."""

    def test_list_projects(self, dokploy_client):
        """Test listing projects."""
        projects = dokploy_client.list_projects()

        assert isinstance(projects, list)
