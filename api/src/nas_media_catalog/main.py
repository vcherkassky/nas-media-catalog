"""NAS Media Catalog Server - Main FastAPI application."""

import asyncio
import logging
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, UploadFile, File
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from .config import settings, setup_logging
from .database import (
    DatabaseManager,
    MediaFileResponse,
    PlaylistCreate,
    PlaylistResponse,
)
from .upnp_client import UPnPClient, discover_fritz_box_media_server
from .playlist_generator import PlaylistGenerator

# Configure logging
setup_logging()
logger = logging.getLogger(__name__)

# Global instances
db_manager = DatabaseManager(settings.database_url)
upnp_client = None
playlist_gen = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global upnp_client, playlist_gen

    # Startup
    logger.info("Starting NAS Media Catalog Server...")

    # Initialize database
    await db_manager.init_db()

    # Discover UPnP media server
    logger.info("Discovering UPnP media servers...")

    if settings.upnp_server_name:
        # Connect to specific server
        upnp_client = UPnPClient()
        await upnp_client.discover_media_servers(settings.upnp_discovery_timeout)
        if upnp_client.connect_to_server(settings.upnp_server_name):
            logger.info(
                f"Connected to specified UPnP server: {settings.upnp_server_name}"
            )
        else:
            logger.error(
                f"Could not connect to specified server: {settings.upnp_server_name}"
            )
    else:
        # Auto-discover Fritz Box or first available server
        server = await discover_fritz_box_media_server()
        if server:
            upnp_client = UPnPClient()
            upnp_client.discovered_servers = [server]
            upnp_client.connect_to_server()
            logger.info(f"Connected to UPnP media server: {server.name}")
        else:
            logger.error("No UPnP media servers found")

    if upnp_client and upnp_client.connected_server:
        playlist_gen = PlaylistGenerator(upnp_client)
        logger.info("UPnP media server connection successful!")

        # Auto-scan if enabled
        if settings.auto_scan_on_startup:
            logger.info("Starting automatic media scan...")
            asyncio.create_task(scan_media_files())
    else:
        logger.error("Failed to establish UPnP connection")

    yield

    # Shutdown
    logger.info("Server shutdown complete")


