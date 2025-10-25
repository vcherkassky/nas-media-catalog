# Setup Guide

This guide will help you get the NAS Media Catalog up and running locally with full UPnP support and Playwright e2e tests.

## Quick Setup

### 1. Prerequisites

- **Python 3.9+**: For the API backend
- **Node.js 18+**: For the UI frontend  
- **uv**: Python package manager ([Install uv](https://github.com/astral-sh/uv))

### 2. Clone and Setup

```bash
git clone <repository-url>
cd nas-media-catalog
```

### 3. Start the Application

#### Quick Start (Recommended)
```bash
# Start both API and UI locally
./scripts/dev-start.sh
```

#### Manual Start
```bash
# Terminal 1 - API
cd api && uv sync && uv run python run_server.py

# Terminal 2 - UI  
cd ui && npm install && npm start
```

**Access:**
- UI: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 4. Run End-to-End Tests

#### Against Running Services
```bash
# First, start the development environment
./scripts/dev-start.sh

# Then in another terminal, run tests
./scripts/test-e2e.sh
```

#### Start Services and Test
```bash
# Start services, run tests, then cleanup
./scripts/test-e2e.sh with-services
```

#### Interactive Testing
```bash
# UI mode for test development
./scripts/test-e2e.sh ui

# Headed mode (see browser)
./scripts/test-e2e.sh local headed
```

## Project Structure

```
nas-media-catalog/
├── api/                     # FastAPI backend
│   ├── src/nas_media_catalog/
│   ├── test/               # API tests
│   └── pyproject.toml
├── ui/                     # Express + Static frontend
│   ├── public/             # Static files (HTML, CSS, JS)
│   ├── server.js           # Express proxy server
│   └── package.json
├── e2e/                    # Playwright tests
│   ├── tests/              # Test specifications
│   ├── playwright.config.ts
│   └── package.json
├── scripts/                # Helper scripts
│   ├── dev-start.sh        # Start development environment
│   └── test-e2e.sh         # E2E test runner
└── README.md               # Full documentation
```

## Available Scripts

### Development
```bash
./scripts/dev-start.sh          # Start local development
```

### Testing
```bash
./scripts/test-e2e.sh           # E2E tests against running services
./scripts/test-e2e.sh with-services  # Start services, test, cleanup
./scripts/test-e2e.sh ui        # Interactive test development
cd api && python run_tests.py  # API unit/integration tests
```

## Configuration

### Environment Variables

Create `api/.env` for custom configuration:

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

## UPnP Configuration

The system automatically discovers UPnP media servers on your network. For Fritz!Box users, it will automatically connect to the Fritz!Box media server. For other devices, specify the server name in `UPNP_SERVER_NAME`.

## Troubleshooting

### Port Conflicts
If you get port conflicts:
```bash
# Check what's using the ports
lsof -i :8000 -i :3000

# Stop conflicting services and restart
./scripts/dev-start.sh
```

### UPnP Discovery Issues
If UPnP discovery fails:
1. Ensure your NAS/media server has UPnP enabled
2. Check network connectivity
3. Try specifying server name in `UPNP_SERVER_NAME`
4. Review API logs for discovery errors

### Test Failures
```bash
# View test report
cd e2e && npm run report

# Run tests in headed mode to debug
./scripts/test-e2e.sh local headed

# Check service health
curl http://localhost:3000/api/health
```

### Dependencies
```bash
# Reinstall API dependencies
cd api && uv sync

# Reinstall UI dependencies
cd ui && npm install

# Reinstall test dependencies
cd e2e && npm install && npx playwright install
```

## Next Steps

1. **Browse Media**: Access the UI and scan for media files
2. **Create Playlists**: Select media files and create playlists
3. **Download M3U**: Export playlists for VLC or other players
4. **Customize**: Modify configuration for your NAS setup
5. **Develop**: Add new features and run tests

## Development Workflow

1. **Make Changes**: Edit code in `api/` or `ui/`
2. **Test Locally**: Use `./scripts/dev-start.sh` for quick iteration
3. **Run Tests**: Use `./scripts/test-e2e.sh` to verify functionality
4. **Commit**: Ensure all tests pass before committing

## Getting Help

- Check the full [README.md](README.md) for detailed documentation
- Review test files in `e2e/tests/` for usage examples
- Check API documentation at `/docs` endpoint
- Look at existing issues and create new ones for bugs/features

## Why No Docker?

Docker on macOS has limitations with UPnP/multicast networking that prevent proper media server discovery. Local development provides:
- ✅ Full UPnP multicast support
- ✅ Direct network access to media servers
- ✅ Better performance and debugging
- ✅ Simpler setup and maintenance