# NAS Media Catalog

A FastAPI-based server that connects to your NAS, caches media file information, and generates VLC-compatible playlists.

## Features

- 🔌 **NAS Connection**: Connect to SMB/CIFS shares with SMB v1 support for Fritz Box and automatic password/port testing
- 📁 **Media Scanning**: Recursively scan shares for audio and video files
- 💾 **Caching**: SQLite database for fast media catalog access
- 🎵 **Playlist Generation**: Create and download M3U playlists for VLC
- 🚀 **REST API**: Full REST API for integration with other tools
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

### 2. Configure NAS Credentials

Create a `.env` file in the project root:

```shell
cp env.example .env
```

**Note**: All logging is centralized through `config.py` with a consistent format across the application. Tests use `test/conftest.py` for automatic logging configuration.

### 3. Test Connection

```bash
# Using uv
uv run python tests/test_nas_connection.py

# Or directly
python tests/test_nas_connection.py
```

### 4. Start Server

```bash
# Using uv
uv run nas-media-catalog

# Or using the entry script
python run_server.py

# Or directly
python -m nas_media_catalog.main
```

The server will be available at `http://localhost:8000`

## API Endpoints

### Server Information
- `GET /` - Server status and information
- `GET /health` - Health check
- `GET /stats` - Cache statistics

### NAS Operations
- `GET /shares` - List available NAS shares
- `POST /scan` - Trigger full NAS scan
- `POST /scan/{share_name}` - Scan specific share

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

## Usage Examples

### Create a Playlist

```bash
curl -X POST "http://localhost:8000/playlists" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Favorites",
    "description": "My favorite songs",
    "file_paths": [
      "\\\\fritz.box\\music\\song1.mp3",
      "\\\\fritz.box\\music\\song2.mp3"
    ]
  }'
```

### Download Playlist for VLC

```bash
curl "http://localhost:8000/playlists/1/download" -o "My_Favorites.m3u"
```

Then open the `.m3u` file in VLC to play your playlist.

### Search Media Files

```bash
# Search by filename
curl "http://localhost:8000/media?search=beethoven"

# Filter by file type
curl "http://localhost:8000/media?file_type=mp3"

# Filter by share
curl "http://localhost:8000/media?share_name=music"
```

## Configuration Options

All configuration can be set via environment variables or `.env` file:

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

## Architecture

The application follows SOLID design principles with clear separation of concerns using the recommended `src/` layout:

```
src/nas_media_catalog/
├── __init__.py          # Package initialization and exports
├── config.py            # Configuration management with Pydantic settings
├── nas_client.py        # SMB client for NAS communication
├── database.py          # SQLAlchemy models and database operations
├── playlist_generator.py # M3U playlist generation logic
└── main.py              # FastAPI application with REST endpoints

tests/
├── __init__.py
├── test_basic.py        # Basic unit tests
├── test_nas_connection.py # End-to-end integration test
└── network_test.py      # Network connectivity diagnostics
```

## Development

### Testing

The project has a comprehensive test suite organized into different categories:

#### Test Categories

- **Unit Tests** (`@pytest.mark.unit`): Fast tests with no external dependencies
- **Integration Tests** (`@pytest.mark.integration`): Require Fritz Box/UPnP server on network  
- **End-to-End Tests** (`@pytest.mark.e2e`): Full system tests with real media server

#### Running Tests

```bash
# Quick unit tests (recommended for development)
python run_tests.py unit
# or: uv run pytest -m unit

# Integration tests (requires Fritz Box)
python run_tests.py integration
# or: uv run pytest -m integration

# End-to-end tests (full system test)
python run_tests.py e2e
# or: uv run pytest -m e2e

# All tests
python run_tests.py all
# or: uv run pytest

# Run specific test file
uv run pytest test/unit/test_basic.py -v
```

#### Test Structure

```
test/
├── unit/
│   └── test_basic.py              # Unit tests (fast, no dependencies)
├── integration/
│   └── test_integration_upnp.py   # UPnP discovery tests (requires network)
└── e2e/
    └── test_e2e_integration.py    # Full end-to-end tests (requires Fritz Box)
```

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

### Database Schema

The application uses SQLite with two main tables:
- `media_files`: Cached media file information
- `playlists`: User-created playlists

## Troubleshooting

### Connection Issues

1. **Check NAS accessibility**: Ensure your NAS is reachable from your network
2. **Verify credentials**: Test different password combinations in the `.env` file
3. **Firewall**: Ensure port 445 (SMB) is not blocked
4. **Share permissions**: Verify your user has read access to the shares

### Common Errors

- **"No working password found"**: Check your credentials in `.env`
- **"NAS client not available"**: Server couldn't connect to NAS on startup
- **"Share not found"**: The specified share name doesn't exist or isn't accessible

### Logs

Check the server logs for detailed error information. Set `LOG_LEVEL=DEBUG` for verbose logging.

## License

This project is open source and available under the MIT License.
