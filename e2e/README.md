# End-to-End Tests

This directory contains Playwright end-to-end tests for the NAS Media Catalog application.

## Setup

1. Install dependencies:
   ```bash
   cd e2e
   npm install
   npx playwright install
   ```

2. Make sure Docker and Docker Compose are installed on your system.

## Running Tests

### Local Development

Run tests against local development servers:
```bash
npm test
```

Run tests in headed mode (see browser):
```bash
npm run test:headed
```

Run tests with UI mode (interactive):
```bash
npm run test:ui
```

Debug tests:
```bash
npm run test:debug
```

### Docker Environment

Run tests against Docker containers:
```bash
# Start services and run tests
docker compose -f ../docker compose.e2e.yml up --build --abort-on-container-exit

# Or run tests in Docker container
docker compose -f ../docker compose.e2e.yml run --rm playwright npm test
```

### CI/CD

For continuous integration, set the `CI` environment variable:
```bash
CI=true npm test
```

## Test Structure

- `tests/catalog-browsing.spec.ts` - Tests for browsing media files, filtering, and UI interactions
- `tests/playlist-management.spec.ts` - Tests for creating and managing playlists
- `tests/playlist-operations.spec.ts` - Tests for playlist operations (view, download, delete)
- `tests/api-integration.spec.ts` - Direct API testing and integration tests

## Configuration

- `playwright.config.ts` - Main Playwright configuration
- `global-setup.ts` - Global setup that waits for services to be ready
- `global-teardown.ts` - Global cleanup after tests

## Environment Variables

- `BASE_URL` - URL of the UI application (default: http://localhost:3002)
- `API_URL` - URL of the API server (default: http://localhost:8002)
- `CI` - Set to true for CI environments

## Docker Compose Services

The e2e tests use `docker compose.e2e.yml` which extends the main docker compose configuration:

- **api**: API server on port 8002
- **ui**: UI server on port 3002  
- **playwright**: Test runner container (profile: test)

## Test Features

### Catalog Browsing
- ✅ Load main page and verify UI elements
- ✅ Check connection status
- ✅ Switch between tabs (Media Files / Playlists)
- ✅ Toggle between grid and list view
- ✅ Filter media files by search, file type, and share
- ✅ Trigger media scan
- ✅ Show empty states appropriately

### Playlist Management
- ✅ Create playlists with selected media files
- ✅ Create playlists from "New Playlist" button
- ✅ Cancel playlist creation
- ✅ Validate required fields (name, selected files)
- ✅ Clear selection
- ✅ Show selected items in current selection panel
- ✅ Remove items from selection
- ✅ Generate auto playlists

### Playlist Operations
- ✅ View existing playlists
- ✅ Download playlists as M3U files
- ✅ Delete playlists with confirmation
- ✅ View/download from sidebar
- ✅ Display playlist metadata correctly
- ✅ Handle empty states

### API Integration
- ✅ Health check and server info
- ✅ CRUD operations for playlists
- ✅ Media file retrieval and filtering
- ✅ UPnP server discovery and info
- ✅ Auto playlist generation
- ✅ Error handling

## Troubleshooting

### Services Not Starting
If services fail to start, check:
1. Docker is running
2. Ports 8002 and 3002 are available
3. No conflicting containers are running

### Tests Timing Out
If tests timeout waiting for services:
1. Increase timeout in `global-setup.ts`
2. Check service logs: `docker compose -f ../docker compose.e2e.yml logs`
3. Verify services are healthy: `docker compose -f ../docker compose.e2e.yml ps`

### Test Failures
1. Check test reports: `npm run report`
2. Review screenshots and videos in `test-results/`
3. Run tests in headed mode to see what's happening: `npm run test:headed`

## Contributing

When adding new tests:
1. Follow the existing test structure and naming conventions
2. Use appropriate `test.describe` blocks to group related tests
3. Add proper `test.beforeEach` setup
4. Include both positive and negative test cases
5. Test error conditions and edge cases
6. Update this README if adding new test categories
