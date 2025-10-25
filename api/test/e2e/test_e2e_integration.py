#!/usr/bin/env python3
"""
End-to-end integration tests for NAS Media Catalog with UPnP.

These tests require:
- Fritz Box or UPnP media server on the network
- Network connectivity
- Actual media files on the server

Run with: pytest test/e2e/ -m e2e
"""

import asyncio
import logging
import pytest
from sqlalchemy import text

from nas_media_catalog.config import settings
from nas_media_catalog.upnp_client import UPnPClient, discover_fritz_box_media_server
from nas_media_catalog.database import DatabaseManager
from nas_media_catalog.playlist_generator import PlaylistGenerator

logger = logging.getLogger(__name__)


# Pytest fixtures for e2e tests
@pytest.fixture(scope="session")
async def upnp_server():
    """Discover and return a UPnP media server."""
    logger.info("=== Discovering UPnP Media Server ===")
    logger.info(f"Discovery timeout: {settings.upnp_discovery_timeout}s")

    try:
        # Try Fritz Box specific discovery first
        server = await discover_fritz_box_media_server()

        if server:
            logger.info(f"✅ Found Fritz Box media server: {server.name}")
            logger.info(f"    UDN: {server.udn}")
            logger.info(f"    Base URL: {server.base_url}")
            return server

        # Fall back to general discovery
        client = UPnPClient()
        servers = await client.discover_media_servers(settings.upnp_discovery_timeout)

        if servers:
            logger.info(f"✅ Found {len(servers)} UPnP media servers:")
            for i, srv in enumerate(servers, 1):
                logger.info(f"  [{i}] {srv.name}")
            return servers[0]  # Return first server
        else:
            logger.error("❌ No UPnP media servers found")
            pytest.skip("No UPnP media servers found")

    except Exception as e:
        logger.error(f"❌ Error during UPnP discovery: {e}")
        pytest.skip(f"UPnP discovery failed: {e}")


@pytest.fixture(scope="session")
async def upnp_client(upnp_server):
    """Create and return a connected UPnP client."""
    logger.info("=== Connecting to UPnP Server ===")

    try:
        client = UPnPClient()
        client.discovered_servers = [upnp_server]

        if client.connect_to_server():
            logger.info(f"✅ Successfully connected to: {upnp_server.name}")

            # Get server info
            info = client.get_server_info()
            if info:
                logger.info("Server details:")
                for key, value in info.items():
                    logger.info(f"  {key}: {value}")

            return client
        else:
            logger.error("❌ Failed to connect to server")
            pytest.skip("Failed to connect to UPnP server")

    except Exception as e:
        logger.error(f"❌ Error connecting to server: {e}")
        pytest.skip(f"UPnP connection failed: {e}")


@pytest.fixture(scope="session")
async def media_files(upnp_client):
    """Browse and return media files from the UPnP server."""
    logger.info("=== Browsing Media Files ===")

    try:
        media_files = await upnp_client.browse_media_files(
            max_depth=settings.max_scan_depth
        )

        if media_files:
            logger.info(f"✅ Found {len(media_files)} media files")

            # Group by file type
            file_types = {}
            for file in media_files:
                file_type = file.file_type or "unknown"
                file_types[file_type] = file_types.get(file_type, 0) + 1

            logger.info("File types found:")
            for file_type, count in file_types.items():
                logger.info(f"  {file_type}: {count} files")

            # Show first few files as examples
            logger.info("Sample files:")
            for i, file in enumerate(media_files[:5]):
                logger.info(f"  [{i+1}] {file.title} ({file.file_type})")
            if len(media_files) > 5:
                logger.info(f"  ... and {len(media_files) - 5} more files")

            return media_files
        else:
            logger.warning("⚠️ No media files found")
            return []

    except Exception as e:
        logger.error(f"❌ Error browsing media files: {e}")
        return []


# Test functions using fixtures
@pytest.mark.e2e
async def test_upnp_discovery(upnp_server):
    """Test UPnP media server discovery."""
    assert upnp_server is not None
    assert upnp_server.name
    assert upnp_server.udn
    assert upnp_server.base_url
    logger.info(f"✅ Discovery test passed for server: {upnp_server.name}")


@pytest.mark.e2e
async def test_server_connection(upnp_client):
    """Test connecting to the UPnP server."""
    assert upnp_client is not None
    assert upnp_client.connected_server is not None
    logger.info(
        f"✅ Connection test passed for server: {upnp_client.connected_server.name}"
    )


@pytest.mark.e2e
async def test_media_browsing(media_files):
    """Test browsing media files from UPnP server."""
    assert isinstance(media_files, list)
    logger.info(f"✅ Media browsing test passed - found {len(media_files)} files")


@pytest.mark.e2e
async def test_database_operations(media_files):
    """Test database caching operations."""
    logger.info("=== Testing Database Operations ===")

    if not media_files:
        logger.warning("⚠️ No media files - skipping database operations test")
        return

    try:
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.init_db()
        logger.info("✅ Database initialized")

        # Cache media files
        if media_files:
            # Clear existing test data first
            async with db_manager.async_session() as session:
                await session.execute(
                    text("DELETE FROM media_files WHERE path LIKE '%test%'")
                )
                await session.commit()

            await db_manager.cache_media_files(media_files)
            logger.info(f"✅ Cached {len(media_files)} media files")

            # Verify cached files
            cached_files = await db_manager.get_media_files()
            logger.info(f"✅ Retrieved {len(cached_files)} cached files")

            assert len(cached_files) >= len(media_files), "Not all files were cached"

        logger.info("✅ Database operations completed successfully")

    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        raise


@pytest.mark.e2e
async def test_playlist_generation(upnp_client, media_files):
    """Test playlist generation."""
    logger.info("=== Testing Playlist Generation ===")

    if not media_files:
        logger.warning("⚠️ No media files available for playlist testing")
        return

    try:
        playlist_gen = PlaylistGenerator(upnp_client)

        # Create auto playlists
        auto_playlists = playlist_gen.create_auto_playlists(media_files)
        logger.info(f"✅ Generated {len(auto_playlists)} auto playlists")

        # Test M3U generation for each playlist
        for playlist_name, playlist_files in auto_playlists.items():
            if playlist_files:  # Only test non-empty playlists
                m3u_content = playlist_gen.generate_m3u_content(playlist_files)
                assert m3u_content.startswith("#EXTM3U"), "Invalid M3U format"
                assert len(m3u_content.split("\n")) > 2, "M3U content too short"
                logger.info(
                    f"✅ Generated M3U for '{playlist_name}' ({len(playlist_files)} files)"
                )

        logger.info("✅ Playlist generation completed successfully")

    except Exception as e:
        logger.error(f"❌ Playlist generation error: {e}")
        raise


if __name__ == "__main__":
    """Run all e2e tests when executed directly."""
    import sys

    async def main():
        logger.info("🚀 Starting E2E Integration Tests")

        # Run tests in sequence
        try:
            # Discovery
            server = await upnp_server()
            logger.info(f"Server discovered: {server.name}")

            # Connection
            client = await upnp_client(server)
            logger.info(f"Client connected to: {client.connected_server.name}")

            # Media browsing
            files = await media_files(client)
            logger.info(f"Found {len(files)} media files")

            # Database operations
            await test_database_operations(files)

            # Playlist generation
            await test_playlist_generation(client, files)

            logger.info("🎉 All E2E tests completed successfully!")

        except Exception as e:
            logger.error(f"❌ E2E test failed: {e}")
            sys.exit(1)

    asyncio.run(main())