app = FastAPI(
    title="NAS Media Catalog",
    description="Cache media files from NAS and create VLC-compatible playlists",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def scan_media_files():
    """Background task to scan media files from UPnP server."""
    if not upnp_client:
        logger.error("UPnP client not available for scanning")
        return

    try:
        logger.info("Scanning media files from UPnP server...")
        media_files = await upnp_client.browse_media_files(
            max_depth=settings.max_scan_depth
        )

        if media_files:
            await db_manager.cache_media_files(media_files, "UPnP")
            logger.info(f"Completed scanning: found {len(media_files)} media files")
        else:
            logger.info(
                "No media files found (UPnP browsing is simplified in current implementation)"
            )

    except Exception as e:
        logger.error(f"Error during media scanning: {e}")


@app.get("/")
async def root():
    """Root endpoint with server information."""
    server_info = upnp_client.get_server_info() if upnp_client else None
    return {
        "message": "NAS Media Catalog Server (UPnP)",
        "version": "0.1.0",
        "upnp_connected": upnp_client is not None
        and upnp_client.connected_server is not None,
        "upnp_server": server_info.get("name") if server_info else None,
    }


@app.get("/health")
async def health_check():
    """Basic health check endpoint for Docker health checks."""
    upnp_connected = (
        upnp_client is not None and upnp_client.connected_server is not None
    )

    # For Docker health checks, we want to fail if UPnP is not connected
    # This will trigger container restart/reconnection attempts
    if not upnp_connected:
        raise HTTPException(status_code=503, detail="UPnP server not connected")

    return {
        "status": "healthy",
        "upnp_connected": upnp_connected,
        "database": "connected",
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check endpoint with more information."""
    upnp_connected = (
        upnp_client is not None and upnp_client.connected_server is not None
    )

    health_info = {
        "status": "healthy" if upnp_connected else "degraded",
        "upnp_connected": upnp_connected,
        "database": "connected",
        "timestamp": time.time(),
    }

    if upnp_client and upnp_client.connected_server:
        server_info = upnp_client.get_server_info()
        health_info["upnp_server"] = server_info
    else:
        health_info["upnp_server"] = None
        health_info["upnp_error"] = "No UPnP server connected"

    return health_info


@app.post("/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger a manual scan of UPnP media server."""
    if not upnp_client:
        raise HTTPException(status_code=503, detail="UPnP client not available")

    background_tasks.add_task(scan_media_files)
    return {"message": "UPnP media scan started in background"}


@app.get("/upnp/server")
async def get_upnp_server_info():
    """Get information about the connected UPnP server."""
    if not upnp_client:
        raise HTTPException(status_code=503, detail="UPnP client not available")

    server_info = upnp_client.get_server_info()
    if not server_info:
        raise HTTPException(status_code=404, detail="No UPnP server connected")

    return server_info


@app.get("/upnp/discover")
async def discover_upnp_servers():
    """Discover available UPnP media servers."""
    try:
        client = UPnPClient()
        servers = await client.discover_media_servers(settings.upnp_discovery_timeout)

        server_list = []
        for server in servers:
            server_list.append(
                {
                    "name": server.name,
                    "udn": server.udn,
                    "base_url": server.base_url,
                    "content_directory_url": server.content_directory_url,
                }
            )

        return {"servers": server_list, "count": len(server_list)}
    except Exception as e:
        logger.error(f"Error listing shares: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upnp/reconnect")
async def reconnect_upnp_server(
    server_name: Optional[str] = Query(
        None, description="Specific server name to connect to"
    )
):
    """Reconnect to UPnP media server, optionally specifying a server name."""
    global upnp_client, playlist_gen

    try:
        logger.info("Attempting to reconnect to UPnP media server...")

        if server_name:
            # Connect to specific server
            upnp_client = UPnPClient()
            await upnp_client.discover_media_servers(settings.upnp_discovery_timeout)
            if upnp_client.connect_to_server(server_name):
                logger.info(f"Connected to specified UPnP server: {server_name}")
            else:
                logger.error(f"Could not connect to specified server: {server_name}")
                raise HTTPException(
                    status_code=404, detail=f"Server '{server_name}' not found"
                )
        else:
            # Auto-discover Fritz Box or first available server
            server = await discover_fritz_box_media_server()
            if server:
                upnp_client = UPnPClient()
                upnp_client.discovered_servers = [server]
                upnp_client.connect_to_server()
                logger.info(f"Connected to UPnP media server: {server.name}")
            else:
                logger.error("No UPnP media servers found")
                raise HTTPException(
                    status_code=404, detail="No UPnP media servers found"
                )

        if upnp_client and upnp_client.connected_server:
            playlist_gen = PlaylistGenerator(upnp_client)
            logger.info("UPnP media server connection successful!")

            server_info = upnp_client.get_server_info()
            return {
                "message": "Successfully reconnected to UPnP server",
                "server": server_info,
            }
        else:
            raise HTTPException(
                status_code=500, detail="Failed to establish UPnP connection"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reconnecting to UPnP server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/media", response_model=List[MediaFileResponse])
async def get_media_files(
    share_name: Optional[str] = Query(None, description="Filter by share name"),
    file_type: Optional[str] = Query(None, description="Filter by file type"),
    search: Optional[str] = Query(None, description="Search in file names"),
):
    """Get cached media files with optional filters."""
    try:
        media_files = await db_manager.get_media_files(share_name, file_type, search)

        # Convert to response model
        response_files = []
        for file in media_files:
            # UPnP URLs would be provided directly from the media server
            upnp_url = file.path  # For UPnP, the path is typically the direct URL
            response_files.append(
                MediaFileResponse(
                    id=file.id,
                    path=file.path,
                    name=file.name,
                    size=file.size,
                    modified_time=file.modified_time,
                    file_type=file.file_type,
                    share_name=file.share_name,
                    cached_at=file.cached_at,
                    smb_url=upnp_url,
                )
            )

        return response_files
    except Exception as e:
        logger.error(f"Error getting media files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_cache_stats():
    """Get statistics about cached media files."""
    try:
        stats = await db_manager.get_cache_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/playlists", response_model=PlaylistResponse)
async def create_playlist(playlist_data: PlaylistCreate):
    """Create a new playlist."""
    try:
        db_playlist = await db_manager.create_playlist(playlist_data)

        return PlaylistResponse(
            id=db_playlist.id,
            name=db_playlist.name,
            description=db_playlist.description,
            file_paths=json.loads(db_playlist.file_paths),
            created_at=db_playlist.created_at,
            updated_at=db_playlist.updated_at,
        )
    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/playlists", response_model=List[PlaylistResponse])
async def get_playlists():
    """Get all playlists."""
    try:
        playlists = await db_manager.get_playlists()

        response_playlists = []
        for playlist in playlists:
            response_playlists.append(
                PlaylistResponse(
                    id=playlist.id,
                    name=playlist.name,
                    description=playlist.description,
                    file_paths=json.loads(playlist.file_paths),
                    created_at=playlist.created_at,
                    updated_at=playlist.updated_at,
                )
            )

        return response_playlists
    except Exception as e:
        logger.error(f"Error getting playlists: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/playlists/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(playlist_id: int):
    """Get a specific playlist."""
    try:
        playlist = await db_manager.get_playlist(playlist_id)
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")

        return PlaylistResponse(
            id=playlist.id,
            name=playlist.name,
            description=playlist.description,
            file_paths=json.loads(playlist.file_paths),
            created_at=playlist.created_at,
            updated_at=playlist.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting playlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/playlists/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(playlist_id: int, playlist_data: PlaylistCreate):
    """Replace a playlist's name, description, and items."""
    name = (playlist_data.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    if not isinstance(playlist_data.file_paths, list):
        raise HTTPException(status_code=400, detail="file_paths must be a list")

    try:
        updated = await db_manager.update_playlist(
            playlist_id,
            name=name,
            description=playlist_data.description or "",
            file_paths=playlist_data.file_paths,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=409, detail=f"A playlist named '{name}' already exists"
        )

    if not updated:
        raise HTTPException(status_code=404, detail="Playlist not found")

    return PlaylistResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
        file_paths=json.loads(updated.file_paths),
        created_at=updated.created_at,
        updated_at=updated.updated_at,
    )


@app.delete("/playlists/{playlist_id}")
async def delete_playlist(playlist_id: int):
    """Delete a playlist."""
    try:
        success = await db_manager.delete_playlist(playlist_id)
        if not success:
            raise HTTPException(status_code=404, detail="Playlist not found")

        return {"message": "Playlist deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting playlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/playlists/{playlist_id}/download")
async def download_playlist_m3u(playlist_id: int):
    """Download playlist as M3U file."""
    if not playlist_gen:
        raise HTTPException(status_code=503, detail="Playlist generator not available")

    try:
        # Get playlist
        playlist = await db_manager.get_playlist(playlist_id)
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")

        # Get media files for the playlist
        file_paths = json.loads(playlist.file_paths)
        all_media_files = await db_manager.get_media_files()

        # Filter media files that are in the playlist
        playlist_media_files = [f for f in all_media_files if f.path in file_paths]

        # Check if we found all the files
        if len(playlist_media_files) != len(file_paths):
            logger.warning(
                f"Playlist {playlist_id}: Found {len(playlist_media_files)} files out of {len(file_paths)} expected"
            )

        if not playlist_media_files:
            raise HTTPException(
                status_code=404, detail="No media files found for this playlist"
            )

        # Generate M3U content
        m3u_content = playlist_gen.generate_m3u_content(playlist, playlist_media_files)

        # Create safe filename - use .vlc.m3u to suggest VLC opening
        safe_name = "".join(
            c for c in playlist.name if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        filename = f"{safe_name}.vlc.m3u"

        return Response(
            content=m3u_content.encode("utf-8"),
            media_type="audio/x-mpegurl",  # Proper MIME type for M3U files
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading playlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/media/{file_id}/download.m3u")
async def download_media_m3u(file_id: int):
    """Download a single media file as a one-item M3U playlist (opens in VLC)."""
    if not playlist_gen:
        raise HTTPException(status_code=503, detail="Playlist generator not available")

    try:
        all_files = await db_manager.get_media_files()
        media_file = next((f for f in all_files if f.id == file_id), None)
        if not media_file:
            raise HTTPException(status_code=404, detail="Media file not found")

        title = Path(media_file.name).stem or "media"
        transient = SimpleNamespace(
            name=title,
            description=None,
            file_paths=json.dumps([media_file.path]),
        )
        m3u_content = playlist_gen.generate_m3u_content(transient, [media_file])

        safe_name = "".join(
            c for c in title if c.isalnum() or c in (" ", "-", "_")
        ).rstrip() or "media"
        filename = f"{safe_name}.vlc.m3u"

        return Response(
            content=m3u_content.encode("utf-8"),
            media_type="audio/x-mpegurl",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating single-file M3U: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _parse_m3u(content: str, fallback_name: str) -> dict:
    """Parse M3U content into {name, description, urls}. Raises ValueError on bad input."""
    # Strip BOM and normalise line endings
    if content.startswith("﻿"):
        content = content[1:]
    lines = [line.rstrip("\r") for line in content.split("\n")]

    # First non-empty line must be #EXTM3U
    first_meaningful = next((line.strip() for line in lines if line.strip()), "")
    if first_meaningful != "#EXTM3U":
        raise ValueError("Not a valid M3U file (missing #EXTM3U header)")

    name = fallback_name
    description_lines: list[str] = []
    urls: list[str] = []
    seen_urls: set[str] = set()

    # State: have we seen #PLAYLIST yet? Used to gate description-comment collection.
    saw_playlist = False
    in_description_block = False
    # Hard-coded VLC instructions added by our exporter — skip them in descriptions
    vlc_instruction_markers = (
        "TO OPEN IN VLC",
        "Right-click this file",
        "drag this file into VLC",
        "open -a VLC",
        "Double-clicking opens Apple Music",
    )

    for raw in lines:
        line = raw.strip()
        if not line:
            in_description_block = False
            continue

        if line.startswith("#PLAYLIST:"):
            name = line[len("#PLAYLIST:") :].strip() or fallback_name
            saw_playlist = True
            in_description_block = True
            continue

        if line.startswith("#EXTINF"):
            in_description_block = False
            continue

        if line.startswith("#"):
            if saw_playlist and in_description_block:
                comment = line.lstrip("#").strip()
                if comment and not any(m in comment for m in vlc_instruction_markers):
                    description_lines.append(comment)
            continue

        # URL line
        if line not in seen_urls:
            seen_urls.add(line)
            urls.append(line)
        in_description_block = False

    if not urls:
        raise ValueError("No media URLs found in file")

    description = "\n".join(description_lines).strip()
    return {"name": name, "description": description, "urls": urls}


@app.post("/playlists/import", status_code=201)
async def import_playlist(file: UploadFile = File(...)):
    """Import an M3U file as a playlist. URLs are matched against the catalog by exact path."""
    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8 text")

    fallback = Path(file.filename or "playlist").stem
    # Strip the conventional .vlc suffix if present
    if fallback.endswith(".vlc"):
        fallback = fallback[: -len(".vlc")]
    fallback = fallback or "Imported playlist"

    try:
        parsed = _parse_m3u(content, fallback_name=fallback)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    all_files = await db_manager.get_media_files()
    catalog_paths = {f.path for f in all_files}
    matched = [u for u in parsed["urls"] if u in catalog_paths]
    unmatched = [u for u in parsed["urls"] if u not in catalog_paths]

    from .database import PlaylistCreate as PlaylistCreateModel

    playlist_data = PlaylistCreateModel(
        name=parsed["name"],
        description=parsed["description"],
        file_paths=matched,
    )

    try:
        db_playlist = await db_manager.create_playlist(playlist_data)
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=f"A playlist named '{parsed['name']}' already exists",
        )

    return {
        "playlist": PlaylistResponse(
            id=db_playlist.id,
            name=db_playlist.name,
            description=db_playlist.description,
            file_paths=json.loads(db_playlist.file_paths),
            created_at=db_playlist.created_at,
            updated_at=db_playlist.updated_at,
        ),
        "matched": len(matched),
        "unmatched": unmatched,
    }


@app.get("/playlists/auto/generate")
async def generate_auto_playlists():
    """Generate automatic playlists based on file types and directories."""
    if not playlist_gen:
        raise HTTPException(status_code=503, detail="Playlist generator not available")

    try:
        media_files = await db_manager.get_media_files()
        auto_playlists = playlist_gen.create_auto_playlists(media_files)
        smart_playlists = playlist_gen.create_smart_playlists(media_files)

        return {
            "auto_playlists": auto_playlists,
            "smart_playlists": smart_playlists,
            "total": len(auto_playlists) + len(smart_playlists),
        }
    except Exception as e:
        logger.error(f"Error generating auto playlists: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the server."""
    import uvicorn

    uvicorn.run(
        "nas_media_catalog.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
