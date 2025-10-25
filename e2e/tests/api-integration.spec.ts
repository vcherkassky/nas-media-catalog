import { test, expect } from '@playwright/test';

test.describe('API Integration', () => {
  const apiUrl = process.env.API_URL || 'http://127.0.0.1:8000';

  test('should connect to API health endpoint', async ({ request }) => {
    const response = await request.get(`${apiUrl}/health`);
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('status', 'healthy');
    expect(data).toHaveProperty('database', 'connected');
  });

  test('should get server info from root endpoint', async ({ request }) => {
    const response = await request.get(`${apiUrl}/`);
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('message', 'NAS Media Catalog Server (UPnP)');
    expect(data).toHaveProperty('version', '0.1.0');
    expect(data).toHaveProperty('upnp_connected');
  });

  test('should get media files from API', async ({ request }) => {
    const response = await request.get(`${apiUrl}/media`);
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(Array.isArray(data)).toBeTruthy();
    
    // If there are media files, check their structure
    if (data.length > 0) {
      const mediaFile = data[0];
      expect(mediaFile).toHaveProperty('id');
      expect(mediaFile).toHaveProperty('name');
      expect(mediaFile).toHaveProperty('path');
      expect(mediaFile).toHaveProperty('file_type');
      expect(mediaFile).toHaveProperty('size');
    }
  });

  test('should get playlists from API', async ({ request }) => {
    const response = await request.get(`${apiUrl}/playlists`);
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(Array.isArray(data)).toBeTruthy();
    
    // If there are playlists, check their structure
    if (data.length > 0) {
      const playlist = data[0];
      expect(playlist).toHaveProperty('id');
      expect(playlist).toHaveProperty('name');
      expect(playlist).toHaveProperty('file_paths');
      expect(playlist).toHaveProperty('created_at');
      expect(Array.isArray(playlist.file_paths)).toBeTruthy();
    }
  });

  test('should get cache stats from API', async ({ request }) => {
    const response = await request.get(`${apiUrl}/stats`);
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(typeof data).toBe('object');
    // Stats structure depends on implementation, but should be an object
  });

  test('should trigger media scan via API', async ({ request }) => {
    const response = await request.post(`${apiUrl}/scan`);
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('message');
    expect(data.message).toContain('scan started');
  });

  test('should create and delete playlist via API', async ({ request }) => {
    // First, get available media files
    const mediaResponse = await request.get(`${apiUrl}/media`);
    const mediaFiles = await mediaResponse.json();
    
    if (mediaFiles.length === 0) {
      test.skip(true, 'No media files available for playlist creation test');
    }
    
    // Create a test playlist
    const playlistData = {
      name: `API Test Playlist ${Date.now()}`,
      description: 'Created via API test',
      file_paths: [mediaFiles[0].path]
    };
    
    const createResponse = await request.post(`${apiUrl}/playlists`, {
      data: playlistData
    });
    
    expect(createResponse.ok()).toBeTruthy();
    
    const createdPlaylist = await createResponse.json();
    expect(createdPlaylist).toHaveProperty('id');
    expect(createdPlaylist).toHaveProperty('name', playlistData.name);
    expect(createdPlaylist).toHaveProperty('description', playlistData.description);
    
    const playlistId = createdPlaylist.id;
    
    // Get the created playlist
    const getResponse = await request.get(`${apiUrl}/playlists/${playlistId}`);
    expect(getResponse.ok()).toBeTruthy();
    
    const retrievedPlaylist = await getResponse.json();
    expect(retrievedPlaylist.id).toBe(playlistId);
    expect(retrievedPlaylist.name).toBe(playlistData.name);
    
    // Download the playlist as M3U
    const downloadResponse = await request.get(`${apiUrl}/playlists/${playlistId}/download`);
    expect(downloadResponse.ok()).toBeTruthy();
    
    // Verify headers
    const contentType = downloadResponse.headers()['content-type'];
    expect(contentType).toContain('audio/x-mpegurl');
    
    const contentDisposition = downloadResponse.headers()['content-disposition'];
    expect(contentDisposition).toContain('attachment');
    expect(contentDisposition).toContain('.vlc.m3u');
    
    // Verify M3U content format
    const m3uContent = await downloadResponse.text();
    expect(m3uContent).toContain('#EXTM3U');
    expect(m3uContent).toContain(playlistData.name);
    
    // Critical: Verify no Python string escaping
    expect(m3uContent).not.toContain('\\n'); // Should not have literal \n
    expect(m3uContent).not.toContain('\\"'); // Should not have escaped quotes
    expect(m3uContent).not.toMatch(/^"/); // Should not start with quote
    expect(m3uContent).not.toMatch(/"$/); // Should not end with quote
    
    // Verify proper line breaks
    const lines = m3uContent.split('\n');
    expect(lines.length).toBeGreaterThan(3);
    expect(lines[0]).toBe('#EXTM3U');
    
    // Delete the playlist
    const deleteResponse = await request.delete(`${apiUrl}/playlists/${playlistId}`);
    expect(deleteResponse.ok()).toBeTruthy();
    
    const deleteResult = await deleteResponse.json();
    expect(deleteResult).toHaveProperty('message');
    expect(deleteResult.message).toContain('deleted successfully');
    
    // Verify playlist is deleted
    const verifyResponse = await request.get(`${apiUrl}/playlists/${playlistId}`);
    expect(verifyResponse.status()).toBe(404);
  });

  test('should filter media files via API', async ({ request }) => {
    // Test search filter
    const searchResponse = await request.get(`${apiUrl}/media?search=test`);
    expect(searchResponse.ok()).toBeTruthy();
    
    const searchResults = await searchResponse.json();
    expect(Array.isArray(searchResults)).toBeTruthy();
    
    // Test file type filter
    const typeResponse = await request.get(`${apiUrl}/media?file_type=mp4`);
    expect(typeResponse.ok()).toBeTruthy();
    
    const typeResults = await typeResponse.json();
    expect(Array.isArray(typeResults)).toBeTruthy();
    
    // If there are results, they should all be mp4
    if (typeResults.length > 0) {
      typeResults.forEach((file: any) => {
        expect(file.file_type).toBe('mp4');
      });
    }
  });

  test('should discover UPnP servers via API', async ({ request }) => {
    const response = await request.get(`${apiUrl}/upnp/discover`);
    
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data).toHaveProperty('servers');
    expect(data).toHaveProperty('count');
    expect(Array.isArray(data.servers)).toBeTruthy();
    expect(typeof data.count).toBe('number');
  });

  test('should get UPnP server info via API', async ({ request }) => {
    const response = await request.get(`${apiUrl}/upnp/server`);
    
    // This might return 503 if no UPnP server is connected, which is acceptable
    if (response.ok()) {
      const data = await response.json();
      expect(typeof data).toBe('object');
    } else {
      expect(response.status()).toBe(503);
    }
  });

  test('should generate auto playlists via API', async ({ request }) => {
    const response = await request.get(`${apiUrl}/playlists/auto/generate`);
    
    // This might return 503 if playlist generator is not available
    if (response.ok()) {
      const data = await response.json();
      expect(data).toHaveProperty('auto_playlists');
      expect(data).toHaveProperty('smart_playlists');
      expect(data).toHaveProperty('total');
      expect(Array.isArray(data.auto_playlists)).toBeTruthy();
      expect(Array.isArray(data.smart_playlists)).toBeTruthy();
    } else {
      expect(response.status()).toBe(503);
    }
  });

  test('should handle API errors gracefully', async ({ request }) => {
    // Test non-existent playlist
    const response = await request.get(`${apiUrl}/playlists/99999`);
    expect(response.status()).toBe(404);
    
    // Test invalid playlist creation
    const invalidResponse = await request.post(`${apiUrl}/playlists`, {
      data: {
        // Missing required fields
      }
    });
    expect(invalidResponse.status()).toBe(422); // Validation error
  });
});
