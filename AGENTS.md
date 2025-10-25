# NAS Media Catalog - Development Rules & Decisions

This document captures the key architectural decisions, coding standards, and lessons learned during the development of the NAS Media Catalog project. It serves as a guide for future development and AI-assisted coding sessions.

## 🏗️ Architecture Overview

### Project Structure
```
nas-media-catalog/
├── api/                    # Python FastAPI backend
│   ├── src/nas_media_catalog/
│   ├── test/              # Proper test structure (unit/integration/e2e)
│   └── run_server.py
├── ui/                    # Node.js Express + Static Frontend
│   ├── public/           # Static HTML/CSS/JS
│   └── server.js         # Proxy server
├── e2e/                  # Playwright E2E tests
├── scripts/              # Development scripts
└── docs/                 # Documentation
```

### Technology Stack
- **Backend**: Python 3.9+ with FastAPI, SQLAlchemy (async), SQLite
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **UI Server**: Node.js Express (proxy to avoid CORS)
- **Testing**: Playwright for E2E, pytest for backend
- **Package Management**: `uv` for Python, `npm` for Node.js

## 🎵 Media Catalog Core Concepts

### UPnP/DLNA Integration
- **Primary Protocol**: UPnP for media server discovery and content access
- **Server Discovery**: SSDP multicast for Fritz Box media server detection
- **Content Access**: Direct HTTP URLs to media files via UPnP

### SMB Fallback Support
- **Purpose**: Alternative access method when UPnP URLs don't work reliably in VLC
- **Configuration**: Optional SMB credentials in environment variables
- **URL Generation**: Convert UPnP paths to SMB URLs with proper encoding

### Playlist Management
- **Format**: M3U playlists with VLC compatibility focus
- **Storage**: SQLite database with JSON file path arrays
- **Generation**: Dynamic M3U creation with proper metadata

## 🔧 Critical Implementation Rules

### 1. M3U Playlist Format Compliance

**Character Sanitization in #EXTINF Entries:**
```python
# REQUIRED: Sanitize titles to prevent M3U parsing issues
def _sanitize_m3u_title(self, title: str) -> str:
    sanitized = title.replace(" - ", " • ")  # Prevent artist-title confusion
    sanitized = sanitized.replace(",", ";")   # Comma breaks EXTINF parsing
    sanitized = sanitized.replace(":", ".")   # Colon used in M3U directives
    sanitized = sanitized.replace("#", "No.") # Hash starts M3U comments
    return sanitized.strip() or "Unknown Title"
```

**Reasoning**: M3U format has strict parsing rules where certain characters have special meaning:
- `,` separates duration from title in `#EXTINF`
- `:` used in various M3U directives
- `#` starts comment/directive lines
- ` - ` commonly interpreted as artist-title separator

### 2. Download Response Handling

**UI Proxy Server Rule:**
```javascript
// CRITICAL: Special handling for download endpoints
if (apiPath.includes('/download')) {
  const response = await axios.get(fullUrl, { responseType: 'stream' });
  // Forward headers and pipe directly - NO JSON serialization
  response.data.pipe(res);
} else {
  // Regular JSON responses
  res.json(response.data);
}
```

**Reasoning**: Download responses must NOT be JSON-serialized as this converts proper content into Python string representations with escaped characters.

### 3. URL Encoding Standards

**SMB URL Encoding:**
```python
# REQUIRED: Proper URL encoding for special characters
def create_vlc_compatible_url(self, url: str) -> str:
    parsed = urlparse(url)
    # Encode path components while preserving separators
    encoded_path = '/'.join(quote(segment, safe='') for segment in parsed.path.split('/'))
    return urlunparse(parsed._replace(path=encoded_path))
```

**UPnP URL Handling:**
- Preserve original UPnP URLs as-is when possible
- Only apply encoding when specifically needed for VLC compatibility

### 4. File Association Handling (macOS)

**Problem**: `.m3u` files default to Apple Music on macOS, not VLC

**Solution:**
- Use `.vlc.m3u` extension to hint at VLC usage
- Include instructions in M3U file comments
- Provide clear user guidance on proper opening methods

```m3u
#EXTM3U
#PLAYLIST:Playlist Name
# TO OPEN IN VLC:
# • Right-click this file → Open With → VLC
# • OR drag this file into VLC window
# • OR use Terminal: open -a VLC filename.m3u
# (Double-clicking opens Apple Music, not VLC!)
```

## 🧪 Testing Strategy

### Test Structure
- **Unit Tests**: `api/test/unit/` - Individual function testing
- **Integration Tests**: `api/test/integration/` - Component interaction testing
- **API E2E Tests**: `api/test/e2e/` - Full API workflow testing
- **UI E2E Tests**: `e2e/` - Browser-based user workflow testing

