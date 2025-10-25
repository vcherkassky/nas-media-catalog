"""Playlist generator for creating VLC-compatible playlists."""

import logging
from typing import List, Optional
from pathlib import Path
from datetime import datetime
import json
from .database import MediaFileDB, PlaylistDB
from .upnp_client import UPnPClient
from .config import settings

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

        # Add helpful instructions for opening in VLC
        lines.append("# ")
        lines.append("# TO OPEN IN VLC:")
        lines.append("# • Right-click this file → Open With → VLC")
        lines.append("# • OR drag this file into VLC window")
        lines.append("# • OR use Terminal: open -a VLC filename.m3u")
        lines.append("# (Double-clicking opens Apple Music, not VLC!)")

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

                # Sanitize title for M3U format - replace characters that have special meaning
                sanitized_title = self._sanitize_m3u_title(title)

                lines.append(f"#EXTINF:{duration},{sanitized_title}")

                # Use SMB URL if SMB is enabled and configured, otherwise use UPnP URL
                if (
                    settings.smb_enabled
                    and settings.smb_hostname
                    and settings.smb_username
                    and hasattr(media_file, "smb_url")
                    and media_file.smb_url
                ):
                    # Use pre-generated SMB URL from database
                    url = media_file.smb_url
                    logger.debug(f"Using SMB URL for {media_file.name}: {url}")
                else:
                    # Fall back to UPnP URL
                    url = media_file.path  # UPnP URLs are stored directly in the path
                    logger.debug(f"Using UPnP URL for {media_file.name}: {url}")

                lines.append(url)
                lines.append("")

        return "\n".join(lines)

    def _sanitize_m3u_title(self, title: str) -> str:
        """
        Sanitize media file title for use in M3U #EXTINF entries.

        Replaces characters that have special meaning in M3U format:
        - ',' separates duration from title in #EXTINF
        - ':' used in various M3U directives
        - '#' starts M3U comment/directive lines
        - ' - ' could be misinterpreted as artist-title separator

        Note: Avoid using '-' as replacement since it's commonly used
        to separate artist from title in M3U format.
        """
        # Replace problematic characters with safe alternatives
        sanitized = title.replace(" - ", " • ")  # Space-dash-space becomes bullet point
        sanitized = sanitized.replace(",", ";")  # Comma becomes semicolon
        sanitized = sanitized.replace(":", ".")  # Colon becomes period
        sanitized = sanitized.replace("#", "No.")  # Hash becomes "No."

        # Remove any leading/trailing whitespace
        sanitized = sanitized.strip()

        # Ensure we don't have an empty title
        if not sanitized:
            sanitized = "Unknown Title"

        return sanitized

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

        # Optimized UPnP playlist (files most likely to work in VLC)
        optimized_upnp_files = self._get_optimized_upnp_files(media_files)
        if optimized_upnp_files:
            smart_playlists.append(
                {
                    "name": "UPnP Compatible Videos",
                    "description": "Video files optimized for reliable UPnP/DLNA playback in VLC",
                    "file_paths": [f.path for f in optimized_upnp_files],
                }
            )

        return smart_playlists

    def _get_optimized_upnp_files(
        self, media_files: List[MediaFileDB]
    ) -> List[MediaFileDB]:
        """Get files optimized for UPnP playback based on success patterns."""
        video_files = [f for f in media_files if f.file_type == "video"]

        if not video_files:
            return []

        # Calculate average path length for comparison
        avg_length = sum(len(f.path) for f in video_files) / len(video_files)

        # Score files based on factors that correlate with UPnP success
        scored_files = []

        for file in video_files:
            score = 0

            # Prefer DLNA-11-0 container (showed best compatibility)
            if "DLNA-11-0" in file.path:
                score += 3
            elif "DLNA-0-0" in file.path:
                score += 2
            elif "DLNA-8-0" in file.path:
                score += 1

            # Prefer MP4 files (best codec compatibility)
            if file.name.lower().endswith(".mp4"):
                score += 3
            elif file.name.lower().endswith(".mkv"):
                score += 2
            elif file.name.lower().endswith(".avi"):
                score += 1

            # Avoid hidden/metadata files
            if not file.name.startswith("._"):
                score += 2

            # Prefer shorter paths (less likely to have encoding issues)
            if len(file.path) < avg_length:
                score += 1

            # Moderate penalty for too many special characters
            special_char_count = sum(
                1 for char in ["'", "(", ")", "[", "]", "&", "%"] if char in file.name
            )
            if special_char_count <= 2:
                score += 1
            elif special_char_count > 5:
                score -= 1

            # Small penalty for Unicode characters (can cause encoding issues)
            if not any(ord(char) > 127 for char in file.name):
                score += 1

            # Only include files with a reasonable score
            if score >= 3:
                scored_files.append((file, score))

        # Sort by score and return top candidates (max 20 for performance)
        scored_files.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in scored_files[:20]]


def create_vlc_compatible_url(
    file_path: str, username: str, password: str, hostname: str
) -> str:
    """Create a VLC-compatible SMB URL with proper URL encoding."""
    from urllib.parse import quote

    # Convert Windows path to SMB URL format
    smb_path = file_path.replace("\\", "/")

    # URL encode the path components, but preserve the path separators
    path_parts = smb_path.split("/")
    encoded_parts = [quote(part, safe="") for part in path_parts if part]
    encoded_path = "/" + "/".join(encoded_parts) if encoded_parts else "/"

    # Handle authentication in URL (don't encode username/password)
    if password:
        auth = f"{username}:{password}@"
    else:
        auth = f"{username}@" if username else ""

    return f"smb://{auth}{hostname}{encoded_path}"
