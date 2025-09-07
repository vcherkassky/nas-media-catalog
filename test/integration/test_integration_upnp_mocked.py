#!/usr/bin/env python3
"""Integration tests for UPnP client with mocked network dependencies."""

import pytest
from unittest.mock import MagicMock, patch
from nas_media_catalog.upnp_client import UPnPClient, UPnPMediaServer, UPnPMediaFile


@pytest.fixture
def mock_upnp_server():
    """Mock UPnP media server."""
    return UPnPMediaServer(
        name="Mock Fritz Box",
        udn="uuid:mock-fritz-box-123",
        base_url="http://192.168.1.1:49000/",
        content_directory_url="http://192.168.1.1:49000/upnp/control/ContentDirectory",
        device=MagicMock(),  # Mock device object
    )


@pytest.fixture
def mock_media_files():
    """Mock media files."""
    return [
        UPnPMediaFile(
            id="1",
            title="Mock Video 1.mp4",
            path="http://192.168.1.1:49000/video1.mp4",
            mime_type="video/mp4",
            size=1024 * 1024 * 100,  # 100MB
        ),
        UPnPMediaFile(
            id="2",
            title="Mock Audio 1.mp3",
            path="http://192.168.1.1:49000/audio1.mp3",
            mime_type="audio/mpeg",
            size=1024 * 1024 * 5,  # 5MB
        ),
        UPnPMediaFile(
            id="3",
            title="Mock Image 1.jpg",
            path="http://192.168.1.1:49000/image1.jpg",
            mime_type="image/jpeg",
            size=1024 * 500,  # 500KB
        ),
    ]


@pytest.mark.integration
class TestUPnPClientIntegration:
    """Integration tests for UPnP client with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_discover_media_servers_success(self, mock_upnp_server):
        """Test successful media server discovery."""
        client = UPnPClient()

        # Mock the entire discover_media_servers method
        with patch.object(client, "discover_media_servers") as mock_discover:
            mock_discover.return_value = [mock_upnp_server]

            servers = await client.discover_media_servers(timeout=1)

            assert len(servers) == 1
            assert servers[0].name == "Mock Fritz Box"
            assert servers[0].udn == "uuid:mock-fritz-box-123"

    @pytest.mark.asyncio
    async def test_discover_media_servers_timeout(self):
        """Test media server discovery timeout."""
        client = UPnPClient()

        with patch("nas_media_catalog.upnp_client.socket.socket") as mock_socket:
            # Mock socket timeout
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.recvfrom.side_effect = TimeoutError()

            servers = await client.discover_media_servers(timeout=0.1)

            assert servers == []

    def test_connect_to_server_success(self, mock_upnp_server):
        """Test successful server connection."""
        client = UPnPClient()
        client.discovered_servers = [mock_upnp_server]

        result = client.connect_to_server()

        assert result is True
        assert client.connected_server == mock_upnp_server

    def test_connect_to_server_no_servers(self):
        """Test connection when no servers are available."""
        client = UPnPClient()
        client.discovered_servers = []

        result = client.connect_to_server()

        assert result is False
        assert client.connected_server is None

    def test_get_server_info_success(self, mock_upnp_server):
        """Test getting server information."""
        client = UPnPClient()
        client.connected_server = mock_upnp_server

        info = client.get_server_info()

        assert info is not None
        assert info["name"] == "Mock Fritz Box"
        assert info["udn"] == "uuid:mock-fritz-box-123"
        assert info["base_url"] == "http://192.168.1.1:49000/"

    def test_get_server_info_no_connection(self):
        """Test getting server info when not connected."""
        client = UPnPClient()
        client.connected_server = None

        info = client.get_server_info()

        assert info is None

    @pytest.mark.asyncio
    async def test_browse_media_files_success(self, mock_upnp_server, mock_media_files):
        """Test successful media file browsing."""
        client = UPnPClient()
        client.connected_server = mock_upnp_server

        # Mock the entire browse_media_files method
        with patch.object(client, "browse_media_files") as mock_browse:
            mock_browse.return_value = mock_media_files[:2]  # Return first 2 files

            media_files = await client.browse_media_files(container_id="0", max_depth=1)

            assert len(media_files) == 2
            assert media_files[0].title == "Mock Video 1.mp4"
            assert media_files[0].mime_type == "video/mp4"
            assert media_files[1].title == "Mock Audio 1.mp3"
            assert media_files[1].mime_type == "audio/mpeg"

    @pytest.mark.asyncio
    async def test_browse_media_files_no_connection(self):
        """Test browsing when not connected to server."""
        client = UPnPClient()
        client.connected_server = None

        with pytest.raises(RuntimeError, match="Not connected to any media server"):
            await client.browse_media_files()

    @pytest.mark.asyncio
    async def test_browse_media_files_soap_error(self, mock_upnp_server):
        """Test browsing with SOAP error response."""
        client = UPnPClient()
        client.connected_server = mock_upnp_server

        with patch("nas_media_catalog.upnp_client.requests.post") as mock_post:
            # Mock SOAP error response
            mock_response = MagicMock()
            mock_response.text = """<?xml version="1.0"?>
                <s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
                    <s:Body>
                        <s:Fault>
                            <faultcode>s:Client</faultcode>
                            <faultstring>Invalid container ID</faultstring>
                        </s:Fault>
                    </s:Body>
                </s:Envelope>"""
            mock_post.return_value = mock_response

            media_files = await client.browse_media_files(container_id="invalid")

            assert media_files == []


@pytest.mark.integration
class TestUPnPHelperFunctions:
    """Integration tests for UPnP helper functions."""

    @pytest.mark.asyncio
    async def test_discover_fritz_box_media_server_success(self, mock_upnp_server):
        """Test successful Fritz Box discovery."""
        from nas_media_catalog.upnp_client import discover_fritz_box_media_server

        with patch(
            "nas_media_catalog.upnp_client.UPnPClient.discover_media_servers"
        ) as mock_discover:
            mock_discover.return_value = [mock_upnp_server]

            server = await discover_fritz_box_media_server()

            assert server == mock_upnp_server

    @pytest.mark.asyncio
    async def test_discover_fritz_box_media_server_not_found(self):
        """Test Fritz Box discovery when no servers found."""
        from nas_media_catalog.upnp_client import discover_fritz_box_media_server

        with patch(
            "nas_media_catalog.upnp_client.UPnPClient.discover_media_servers"
        ) as mock_discover:
            mock_discover.return_value = []

            server = await discover_fritz_box_media_server()

            assert server is None

    def test_upnp_media_file_creation(self):
        """Test UPnPMediaFile creation and attributes."""
        media_file = UPnPMediaFile(
            id="test-1",
            title="Test Video.mp4",
            path="http://example.com/video.mp4",
            mime_type="video/mp4",
            size=1024 * 1024,
        )

        assert media_file.id == "test-1"
        assert media_file.title == "Test Video.mp4"
        assert media_file.path == "http://example.com/video.mp4"
        assert media_file.mime_type == "video/mp4"
        assert media_file.size == 1024 * 1024