### Critical E2E Test Cases
1. **Playlist Download Format Validation**: Verify M3U content is properly formatted (not Python string representation)
2. **Character Sanitization**: Test special characters in filenames are properly handled
3. **Cross-browser Compatibility**: Test download functionality across different browsers
4. **File Association Handling**: Verify correct filename extensions and headers

### Testing Anti-Patterns
- ❌ Never create temporary `test_*.py` files in project root
- ❌ Don't use print statements as test assertions
- ❌ Avoid hardcoded ports/URLs in tests (use environment variables)

## 🚫 Docker Limitations & Decisions

### macOS Docker Networking Issue
**Problem**: UPnP multicast discovery fails in Docker containers on macOS due to network isolation limitations.

**Decision**: Abandon Docker Compose for local development on macOS. Use native execution with development scripts.

**Alternative**: Provide Docker support for Linux/production environments only.

### Development Workflow
```bash
# Local development (macOS compatible)
./scripts/dev-start.sh

# E2E testing
./scripts/test-e2e.sh
```

## 🎯 Code Quality Standards

### Python Code Style
- Follow SOLID principles with pragmatic, minimal approach
- Use type hints consistently
- Prefer async/await for I/O operations
- Use `uv` for dependency management

### JavaScript Code Style
- Use modern ES6+ features
- Prefer `const`/`let` over `var`
- Use async/await over Promise chains
- Avoid jQuery or heavy frameworks - keep it vanilla

### Error Handling
- Use proper HTTP status codes
- Provide meaningful error messages
- Log errors with appropriate levels
- Graceful degradation for optional features

## 📊 Performance Considerations

### Database Operations
- Use async SQLAlchemy for non-blocking I/O
- Implement proper connection pooling
- Cache media file metadata to reduce UPnP calls

### Frontend Optimization
- Lazy load media lists for large catalogs
- Implement client-side filtering/searching
- Use proper HTTP caching headers

## 🔐 Security Guidelines

### Environment Configuration
- Never commit secrets to version control
- Use `.env` files with `.env.example` templates
- Validate and sanitize all user inputs

### Network Security
- CORS properly configured for UI proxy
- Validate UPnP server responses
- Sanitize file paths to prevent directory traversal

## 📝 Documentation Standards

### Code Documentation
- Document all public APIs
- Include usage examples for complex functions
- Explain architectural decisions in comments

### User Documentation
- Provide clear setup instructions
- Document configuration options
- Include troubleshooting guides

## 🔄 Development Workflow

### Branch Strategy
- Use feature branches for new functionality
- Require E2E tests for UI changes
- Test both UPnP and SMB scenarios

### Debugging Approach
1. Use proper logging instead of print statements
2. Create temporary scripts in `/tmp/` for debugging
3. Remove debug code before committing
4. Use E2E tests to validate fixes

### Release Process
1. Run full test suite (unit + integration + E2E)
2. Test on clean environment
3. Verify both UPnP and SMB functionality
4. Update documentation as needed

## 🎵 Media Format Support

### Supported Formats
- **Video**: MP4, MKV, AVI, MOV
- **Audio**: MP3, FLAC, WAV, AAC
- **Playlists**: M3U (VLC-optimized)

### VLC Compatibility
- Prioritize VLC compatibility over other players
- Test playlist functionality with VLC specifically
- Provide VLC-specific usage instructions

## 🔍 Troubleshooting Common Issues

### UPnP Discovery Failures
- Check network connectivity to media server
- Verify SSDP multicast is not blocked
- Consider SMB fallback for unreliable UPnP

### Playlist Playback Issues
- Verify character sanitization in filenames
- Check URL encoding for special characters
- Ensure proper M3U format compliance

### Development Environment Issues
- Use `127.0.0.1` instead of `localhost` to avoid IPv6 issues
- Ensure ports are properly configured and not conflicting
- Check that all required dependencies are installed

---

## 📚 Key Lessons Learned

1. **M3U Format is Strict**: Character sanitization is critical for playlist compatibility
2. **macOS File Associations Matter**: Default app handling affects user experience
3. **Docker Networking Limitations**: Not all networking scenarios work in containers
4. **E2E Tests are Essential**: They catch issues that unit tests miss
5. **Proxy Serialization Issues**: Be careful with response transformation in proxy layers
6. **Character Encoding Matters**: Proper URL encoding is crucial for special characters
7. **User Experience First**: Consider how users will actually interact with generated files

This document should be updated as new decisions are made and lessons are learned during continued development.

