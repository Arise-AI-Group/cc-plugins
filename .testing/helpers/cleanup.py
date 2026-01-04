"""
Cleanup utilities for test resources.

Each function handles cleanup for a specific service, safely removing
any test resources created during test runs.
"""
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.conftest import CleanupRegistry

logger = logging.getLogger(__name__)


def cleanup_slack_resources(client, registry: "CleanupRegistry") -> dict:
    """
    Clean up all Slack test resources.

    Args:
        client: SlackClient instance
        registry: CleanupRegistry with resources to clean

    Returns:
        dict with cleanup results
    """
    results = {"success": [], "failed": []}

    # Archive channels (can't delete, but archive is sufficient)
    for channel_info in registry.get_resources("slack_channels"):
        try:
            client.archive_channel(channel_info["id"])
            results["success"].append(f"channel:{channel_info['id']}")
            logger.info(f"Archived Slack channel: {channel_info['id']}")
        except Exception as e:
            results["failed"].append(f"channel:{channel_info['id']} - {e}")
            logger.warning(f"Failed to archive channel {channel_info['id']}: {e}")

    # Delete messages
    for msg_info in registry.get_resources("slack_messages"):
        try:
            client.delete_message(
                msg_info["channel"],
                msg_info["ts"],
                use_user_token=msg_info.get("use_user_token", False)
            )
            results["success"].append(f"message:{msg_info['ts']}")
            logger.info(f"Deleted Slack message: {msg_info['ts']}")
        except Exception as e:
            # Messages may already be deleted
            results["failed"].append(f"message:{msg_info['ts']} - {e}")
            logger.debug(f"Failed to delete message {msg_info['ts']}: {e}")

    # Disable usergroups
    for ug_info in registry.get_resources("slack_usergroups"):
        try:
            client.disable_usergroup(ug_info["id"])
            results["success"].append(f"usergroup:{ug_info['id']}")
            logger.info(f"Disabled Slack usergroup: {ug_info['id']}")
        except Exception as e:
            results["failed"].append(f"usergroup:{ug_info['id']} - {e}")
            logger.warning(f"Failed to disable usergroup {ug_info['id']}: {e}")

    return results


def cleanup_notion_resources(client, registry: "CleanupRegistry") -> dict:
    """
    Clean up all Notion test resources.

    Args:
        client: NotionClient instance
        registry: CleanupRegistry with resources to clean

    Returns:
        dict with cleanup results
    """
    results = {"success": [], "failed": []}

    # Archive pages
    for page_info in registry.get_resources("notion_pages"):
        try:
            client.archive_page(page_info["id"])
            results["success"].append(f"page:{page_info['id']}")
            logger.info(f"Archived Notion page: {page_info['id']}")
        except Exception as e:
            results["failed"].append(f"page:{page_info['id']} - {e}")
            logger.warning(f"Failed to archive page {page_info['id']}: {e}")

    # Archive databases (can't delete via API, only archive)
    for db_info in registry.get_resources("notion_databases"):
        try:
            client.update_database(db_info["id"], archived=True)
            results["success"].append(f"database:{db_info['id']}")
            logger.info(f"Archived Notion database: {db_info['id']}")
        except Exception as e:
            results["failed"].append(f"database:{db_info['id']} - {e}")
            logger.warning(f"Failed to archive database {db_info['id']}: {e}")

    return results


def cleanup_n8n_resources(client, registry: "CleanupRegistry") -> dict:
    """
    Clean up all n8n test resources.

    Args:
        client: N8nClient instance
        registry: CleanupRegistry with resources to clean

    Returns:
        dict with cleanup results
    """
    results = {"success": [], "failed": []}

    for workflow_info in registry.get_resources("n8n_workflows"):
        try:
            # Deactivate first if active
            try:
                client.deactivate_workflow(workflow_info["id"])
            except Exception:
                pass  # May not be active

            # Then delete
            client.delete_workflow(workflow_info["id"])
            results["success"].append(f"workflow:{workflow_info['id']}")
            logger.info(f"Deleted n8n workflow: {workflow_info['id']}")
        except Exception as e:
            results["failed"].append(f"workflow:{workflow_info['id']} - {e}")
            logger.warning(f"Failed to delete workflow {workflow_info['id']}: {e}")

    return results


def cleanup_cloudflare_resources(client, registry: "CleanupRegistry") -> dict:
    """
    Clean up all Cloudflare test resources.

    Args:
        client: CloudflareClient instance
        registry: CleanupRegistry with resources to clean

    Returns:
        dict with cleanup results
    """
    results = {"success": [], "failed": []}

    for record_info in registry.get_resources("cloudflare_dns_records"):
        try:
            client.delete_dns_record(
                record_info["zone_id"],
                record_info["record_id"]
            )
            results["success"].append(f"dns:{record_info['record_id']}")
            logger.info(f"Deleted Cloudflare DNS record: {record_info['record_id']}")
        except Exception as e:
            results["failed"].append(f"dns:{record_info['record_id']} - {e}")
            logger.warning(f"Failed to delete DNS record {record_info['record_id']}: {e}")

    return results


def cleanup_dokploy_resources(client, registry: "CleanupRegistry") -> dict:
    """
    Clean up all Dokploy test resources.

    Args:
        client: DokployClient instance
        registry: CleanupRegistry with resources to clean

    Returns:
        dict with cleanup results
    """
    results = {"success": [], "failed": []}

    for compose_info in registry.get_resources("dokploy_composes"):
        try:
            client.delete_compose(compose_info["id"])
            results["success"].append(f"compose:{compose_info['id']}")
            logger.info(f"Deleted Dokploy compose: {compose_info['id']}")
        except Exception as e:
            results["failed"].append(f"compose:{compose_info['id']} - {e}")
            logger.warning(f"Failed to delete compose {compose_info['id']}: {e}")

    return results


def cleanup_ssh_files(client, registry: "CleanupRegistry") -> dict:
    """
    Clean up all SSH test files on remote servers.

    Args:
        client: SSHClient instance
        registry: CleanupRegistry with resources to clean

    Returns:
        dict with cleanup results
    """
    results = {"success": [], "failed": []}

    for file_info in registry.get_resources("ssh_files"):
        try:
            client.exec(file_info["target"], f"rm -rf {file_info['path']}")
            results["success"].append(f"file:{file_info['path']}")
            logger.info(f"Deleted remote file: {file_info['path']}")
        except Exception as e:
            results["failed"].append(f"file:{file_info['path']} - {e}")
            logger.warning(f"Failed to delete file {file_info['path']}: {e}")

    return results
