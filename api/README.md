# NAS Media Catalog API

FastAPI-based server that connects to your NAS via UPnP, caches media file information, and generates VLC-compatible playlists.

## Features

- 🔌 **UPnP Connection**: Connect to Fritz Box and other UPnP media servers
- 📁 **Media Scanning**: Recursively scan for audio and video files
- 💾 **Caching**: SQLite database for fast media catalog access
- 🎵 **Playlist Generation**: Create and download M3U playlists for VLC
- 🚀 **REST API**: Full REST API for integration with frontends
- ⚙️ **Configuration**: Environment variable configuration with .env support

## Supported Media Formats

**Video**: mp4, avi, mkv, mov, wmv, flv, webm, m4v  
**Audio**: mp3, flac, wav, aac, ogg, wma, m4a

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Configure Environment

Copy the environment file from the project root:

```bash
cp ../env.example .env
# Edit .env with your settings
```

### 3. Start API Server

```bash
# Using uv
uv run python run_server.py

# Or directly
python -m nas_media_catalog.main
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Server Information
- `GET /` - Server status and information
- `GET /health` - Health check
- `GET /stats` - Cache statistics

### UPnP Operations
- `GET /upnp/server` - Get UPnP server info
- `GET /upnp/discover` - Discover UPnP servers
- `POST /scan` - Trigger media scan

### Media Files
- `GET /media` - Get cached media files
  - Query params: `share_name`, `file_type`, `search`

### Playlists
- `GET /playlists` - List all playlists
- `POST /playlists` - Create new playlist
- `GET /playlists/{id}` - Get specific playlist
- `DELETE /playlists/{id}` - Delete playlist
- `GET /playlists/{id}/download` - Download M3U file
- `GET /playlists/auto/generate` - Generate automatic playlists

## Configuration

Set these environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `UPNP_DISCOVERY_TIMEOUT` | `10` | UPnP discovery timeout in seconds |
| `UPNP_SERVER_NAME` | `` | Specific UPnP server name (empty = auto-discover) |
| `SERVER_HOST` | `0.0.0.0` | Server bind address |
| `SERVER_PORT` | `8000` | Server port |
| `DATABASE_URL` | `sqlite+aiosqlite:///./media_catalog.db` | Database connection string |
| `MAX_SCAN_DEPTH` | `5` | Maximum directory depth for scanning |
| `AUTO_SCAN_ON_STARTUP` | `true` | Automatically scan on server start |
| `LOG_LEVEL` | `INFO` | Logging level |

## Development

### Testing

```bash
# Quick unit tests
python run_tests.py unit

# Integration tests (requires UPnP server)
python run_tests.py integration

# End-to-end tests
python run_tests.py e2e

# All tests
python run_tests.py all
```

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Architecture

```
api/
├── src/nas_media_catalog/
│   ├── __init__.py          # Package initialization
│   ├── config.py            # Configuration management
│   ├── database.py          # SQLAlchemy models and operations
│   ├── main.py              # FastAPI application
│   ├── playlist_generator.py # M3U playlist generation
│   └── upnp_client.py       # UPnP client implementation
├── test/                    # Test suite
├── run_server.py            # Server entry point
└── run_tests.py             # Test runner
```
