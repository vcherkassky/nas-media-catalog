import { test, expect } from '@playwright/test';

test.describe('Playlist Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for the app to load
    await expect(page.locator('#connection-status')).toContainText('Connected', { timeout: 10000 });
  });

  test('should create a new playlist with selected media files', async ({ page }) => {
    // Wait for media files to load
    await page.waitForSelector('.media-item', { timeout: 10000 });
    
    const mediaItems = page.locator('.media-item');
    const itemCount = await mediaItems.count();
    
    if (itemCount === 0) {
      // If no media files, skip this test
      test.skip(true, 'No media files available for testing');
    }
    
    // Select first two media files
    await mediaItems.nth(0).click();
    await mediaItems.nth(1).click();
    
    // Verify items are selected
    await expect(mediaItems.nth(0)).toHaveClass(/selected/);
    await expect(mediaItems.nth(1)).toHaveClass(/selected/);
    
    // Check that save button is enabled
    const saveBtn = page.locator('#save-playlist-btn');
    await expect(saveBtn).toBeEnabled();
    
    // Click save playlist button
    await saveBtn.click();
    
    // Modal should open
    const modal = page.locator('#playlist-modal');
    await expect(modal).toHaveClass(/show/);
    
    // Fill in playlist details
    const playlistName = `Test Playlist ${Date.now()}`;
    await page.locator('#playlist-name').fill(playlistName);
    await page.locator('#playlist-description').fill('Test playlist description');
    
    // Create playlist
    await page.locator('#create-playlist-btn').click();
    
    // Modal should close
    await expect(modal).not.toHaveClass(/show/);
    
    // Success toast should appear
    await expect(page.locator('.toast.success')).toContainText('Playlist created successfully');
    
    // Selection should be cleared
    await expect(mediaItems.nth(0)).not.toHaveClass(/selected/);
    await expect(mediaItems.nth(1)).not.toHaveClass(/selected/);
    
    // Save button should be disabled again
    await expect(saveBtn).toBeDisabled();
    
    // Check that playlist appears in sidebar
    await expect(page.locator('#playlists-list')).toContainText(playlistName);
  });

  test('should create playlist from new playlist button', async ({ page }) => {
    // Wait for media files to load and select some
    await page.waitForSelector('.media-item', { timeout: 10000 });
    
    const mediaItems = page.locator('.media-item');
    const itemCount = await mediaItems.count();
    
    if (itemCount === 0) {
      test.skip(true, 'No media files available for testing');
    }
    
    // Select a media file
    await mediaItems.nth(0).click();
    
    // Click new playlist button in sidebar
    await page.locator('#new-playlist-btn').click();
    
    // Modal should open
    const modal = page.locator('#playlist-modal');
    await expect(modal).toHaveClass(/show/);
    
    // Fill in playlist details
    const playlistName = `New Playlist ${Date.now()}`;
    await page.locator('#playlist-name').fill(playlistName);
    
    // Create playlist
    await page.locator('#create-playlist-btn').click();
    
    // Modal should close and playlist should be created
    await expect(modal).not.toHaveClass(/show/);
    await expect(page.locator('.toast.success')).toContainText('Playlist created successfully');
  });

  test('should cancel playlist creation', async ({ page }) => {
    // Open new playlist modal
    await page.locator('#new-playlist-btn').click();
    
    const modal = page.locator('#playlist-modal');
    await expect(modal).toHaveClass(/show/);
    
    // Fill in some data
    await page.locator('#playlist-name').fill('Test Playlist');
    
    // Cancel
    await page.locator('#cancel-playlist-btn').click();
    
    // Modal should close
    await expect(modal).not.toHaveClass(/show/);
  });

  test('should close modal by clicking backdrop', async ({ page }) => {
    // Open new playlist modal
    await page.locator('#new-playlist-btn').click();
    
    const modal = page.locator('#playlist-modal');
    await expect(modal).toHaveClass(/show/);
    
    // Click on backdrop (modal itself, not content)
    await modal.click({ position: { x: 10, y: 10 } });
    
    // Modal should close
    await expect(modal).not.toHaveClass(/show/);
  });

  test('should close modal by clicking X button', async ({ page }) => {
    // Open new playlist modal
    await page.locator('#new-playlist-btn').click();
    
    const modal = page.locator('#playlist-modal');
    await expect(modal).toHaveClass(/show/);
    
    // Click close button
    await page.locator('.modal-close').click();
    
    // Modal should close
    await expect(modal).not.toHaveClass(/show/);
  });

  test('should require playlist name', async ({ page }) => {
    // Wait for media files and select one
    await page.waitForSelector('.media-item', { timeout: 10000 });
    
    const mediaItems = page.locator('.media-item');
    const itemCount = await mediaItems.count();
    
    if (itemCount > 0) {
      await mediaItems.nth(0).click();
    }
    
    // Open new playlist modal
    await page.locator('#new-playlist-btn').click();
    
    // Try to create without name
    await page.locator('#create-playlist-btn').click();
    
    // Should show warning toast
    await expect(page.locator('.toast.warning')).toContainText('Please enter a playlist name');
    
    // Modal should still be open
    const modal = page.locator('#playlist-modal');
    await expect(modal).toHaveClass(/show/);
  });

  test('should require selected files for playlist', async ({ page }) => {
    // Open new playlist modal without selecting files
    await page.locator('#new-playlist-btn').click();
    
    // Fill in name
    await page.locator('#playlist-name').fill('Empty Playlist');
    
    // Try to create
    await page.locator('#create-playlist-btn').click();
    
    // Should show warning toast
    await expect(page.locator('.toast.warning')).toContainText('Please select some media files first');
  });

  test('should clear selection', async ({ page }) => {
    // Wait for media files to load
    await page.waitForSelector('.media-item', { timeout: 10000 });
    
    const mediaItems = page.locator('.media-item');
    const itemCount = await mediaItems.count();
    
    if (itemCount === 0) {
      test.skip(true, 'No media files available for testing');
    }
    
    // Select some files
    await mediaItems.nth(0).click();
    if (itemCount > 1) {
      await mediaItems.nth(1).click();
    }
    
    // Verify selection
    await expect(mediaItems.nth(0)).toHaveClass(/selected/);
    
    // Clear selection
    await page.locator('#clear-selection-btn').click();
    
    // Verify selection is cleared
    await expect(mediaItems.nth(0)).not.toHaveClass(/selected/);
    if (itemCount > 1) {
      await expect(mediaItems.nth(1)).not.toHaveClass(/selected/);
    }
    
    // Save button should be disabled
    await expect(page.locator('#save-playlist-btn')).toBeDisabled();
  });

  test.skip('should show selected items in current selection panel', async ({ page }) => {
    // This test is skipped because the media item selection functionality
    // is not yet implemented in the UI
  });

  test('should remove item from selection using remove button', async ({ page }) => {
    // Wait for media files to load
    await page.waitForSelector('.media-item', { timeout: 10000 });
    
    const mediaItems = page.locator('.media-item');
    const itemCount = await mediaItems.count();
    
    if (itemCount === 0) {
      test.skip(true, 'No media files available for testing');
    }
    
    // Select a file
    await mediaItems.nth(0).click();
    
    // Verify it's selected
    await expect(page.locator('#selected-items .selected-item')).toHaveCount(1);
    
    // Remove using the remove button in selection panel
    await page.locator('.remove-item-btn').click();
    
    // Should be removed from selection
    await expect(page.locator('#selected-items')).toContainText('No items selected');
    await expect(mediaItems.nth(0)).not.toHaveClass(/selected/);
  });

  test('should switch to playlists tab and view playlists', async ({ page }) => {
    // Switch to playlists tab
    await page.click('[data-tab="playlists"]');
    
    // Should show playlists content
    await expect(page.locator('#playlists-tab')).toHaveClass(/active/);
    await expect(page.locator('#playlists-tab h2')).toContainText('All Playlists');
    
    // Should show auto-generate button
    await expect(page.locator('#auto-generate-btn')).toBeVisible();
  });

  test('should generate auto playlists', async ({ page }) => {
    // Switch to playlists tab
    await page.click('[data-tab="playlists"]');
    
    const autoGenBtn = page.locator('#auto-generate-btn');
    
    // Click auto-generate
    await autoGenBtn.click();
    
    // Button should show loading state
    await expect(autoGenBtn).toContainText('Generating...');
    await expect(autoGenBtn).toBeDisabled();
    
    // Wait for completion
    await expect(autoGenBtn).toContainText('Auto Generate', { timeout: 10000 });
    await expect(autoGenBtn).toBeEnabled();
    
    // Should show success toast
    await expect(page.locator('.toast.success')).toBeVisible();
  });
});
