#!/usr/bin/env python3
"""Test UPnP discovery and connection to Fritz Box media server."""

import asyncio
import logging
import pytest

from nas_media_catalog.upnp_client import UPnPClient, discover_fritz_box_media_server
from nas_media_catalog.config import settings

logger = logging.getLogger(__name__)


@pytest.mark.e2e
async def test_upnp_discovery():
    """Test UPnP media server discovery."""
    logger.info("=== Testing UPnP Media Server Discovery ===")

    try:
        client = UPnPClient()
        servers = await client.discover_media_servers(
            timeout=settings.upnp_discovery_timeout
        )

        if servers:
            logger.info(f"✅ Found {len(servers)} UPnP media servers:")
            for i, server in enumerate(servers, 1):
                logger.info(f"  [{i}] {server.name}")
                logger.info(f"      UDN: {server.udn}")
                logger.info(f"      Base URL: {server.base_url}")
            return servers
        else:
            logger.error("❌ No UPnP media servers found")
            return []

    except Exception as e:
        logger.error(f"❌ Error during UPnP discovery: {e}")
        return []


@pytest.mark.e2e
async def test_fritz_box_discovery():
    """Test Fritz Box specific discovery."""
    logger.info("\n=== Testing Fritz Box Media Server Discovery ===")

    try:
        server = await discover_fritz_box_media_server()

        if server:
            logger.info(f"✅ Found Fritz Box media server: {server.name}")
            logger.info(f"    UDN: {server.udn}")
            logger.info(f"    Base URL: {server.base_url}")
            return server
        else:
            logger.error("❌ No Fritz Box media server found")
            return None

    except Exception as e:
        logger.error(f"❌ Error discovering Fritz Box: {e}")
        return None


@pytest.mark.e2e
async def test_media_browsing():
    """Test browsing media content from the server."""
    logger.info("\n=== Testing Media Content Browsing ===")

    # First discover and connect to a server
    server = await discover_fritz_box_media_server()
    if not server:
        logger.warning(
            "⚠️ No Fritz Box media server found - skipping media browsing test"
        )
        return

    try:
        client = UPnPClient()
        client.connected_server = server

        # Browse root container
        media_files = await client.browse_media_files(container_id="0", max_depth=2)

        if media_files:
            logger.info(f"✅ Found {len(media_files)} media files:")

            # Group by file type
            by_type = {}
            for file in media_files:
                file_type = (
                    file.mime_type.split("/")[0] if file.mime_type else "unknown"
                )
                if file_type not in by_type:
                    by_type[file_type] = []
                by_type[file_type].append(file)

            for file_type, files in by_type.items():
                logger.info(f"  {file_type.upper()}: {len(files)} files")

            # Show first few files as examples
            logger.info("\n  Sample files:")
            for i, file in enumerate(media_files[:5], 1):
                size_mb = (
                    file.size / (1024 * 1024) if file.size and file.size > 0 else 0
                )
                logger.info(f"    [{i}] {file.title}")
                logger.info(
                    f"        MIME Type: {file.mime_type}, Size: {size_mb:.1f} MB"
                )
                logger.info(f"        Path: {file.path}")
                if hasattr(file, "url") and file.url:
                    logger.info(f"        URL: {file.url[:80]}...")

            if len(media_files) > 5:
                logger.info(f"    ... and {len(media_files) - 5} more files")

            return media_files
        else:
            logger.warning("⚠️ No media files found")
            return []

    except Exception as e:
        logger.error(f"❌ Error browsing media content: {e}")
        return []


@pytest.mark.e2e
async def test_server_info():
    """Test getting server information."""
    logger.info("\n=== Testing Server Information ===")

    # First discover and connect to a server
    server = await discover_fritz_box_media_server()
    if not server:
        logger.warning("⚠️ No Fritz Box media server found - skipping server info test")
        return

    try:
        client = UPnPClient()
        client.connected_server = server

        info = client.get_server_info()
        if info:
            logger.info("✅ Server Information:")
            for key, value in info.items():
                logger.info(f"    {key}: {value}")
        else:
            logger.warning("⚠️ Could not get server information")

    except Exception as e:
        logger.error(f"❌ Error getting server info: {e}")


async def main():
    """Run all UPnP tests."""
    logger.info("🚀 Starting UPnP Media Server Discovery Test")
    logger.info(f"Discovery timeout: {settings.upnp_discovery_timeout} seconds")

    # Test 1: General UPnP Discovery
    servers = await test_upnp_discovery()

    # Test 2: Fritz Box Specific Discovery
    fritz_server = await test_fritz_box_discovery()

    if fritz_server:
        # Test 3: Server Information
        await test_server_info(fritz_server)

        # Test 4: Media Browsing
        media_files = await test_media_browsing(fritz_server)

        logger.info("\n🎉 UPnP Discovery Test Complete!")
        logger.info("✅ Fritz Box media server is accessible via UPnP")
        logger.info(f"✅ Found {len(media_files)} media files")
        logger.info("\nTo start the server:")
        logger.info("1. Run: uv run python run_server.py")
        logger.info("2. Visit: http://localhost:8000")

        return True

    elif servers:
        logger.info("\n📋 UPnP Discovery Results:")
        logger.info("✅ Found UPnP media servers, but no Fritz Box detected")
        logger.info("💡 You can still use the first available server")
        logger.info(
            "The server will auto-discover and connect to available UPnP servers"
        )

        return True

    else:
        logger.info("\n❌ UPnP Discovery Failed")
        logger.info("💡 Troubleshooting tips:")
        logger.info("- Ensure UPnP/DLNA is enabled on your Fritz Box")
        logger.info("- Check that media server is running")
        logger.info("- Verify you're on the same network")
        logger.info("- Try increasing UPnP_DISCOVERY_TIMEOUT in .env")

        return False


if __name__ == "__main__":
    import sys

    success = asyncio.run(main())
    sys.exit(0 if success else 1)
