"""Playlist generator for creating VLC-compatible playlists."""

import logging
from typing import List, Optional
from pathlib import Path
from datetime import datetime
import json
from .database import MediaFileDB, PlaylistDB
from .upnp_client import UPnPClient

logger = logging.getLogger(__name__)


class PlaylistGenerator:
    """Generates VLC-compatible playlists in M3U format."""

    def __init__(self, upnp_client: UPnPClient):
        self.upnp_client = upnp_client

    def generate_m3u_content(
        self, playlist: PlaylistDB, media_files: List[MediaFileDB]
    ) -> str:
        """Generate M3U playlist content."""
        lines = ["#EXTM3U"]
        lines.append(f"#PLAYLIST:{playlist.name}")

        if playlist.description:
            lines.append(f"# {playlist.description}")

        lines.append("")

        # Parse file paths from playlist
        file_paths = json.loads(playlist.file_paths)

        # Create a lookup dict for media files
        media_lookup = {file.path: file for file in media_files}

        for file_path in file_paths:
            if file_path in media_lookup:
                media_file = media_lookup[file_path]

                # Add extended info
                duration = -1  # VLC will determine duration
                title = Path(media_file.name).stem

                lines.append(f"#EXTINF:{duration},{title}")

                # For UPnP, the path is typically the direct media URL
                upnp_url = media_file.path  # UPnP URLs are stored directly in the path
                lines.append(upnp_url)
                lines.append("")

        return "\n".join(lines)

    def generate_m3u_file(
        self,
        playlist: PlaylistDB,
        media_files: List[MediaFileDB],
        output_path: Optional[str] = None,
    ) -> str:
        """Generate M3U file and return the file path."""
        content = self.generate_m3u_content(playlist, media_files)

        if not output_path:
            # Create safe filename
            safe_name = "".join(
                c for c in playlist.name if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            output_path = f"{safe_name}.m3u"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Generated M3U playlist: {output_path}")
        return output_path

    def create_auto_playlists(self, media_files: List[MediaFileDB]) -> List[dict]:
        """Create automatic playlists based on file types and directories."""
        auto_playlists = []

        # Group by file type
        by_type = {}
        for file in media_files:
            if file.file_type not in by_type:
                by_type[file.file_type] = []
            by_type[file.file_type].append(file.path)

        for file_type, paths in by_type.items():
            if len(paths) > 1:  # Only create playlist if more than 1 file
                auto_playlists.append(
                    {
                        "name": f"All {file_type.upper()} Files",
                        "description": f"Auto-generated playlist for all {file_type} files",
                        "file_paths": paths,
                    }
                )

        # Group by directory (first level under share)
        by_directory = {}
        for file in media_files:
            # Extract directory from path
            path_parts = file.path.split("\\")
            if len(path_parts) > 3:  # \\hostname\share\directory\...
                directory = path_parts[3]
                if directory not in by_directory:
                    by_directory[directory] = []
                by_directory[directory].append(file.path)

        for directory, paths in by_directory.items():
            if len(paths) > 1:  # Only create playlist if more than 1 file
                auto_playlists.append(
                    {
                        "name": f"Directory: {directory}",
                        "description": f"Auto-generated playlist for directory '{directory}'",
                        "file_paths": paths,
                    }
                )

        return auto_playlists

    def create_smart_playlists(self, media_files: List[MediaFileDB]) -> List[dict]:
        """Create smart playlists based on patterns and metadata."""
        smart_playlists = []

        # Recent files (last 30 days)
        recent_threshold = datetime.now().timestamp() - (30 * 24 * 60 * 60)
        recent_files = [
            f.path for f in media_files if f.modified_time > recent_threshold
        ]

        if recent_files:
            smart_playlists.append(
                {
                    "name": "Recently Added",
                    "description": "Files added in the last 30 days",
                    "file_paths": recent_files,
                }
            )

        # Large files (>100MB)
        large_files = [f.path for f in media_files if f.size > 100 * 1024 * 1024]
        if large_files:
            smart_playlists.append(
                {
                    "name": "Large Files",
                    "description": "Files larger than 100MB",
                    "file_paths": large_files,
                }
            )

        # Audio files only
        audio_extensions = {"mp3", "flac", "wav", "aac", "ogg", "wma", "m4a"}
        audio_files = [f.path for f in media_files if f.file_type in audio_extensions]
        if audio_files:
            smart_playlists.append(
                {
                    "name": "Audio Collection",
                    "description": "All audio files",
                    "file_paths": audio_files,
                }
            )

        # Video files only
        video_extensions = {"mp4", "avi", "mkv", "mov", "wmv", "flv", "webm", "m4v"}
        video_files = [f.path for f in media_files if f.file_type in video_extensions]
        if video_files:
            smart_playlists.append(
                {
                    "name": "Video Collection",
                    "description": "All video files",
                    "file_paths": video_files,
                }
            )

        return smart_playlists


def create_vlc_compatible_url(
    file_path: str, username: str, password: str, hostname: str
) -> str:
    """Create a VLC-compatible SMB URL."""
    # Convert Windows path to SMB URL format
    smb_path = file_path.replace("\\", "/")

    # Handle authentication in URL
    if password:
        auth = f"{username}:{password}@"
    else:
        auth = f"{username}@" if username else ""

    return f"smb://{auth}{hostname}{smb_path}"
