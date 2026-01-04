"""
Infrastructure plugin test fixtures (Cloudflare + Dokploy).
"""
import os
import sys
import pytest
from pathlib import Path

# .testing/plugins/infrastructure/conftest.py -> project root is 4 levels up
TESTING_ROOT = Path(__file__).parent.parent.parent  # .testing/
PROJECT_ROOT = TESTING_ROOT.parent  # cc-plugins/

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(TESTING_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTING_ROOT))

from helpers.mock_factory import MockClientFactory
from helpers.cleanup import cleanup_cloudflare_resources, cleanup_dokploy_resources


@pytest.fixture
def mock_cloudflare_client():
    """Fully mocked Cloudflare client for Level 1 tests."""
    factory = MockClientFactory()
    return factory.create_cloudflare_client()


@pytest.fixture
def mock_dokploy_client():
    """Fully mocked Dokploy client for Level 1 tests."""
    factory = MockClientFactory()
    return factory.create_dokploy_client()


@pytest.fixture(scope="module")
def cloudflare_client(has_cloudflare_credentials):
    """Real Cloudflare client for Level 2 and 3 tests."""
    if not has_cloudflare_credentials:
        pytest.skip("Cloudflare credentials not configured")

    try:
        from infrastructure.tool.cloudflare_api import CloudflareClient, CloudflareError
    except ImportError:
        pytest.skip("Cloudflare client not available")

    client = CloudflareClient()

    # Test connectivity - skip if location-restricted
    try:
        client.list_zones()
    except CloudflareError as e:
        if "location" in str(e).lower():
            pytest.skip(f"Cloudflare API access restricted: {e}")
        raise

    return client


@pytest.fixture(scope="module")
def dokploy_client(has_dokploy_credentials):
    """Real Dokploy client for Level 2 and 3 tests."""
    if not has_dokploy_credentials:
        pytest.skip("Dokploy credentials not configured")

    try:
        from infrastructure.tool.dokploy_api import DokployClient
    except ImportError:
        pytest.skip("Dokploy client not available")

    return DokployClient()


@pytest.fixture
def cloudflare_cleanup(cloudflare_client, cleanup_registry):
    """Cleanup fixture for Cloudflare resources."""
    yield cleanup_registry
    cleanup_cloudflare_resources(cloudflare_client, cleanup_registry)


@pytest.fixture
def dokploy_cleanup(dokploy_client, cleanup_registry):
    """Cleanup fixture for Dokploy resources."""
    yield cleanup_registry
    cleanup_dokploy_resources(dokploy_client, cleanup_registry)


@pytest.fixture
def find_existing_zone(cloudflare_client):
    """Helper to find an existing DNS zone."""
    def _find():
        zones = cloudflare_client.list_zones()
        return zones[0] if zones else None
    return _find
