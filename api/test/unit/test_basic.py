"""Basic unit tests for NAS Media Catalog."""

import pytest

from nas_media_catalog.config import settings
from nas_media_catalog.upnp_client import UPnPMediaFile, UPnPMediaServer


@pytest.mark.unit
def test_settings_loading():
    """Test that settings can be loaded."""
    assert settings.upnp_discovery_timeout > 0
    assert settings.server_host is not None
    assert settings.server_port > 0


@pytest.mark.unit
def test_upnp_media_file_creation():
    """Test UPnPMediaFile dataclass creation."""
    media_file = UPnPMediaFile(
        id="test_id",
        title="Test Song",
        mime_type="audio/mp3",
        size=1024,
        duration="03:45",
        url="http://192.168.1.1:49200/audio/test.mp3",
        path="http://192.168.1.1:49200/audio/test.mp3",
    )

    assert media_file.id == "test_id"
    assert media_file.title == "Test Song"
    assert media_file.mime_type == "audio/mp3"
    assert media_file.size == 1024
    assert media_file.duration == "03:45"
    assert media_file.url == "http://192.168.1.1:49200/audio/test.mp3"


@pytest.mark.unit
def test_upnp_media_server_creation():
    """Test UPnPMediaServer dataclass creation."""
    server = UPnPMediaServer(
        name="Test Media Server",
        udn="uuid:test-server-123",
        base_url="http://192.168.1.1:49200/",
        content_directory_url="http://192.168.1.1:49200/ctl/ContentDir",
        device={"test": "data"},
    )

    assert server.name == "Test Media Server"
    assert server.udn == "uuid:test-server-123"
    assert server.base_url == "http://192.168.1.1:49200/"
    assert server.content_directory_url == "http://192.168.1.1:49200/ctl/ContentDir"


@pytest.mark.unit
def test_mime_type_detection():
    """Test MIME type to file type conversion."""
    from nas_media_catalog.database import DatabaseManager

    db_manager = DatabaseManager()

    # Test video types
    assert db_manager._get_file_type_from_mime("video/mp4") == "video"
    assert db_manager._get_file_type_from_mime("video/avi") == "video"
    assert db_manager._get_file_type_from_mime("video/x-msvideo") == "video"

    # Test audio types
    assert db_manager._get_file_type_from_mime("audio/mp3") == "audio"
    assert db_manager._get_file_type_from_mime("audio/mpeg") == "audio"
    assert db_manager._get_file_type_from_mime("audio/flac") == "audio"

    # Test unknown types
    assert db_manager._get_file_type_from_mime("application/pdf") == "unknown"
    assert db_manager._get_file_type_from_mime("") == "unknown"
