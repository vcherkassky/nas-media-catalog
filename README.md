# NAS Media Catalog

A comprehensive media catalog system for Network Attached Storage (NAS) devices with UPnP support, featuring a FastAPI backend and modern web UI for browsing and organizing media files into playlists.

## Features

- 🎵 **Media Discovery**: Automatic discovery and cataloging of media files via UPnP
- 📁 **Smart Organization**: Browse media files with filtering by type, share, and search
- 🎼 **Playlist Management**: Create, edit, and download VLC-compatible M3U playlists
- 🔄 **Auto Playlists**: Automatically generate playlists based on file types and directories
- 🌐 **Modern Web UI**: Responsive interface with grid/list views and real-time updates
- 🚀 **Local Development**: Optimized for local development with full UPnP support
- 🧪 **E2E Testing**: Comprehensive Playwright test suite for quality assurance

## Architecture

```
nas-media-catalog/
├── api/                    # FastAPI backend
│   ├── src/nas_media_catalog/
│   │   ├── main.py        # FastAPI application
│   │   ├── database.py    # SQLite database management
│   │   ├── upnp_client.py # UPnP discovery and browsing
│   │   └── config.py      # Configuration management
│   ├── test/              # API tests (unit, integration, e2e)
│   └── Dockerfile         # API container
├── ui/                    # Web frontend
│   ├── public/
│   │   ├── index.html     # Main UI
│   │   ├── app.js         # JavaScript application
│   │   └── styles.css     # Styling
│   ├── server.js          # Express proxy server
│   └── Dockerfile         # UI container
├── e2e/                   # Playwright end-to-end tests
│   ├── tests/             # Test specifications
│   ├── playwright.config.ts
│   └── Dockerfile         # Test runner container
├── docker compose.yml     # Development environment
└── docker compose.e2e.yml # Testing environment
```

## Quick Start

### Development Mode

1. **Start the API** (Python 3.9+):
   ```bash
   cd api
   pip install uv
   uv sync
   python run_server.py
   ```

2. **Start the UI** (Node.js 18+):
   ```bash
   cd ui
   npm install
   npm start
   ```

3. **Access the application**:
   - UI: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Quick Start Script

1. **Start both services**:
   ```bash
   ./scripts/dev-start.sh
   ```

2. **Cleanup only** (stop existing processes):
   ```bash
   ./scripts/dev-start.sh --cleanup
   ```

3. **Custom ports**:
   ```bash
   ./scripts/dev-start.sh --api-port 8001 --ui-port 3001
   ```

4. **Access the application**:
   - UI: http://localhost:3000
   - API: http://localhost:8000

#### Script Options

- `-h, --help` - Show help message
- `-c, --cleanup` - Only perform cleanup (kill existing processes)  
- `-s, --start` - Start services with cleanup (default)
- `--api-port` - Custom API port (default: 8000)
- `--ui-port` - Custom UI port (default: 3000)

### Running Tests

1. **API Tests**:
   ```bash
   cd api
   python run_tests.py
   ```

2. **End-to-End Tests**:
   ```bash
   ./scripts/test-e2e.sh
   ```

3. **E2E Tests with Services**:
   ```bash
   ./scripts/test-e2e.sh with-services
   ```

## Configuration

### Environment Variables

Create a `.env` file in the `api/` directory:

```env
# UPnP Settings
UPNP_DISCOVERY_TIMEOUT=10
UPNP_SERVER_NAME=

# Server Settings  
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Database
DATABASE_URL=sqlite+aiosqlite:///./media_catalog.db

# Scanning
MAX_SCAN_DEPTH=5
AUTO_SCAN_ON_STARTUP=true

# Logging
LOG_LEVEL=INFO
```

### UPnP Configuration

The system automatically discovers UPnP media servers on your network. For Fritz!Box users, it will automatically connect to the Fritz!Box media server. For other devices, specify the server name in `UPNP_SERVER_NAME`.

## Usage

### Browsing Media

1. **Automatic Discovery**: The system automatically scans for UPnP media servers on startup
2. **Manual Scan**: Click "Scan Media" to refresh the media catalog
3. **Filtering**: Use search, file type, and share filters to find specific content
4. **View Modes**: Switch between grid and list views for different browsing experiences

