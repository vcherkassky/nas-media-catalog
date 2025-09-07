"""NAS Media Catalog - A FastAPI server for cataloging NAS media files and creating VLC playlists."""

__version__ = "0.1.0"
__author__ = "Viktor"
__description__ = (
    "NAS Media Catalog Server - Cache media files and create VLC playlists"
)

from .config import settings
from .upnp_client import UPnPClient, UPnPMediaFile, UPnPMediaServer
from .database import (
    DatabaseManager,
    MediaFileResponse,
    PlaylistCreate,
    PlaylistResponse,
)
from .playlist_generator import PlaylistGenerator

__all__ = [
    "settings",
    "UPnPClient",
    "UPnPMediaFile",
    "UPnPMediaServer",
    "DatabaseManager",
    "MediaFileResponse",
    "PlaylistCreate",
    "PlaylistResponse",
    "PlaylistGenerator",
]
