# NAS Media Catalog UI

Modern web interface for browsing your NAS media catalog and creating playlists.

## Features

- 📱 **Responsive Design**: Works on desktop, tablet, and mobile
- 🔍 **Advanced Filtering**: Search by name, file type, and share
- 📋 **Playlist Management**: Create, view, edit, and download playlists
- 🎵 **VLC Integration**: Download M3U playlists for VLC player
- ⚡ **Real-time Updates**: Live connection status and instant feedback
- 🎨 **Modern UI**: Clean, intuitive interface with grid/list views

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Start the UI Server

```bash
npm start
```

The UI will be available at `http://localhost:3000`

### 3. Start the API Server

Make sure the NAS Media Catalog API is running on `http://localhost:8000`:

```bash
# In the api directory
cd ../api
uv run python -m run_server
```

## Usage

### Browsing Media

1. **View Media Files**: Browse all your media files in grid or list view
2. **Filter Content**: Use the sidebar filters to find specific files
3. **Search**: Type in the search box to find files by name
4. **Select Files**: Click on media items to add them to your current selection

### Creating Playlists

1. **Select Media**: Choose files you want in your playlist
2. **Create Playlist**: Click "Save as Playlist" in the selection panel
3. **Name & Describe**: Give your playlist a name and optional description
4. **Save**: Your playlist is now available in the sidebar and playlists tab

### Managing Playlists

- **View**: Click the eye icon to load a playlist's contents
- **Download**: Click download to get an M3U file for VLC
- **Delete**: Remove playlists you no longer need
- **Auto-Generate**: Create smart playlists based on file types and directories

## Configuration

### Environment Variables

- `PORT`: UI server port (default: 3000)
- `API_BASE_URL`: API server URL (default: http://localhost:8000)

### Example

```bash
PORT=4000 API_BASE_URL=http://192.168.1.100:8000 npm start
```

## Development

### File Structure

```
ui/
├── server.js          # Express server with API proxy
├── package.json       # Dependencies and scripts
├── public/
│   ├── index.html     # Main HTML template
│   ├── styles.css     # CSS styles and responsive design
│   └── app.js         # JavaScript application logic
└── README.md          # This file
```

### API Proxy

The Node.js server acts as a proxy to avoid CORS issues:
- UI requests to `/api/*` are forwarded to the Python API
- Supports GET, POST, and DELETE methods
- Handles errors gracefully with user-friendly messages

### Development Mode

```bash
npm run dev  # Uses nodemon for auto-restart
```

## Browser Support

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Troubleshooting

### Connection Issues

1. **Check API Server**: Ensure the Python API is running on port 8000
2. **Network Access**: Verify the API server is accessible from your browser
3. **CORS**: The proxy server handles CORS, so direct API access isn't needed

### Common Errors

- **"Disconnected" status**: API server is not running or unreachable
- **"Failed to load media files"**: Check API server logs for UPnP connection issues
- **Empty media list**: Run a media scan from the UI or check NAS connectivity

### Performance

- Large media collections (1000+ files) may take a few seconds to load
- Filtering and search are performed client-side for instant results
- Playlists are cached locally until refresh