### Creating Playlists

1. **Select Media**: Click on media files to select them (multi-select supported)
2. **Create Playlist**: Click "Save as Playlist" or "New Playlist"
3. **Name & Describe**: Enter playlist name and optional description
4. **Save**: Your playlist is saved and can be downloaded as M3U

### Managing Playlists

- **View**: Click the eye icon to load playlist items into selection
- **Download**: Click download to get VLC-compatible M3U file
- **Delete**: Remove playlists you no longer need
- **Auto-Generate**: Create automatic playlists based on file organization

## API Endpoints

### Core Endpoints
- `GET /` - Server information
- `GET /health` - Health check
- `POST /scan` - Trigger media scan

### Media Management
- `GET /media` - List media files (with filtering)
- `GET /stats` - Cache statistics

### Playlist Management
- `GET /playlists` - List all playlists
- `POST /playlists` - Create new playlist
- `GET /playlists/{id}` - Get specific playlist
- `DELETE /playlists/{id}` - Delete playlist
- `GET /playlists/{id}/download` - Download M3U file

### UPnP Integration
- `GET /upnp/discover` - Discover UPnP servers
- `GET /upnp/server` - Current server info
- `GET /playlists/auto/generate` - Generate automatic playlists

## Testing

### Test Categories

1. **Unit Tests** (`api/test/unit/`): Core functionality testing
2. **Integration Tests** (`api/test/integration/`): Component interaction testing  
3. **E2E Tests** (`api/test/e2e/` & `e2e/tests/`): Full system testing
4. **Playwright Tests** (`e2e/`): Browser-based UI testing

### Test Features

- ✅ Media catalog browsing and filtering
- ✅ Playlist creation and management
- ✅ File selection and UI interactions
- ✅ API integration and error handling
- ✅ UPnP discovery and connection
- ✅ Download functionality
- ✅ Responsive design testing

### Running Specific Tests

```bash
# API unit tests only
cd api && python -m pytest test/unit/ -v

# API integration tests (requires network)
cd api && python -m pytest test/integration/ -v -m integration

# API e2e tests (full system)
cd api && python -m pytest test/e2e/ -v -m e2e

# Playwright UI tests
cd e2e && npm test

# Specific test file
cd e2e && npx playwright test catalog-browsing.spec.ts
```

## Docker Services

### Development (`docker compose.yml`)
- **api**: Port 8001 → 8000
- **ui**: Port 3001 → 3000
- **Volumes**: Persistent API data

### Testing (`docker compose.e2e.yml`)
- **api**: Port 8002 → 8000 (test database)
- **ui**: Port 3002 → 3000
- **playwright**: Test runner (profile: test)

## Troubleshooting

### UPnP Connection Issues
1. Ensure UPnP is enabled on your NAS/media server
2. Check network connectivity and firewall settings
3. Try manual server specification via `UPNP_SERVER_NAME`
4. Review logs for discovery timeout issues

### Docker Issues
1. Ensure ports 8001/3001 (dev) or 8002/3002 (test) are available
2. Check Docker daemon is running
3. Verify no conflicting containers: `docker ps`
4. Review service logs: `docker compose logs [service]`

### Test Failures
1. Check service health: `docker compose ps`
2. Review test reports: `cd e2e && npm run report`
3. Run tests in headed mode: `cd e2e && npm run test:headed`
4. Check screenshots/videos in `e2e/test-results/`

## Contributing

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Add tests** for new functionality
4. **Run tests**: `npm test` (e2e) and `python run_tests.py` (api)
5. **Commit** changes: `git commit -m 'Add amazing feature'`
6. **Push** to branch: `git push origin feature/amazing-feature`
7. **Open** a Pull Request

### Development Guidelines

- Follow SOLID principles and pragmatic design
- Maintain clear separation between API and UI
- Write tests for new features
- Update documentation for API changes
- Use TypeScript for new frontend code
- Follow existing code style and conventions

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **FastAPI** for the excellent Python web framework
- **Playwright** for robust end-to-end testing
- **UPnP** community for media server standards
- **VLC Media Player** for M3U playlist compatibility