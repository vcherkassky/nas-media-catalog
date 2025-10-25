# Architecture Overview

## System Architecture

The NAS Media Catalog is built as a modern full-stack application with clear separation between the backend API and frontend UI.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   Node.js UI    │    │  Python API     │
│                 │◄──►│                 │◄──►│                 │
│  React-like SPA │    │  Express Proxy  │    │   FastAPI       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   UPnP Server   │
                                               │   (Fritz Box)   │
                                               └─────────────────┘
```

## Components

### 1. Python API (`/api`)

**Technology Stack:**
- FastAPI for REST API
- SQLAlchemy for database ORM
- SQLite for data storage
- UPnP client for media server communication

**Responsibilities:**
- UPnP server discovery and connection
- Media file scanning and caching
- Playlist creation and management
- M3U file generation
- Database operations

**Key Files:**
- `main.py` - FastAPI application and routes
- `upnp_client.py` - UPnP protocol implementation
- `database.py` - Data models and database operations
- `playlist_generator.py` - M3U playlist generation
- `config.py` - Configuration management

### 2. Node.js UI (`/ui`)

**Technology Stack:**
- Express.js for server and API proxy
- Vanilla JavaScript for frontend logic
- Modern CSS with responsive design
- Font Awesome for icons

**Responsibilities:**
- Serve static web assets
- Proxy API requests to avoid CORS issues
- Provide modern web interface
- Handle user interactions and state management

**Key Files:**
- `server.js` - Express server with API proxy
- `public/index.html` - Main HTML template
- `public/app.js` - Frontend application logic
- `public/styles.css` - Responsive CSS styles

## Data Flow

### 1. Media Discovery
```
UPnP Server → Python API → SQLite Database
```

### 2. User Interface
```
Browser → Node.js Proxy → Python API → Database
```

### 3. Playlist Generation
```
User Selection → Python API → M3U File → VLC Player
```

## API Design

The API follows REST principles with clear resource-based endpoints:

- **Media Resources**: `/media` - Browse and search media files
- **Playlist Resources**: `/playlists` - CRUD operations for playlists
- **UPnP Resources**: `/upnp/*` - UPnP server operations
- **System Resources**: `/health`, `/stats` - System information

## Security Considerations

- **CORS Handling**: Node.js proxy eliminates CORS issues
- **Input Validation**: FastAPI automatic validation
- **File System Access**: Read-only access to media files
- **Network Security**: UPnP discovery limited to local network

## Scalability

### Current Architecture
- Single-user application
- Local SQLite database
- Direct UPnP connections

### Future Enhancements
- Multi-user support with authentication
- PostgreSQL for larger datasets
- Caching layer (Redis)
- Background job processing
- Docker containerization

## Development Workflow

1. **API Development**: Develop and test API endpoints independently
2. **UI Development**: Build frontend features against stable API
3. **Integration Testing**: Test full stack functionality
4. **Deployment**: Both components can be deployed independently

## Configuration Management

- **Shared Config**: Environment variables in root `.env`
- **API Config**: Python-specific settings in `api/.env`
- **UI Config**: Node.js environment variables
- **Runtime Config**: Dynamic configuration through API endpoints
