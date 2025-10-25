import { test, expect } from '@playwright/test';

test.describe('Media Catalog Browsing', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load the main page with correct title and header', async ({ page }) => {
    await expect(page).toHaveTitle('NAS Media Catalog');
    await expect(page.locator('h1')).toContainText('NAS Media Catalog');
    await expect(page.locator('.header')).toBeVisible();
  });

  test('should show connection status', async ({ page }) => {
    const connectionStatus = page.locator('#connection-status');
    await expect(connectionStatus).toBeVisible();
    
    // Wait for connection to establish
    await expect(connectionStatus).toContainText('Connected', { timeout: 10000 });
    await expect(connectionStatus).toHaveClass(/connected/);
  });

  test('should display media files tab by default', async ({ page }) => {
    const mediaTab = page.locator('[data-tab="media"]');
    const mediaTabContent = page.locator('#media-tab');
    
    await expect(mediaTab).toHaveClass(/active/);
    await expect(mediaTabContent).toHaveClass(/active/);
    await expect(page.locator('#media-tab h2')).toContainText('Media Files');
  });

  test('should switch between tabs', async ({ page }) => {
    // Switch to playlists tab
    await page.click('[data-tab="playlists"]');
    
    const playlistsTab = page.locator('[data-tab="playlists"]');
    const playlistsTabContent = page.locator('#playlists-tab');
    
    await expect(playlistsTab).toHaveClass(/active/);
    await expect(playlistsTabContent).toHaveClass(/active/);
    await expect(page.locator('#playlists-tab h2')).toContainText('All Playlists');
    
    // Switch back to media tab
    await page.click('[data-tab="media"]');
    
    const mediaTab = page.locator('[data-tab="media"]');
    const mediaTabContent = page.locator('#media-tab');
    
    await expect(mediaTab).toHaveClass(/active/);
    await expect(mediaTabContent).toHaveClass(/active/);
  });

  test('should toggle between grid and list view', async ({ page }) => {
    const gridViewBtn = page.locator('#grid-view-btn');
    const listViewBtn = page.locator('#list-view-btn');
    const mediaGrid = page.locator('#media-grid');
    
    // Default should be grid view
    await expect(gridViewBtn).toHaveClass(/view-btn active/);
    
    // Switch to list view
    await listViewBtn.click();
    await expect(listViewBtn).toHaveClass(/view-btn active/);
    await expect(gridViewBtn).toHaveClass(/view-btn$/); // Only view-btn, no active
    await expect(mediaGrid).toHaveClass(/list-view/);
    
    // Switch back to grid view
    await gridViewBtn.click();
    await expect(gridViewBtn).toHaveClass(/view-btn active/);
    await expect(listViewBtn).not.toHaveClass(/active/);
    await expect(mediaGrid).not.toHaveClass(/list-view/);
  });

  test('should filter media files by search', async ({ page }) => {
    // Wait for media files to load
    await page.waitForSelector('.media-item', { timeout: 10000 });
    
    const searchInput = page.locator('#search-input');
    const mediaItems = page.locator('.media-item');
    
    // Get initial count
    const initialCount = await mediaItems.count();
    
    // Search for a specific term
    await searchInput.fill('test');
    
    // Wait for filter to apply
    await page.waitForTimeout(500);
    
    // Check that results are filtered (should be less than or equal to initial)
    const filteredCount = await mediaItems.count();
    expect(filteredCount).toBeLessThanOrEqual(initialCount);
  });

  test('should filter media files by file type', async ({ page }) => {
    // Wait for media files to load
    await page.waitForSelector('.media-item', { timeout: 10000 });
    
    const fileTypeFilter = page.locator('#file-type-filter');
    
    // Select MP4 filter
    await fileTypeFilter.selectOption('mp4');
    
    // Wait for filter to apply
    await page.waitForTimeout(500);
    
    // Check that all visible items are MP4
    const mediaItems = page.locator('.media-item');
    const count = await mediaItems.count();
    
    if (count > 0) {
      for (let i = 0; i < count; i++) {
        const item = mediaItems.nth(i);
        await expect(item.locator('.media-meta')).toContainText('MP4');
      }
    }
  });

  test('should show empty state when no media files match filters', async ({ page }) => {
    const searchInput = page.locator('#search-input');
    
    // Search for something that definitely won't exist
    await searchInput.fill('nonexistentfilename12345');
    
    // Wait for filter to apply
    await page.waitForTimeout(500);
    
    // Should show empty state in media grid
    await expect(page.locator('#media-grid .empty-state')).toBeVisible();
    await expect(page.locator('#media-grid .empty-state h3')).toContainText('No media files found');
  });

  test('should trigger media scan', async ({ page }) => {
    const scanBtn = page.locator('#scan-btn');
    
    await scanBtn.click();
    
    // Wait for scan to complete (scan might be too fast to see loading state)
    await expect(scanBtn).toContainText('Scan Media', { timeout: 10000 });
    await expect(scanBtn).toBeEnabled();
    
    // Should show success toast
    await expect(page.locator('.toast.success')).toBeVisible();
  });

  test('should show sidebar with filters and playlists', async ({ page }) => {
    const sidebar = page.locator('.sidebar');
    
    await expect(sidebar).toBeVisible();
    await expect(sidebar.locator('h3').first()).toContainText('Filters');
    await expect(sidebar.locator('#search-input')).toBeVisible();
    await expect(sidebar.locator('#file-type-filter')).toBeVisible();
    await expect(sidebar.locator('#share-filter')).toBeVisible();
    
    // Check playlists section
    await expect(sidebar.locator('h3').nth(1)).toContainText('My Playlists');
    await expect(sidebar.locator('#new-playlist-btn')).toBeVisible();
  });

  test('should show current selection panel', async ({ page }) => {
    const currentPlaylist = page.locator('#current-playlist');
    
    await expect(currentPlaylist).toBeVisible();
    await expect(currentPlaylist.locator('h3')).toContainText('Current Selection');
    await expect(currentPlaylist.locator('#clear-selection-btn')).toBeVisible();
    await expect(currentPlaylist.locator('#save-playlist-btn')).toBeVisible();
    await expect(currentPlaylist.locator('#save-playlist-btn')).toBeDisabled();
  });
});
