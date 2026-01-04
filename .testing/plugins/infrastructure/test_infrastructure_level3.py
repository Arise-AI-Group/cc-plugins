"""
Infrastructure Plugin - Level 3 Tests (Write Operations)
"""
import pytest
import time


@pytest.mark.level3
@pytest.mark.requires_credentials
class TestCloudflareWriteOperations:
    """Write tests against real Cloudflare API."""

    def test_create_and_delete_dns_record(
        self,
        cloudflare_client,
        find_existing_zone,
        test_prefix,
        cloudflare_cleanup
    ):
        """Test creating and deleting a DNS record."""
        zone = find_existing_zone()
        if not zone:
            pytest.skip("No zones available for testing")

        timestamp = int(time.time())
        record_name = f"{test_prefix}test-{timestamp}"

        # Create TXT record (safe for testing)
        record = cloudflare_client.create_dns_record(
            zone["id"],
            {
                "type": "TXT",
                "name": record_name,
                "content": f"test-record-{timestamp}",
                "ttl": 1  # Auto TTL
            }
        )

        cloudflare_cleanup.register("cloudflare_dns_records", {
            "zone_id": zone["id"],
            "record_id": record["id"]
        })

        assert "id" in record
        assert record["type"] == "TXT"

        # Delete record
        result = cloudflare_client.delete_dns_record(zone["id"], record["id"])
        assert result is True
