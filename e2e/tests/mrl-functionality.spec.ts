import { test, expect } from '@playwright/test';

test.describe('MRL (Media Resource Locator) Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    
    // Wait for connection and media files to load
    await expect(page.locator('#connection-status')).toContainText('Connected', { timeout: 10000 });
    await page.waitForSelector('.media-item', { timeout: 10000 });
  });

  test('should render MRL buttons on media items in grid view', async ({ page }) => {
    const mediaItems = page.locator('.media-item');
    const firstItem = mediaItems.first();
    
    // Hover over the first media item to reveal MRL button
    await firstItem.hover();
    
    // Check that MRL link is visible
    const mrlLink = firstItem.locator('.mrl-link-btn');
    await expect(mrlLink).toBeVisible();
    await expect(mrlLink).toContainText('VLC');
    await expect(mrlLink.locator('i')).toHaveClass(/fa-external-link-alt/);
    
    // Check link attributes
    await expect(mrlLink).toHaveAttribute('href');
    await expect(mrlLink).toHaveAttribute('title', /Open in VLC.*UPnP URL/);
  });

  test('should render MRL buttons on media items in list view', async ({ page }) => {
    // Switch to list view
    await page.click('#list-view-btn');
    await expect(page.locator('#media-grid')).toHaveClass(/list-view/);
    
    const mediaItems = page.locator('.media-item');
    const firstItem = mediaItems.first();
    
    // In list view, MRL link should be always visible
    const mrlLink = firstItem.locator('.mrl-link-btn');
    await expect(mrlLink).toBeVisible();
    await expect(mrlLink).toContainText('VLC');
    
    // Check link attributes
    await expect(mrlLink).toHaveAttribute('href');
    await expect(mrlLink).toHaveAttribute('title', /Open in VLC.*UPnP URL/);
  });

  test('should have valid UPnP URLs in MRL links', async ({ page }) => {
    const mediaItems = page.locator('.media-item');
    const firstItem = mediaItems.first();
    
    // Hover to reveal MRL link
    await firstItem.hover();
    
    const mrlLink = firstItem.locator('.mrl-link-btn');
    const href = await mrlLink.getAttribute('href');
    
    // Check that the href contains a valid UPnP URL
    expect(href).toBeTruthy();
    expect(href).toMatch(/^https?:\/\//); // Should be a valid HTTP/HTTPS URL
    expect(href.length).toBeGreaterThan(10); // Should be a reasonable length
  });

  test('should have proper VLC protocol link', async ({ page }) => {
    const mediaItems = page.locator('.media-item');
    const firstItem = mediaItems.first();
    
    // Hover to reveal MRL button
    await firstItem.hover();
    
    const mrlLink = firstItem.locator('.mrl-link-btn');
    
    // Check that it's a proper link with UPnP URL
    const href = await mrlLink.getAttribute('href');
    expect(href).toMatch(/^https?:\/\//);
    expect(href.length).toBeGreaterThan(10); // Should be a reasonable length
    
    // Check that clicking doesn't cause unexpected errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        // Filter out expected media loading errors
        const errorText = msg.text();
        if (!errorText.includes('Failed to load resource') && 
            !errorText.includes('Plug-in handled load') &&
            !errorText.includes('Button failed to load')) {
          consoleErrors.push(errorText);
        }
      }
    });
    
    // Click the MRL link
    await mrlLink.click();
    
    // Wait a bit for any async operations
    await page.waitForTimeout(1000);
    
    // Check that no unexpected JavaScript errors occurred
    expect(consoleErrors).toHaveLength(0);
  });

  test('should have correct VLC protocol URL format', async ({ page }) => {
    const mediaItems = page.locator('.media-item');
    const firstItem = mediaItems.first();
    
    // Hover to reveal MRL link
    await firstItem.hover();
    
    const mrlLink = firstItem.locator('.mrl-link-btn');
    
    // Check that the href is properly formatted
    const href = await mrlLink.getAttribute('href');
    expect(href).toMatch(/^https?:\/\//); // Should be a valid HTTP/HTTPS URL
    expect(href.length).toBeGreaterThan(10); // Should be a reasonable length
    
    // Check that the link has proper attributes
    await expect(mrlLink).toHaveAttribute('title', /Open in VLC.*UPnP URL/);
  });

  test('should prevent event propagation when MRL link is clicked', async ({ page }) => {
    const mediaItems = page.locator('.media-item');
    const firstItem = mediaItems.first();
    
    // Hover to reveal MRL link
    await firstItem.hover();
    
    const mrlLink = firstItem.locator('.mrl-link-btn');
    
    // Click the MRL link with preventDefault to avoid navigation
    await mrlLink.click({ modifiers: ['Meta'] }); // Use Cmd/Ctrl+click to prevent navigation
    
    // Check that the media item is not selected (event propagation was prevented)
    await expect(firstItem).not.toHaveClass(/selected/);
  });

  test('should work with different media file types', async ({ page }) => {
    const mediaItems = page.locator('.media-item');
    const itemCount = await mediaItems.count();
    
    // Test MRL links on multiple items
    for (let i = 0; i < Math.min(itemCount, 3); i++) {
      const item = mediaItems.nth(i);
      
      // Hover to reveal MRL link
      await item.hover();
      
      const mrlLink = item.locator('.mrl-link-btn');
      await expect(mrlLink).toBeVisible();
      
      // Check that link has valid UPnP URL
      const href = await mrlLink.getAttribute('href');
      expect(href).toBeTruthy();
      expect(href).toMatch(/^https?:\/\//);
    }
  });

  test('should handle MRL button styling correctly', async ({ page }) => {
    const mediaItems = page.locator('.media-item');
    const firstItem = mediaItems.first();
    
    // Hover to reveal MRL button
    await firstItem.hover();
    
    const mrlButton = firstItem.locator('.mrl-link-btn');
    
    // Check button styling
    await expect(mrlButton).toHaveCSS('background-color', /rgb\(66, 153, 225\)/); // Blue background
    await expect(mrlButton).toHaveCSS('color', /rgb\(255, 255, 255\)/); // White text
    await expect(mrlButton).toHaveCSS('border-radius', '4px');
    await expect(mrlButton).toHaveCSS('cursor', 'pointer');
  });

  test('should handle MRL button hover effects', async ({ page }) => {
    const mediaItems = page.locator('.media-item');
    const firstItem = mediaItems.first();
    
    // Hover over media item to reveal MRL button
    await firstItem.hover();
    
    const mrlButton = firstItem.locator('.mrl-link-btn');
    
    // Hover over the MRL button itself
    await mrlButton.hover();
    
    // Check that hover effect is applied (darker blue background)
    await expect(mrlButton).toHaveCSS('background-color', /rgb\(49, 130, 206\)/);
  });

  test('should work in both grid and list view modes', async ({ page }) => {
    const mediaItems = page.locator('.media-item');
    const firstItem = mediaItems.first();
    
    // Test in grid view
    await expect(page.locator('#media-grid')).not.toHaveClass(/list-view/);
    await firstItem.hover();
    const gridMrlLink = firstItem.locator('.mrl-link-btn');
    await expect(gridMrlLink).toBeVisible();
    
    // Switch to list view
    await page.click('#list-view-btn');
    await expect(page.locator('#media-grid')).toHaveClass(/list-view/);
    
    // Test in list view (link should be always visible)
    const listMrlLink = firstItem.locator('.mrl-link-btn');
    await expect(listMrlLink).toBeVisible();
    
    // Both links should have the same href
    const gridHref = await gridMrlLink.getAttribute('href');
    const listHref = await listMrlLink.getAttribute('href');
    expect(gridHref).toBe(listHref);
  });

  test('should have proper link behavior for VLC protocol', async ({ page }) => {
    const mediaItems = page.locator('.media-item');
    const firstItem = mediaItems.first();
    
    // Hover to reveal MRL link
    await firstItem.hover();
    
    const mrlLink = firstItem.locator('.mrl-link-btn');
    const href = await mrlLink.getAttribute('href');
    
    // Check that the link has the correct UPnP URL
    expect(href).toMatch(/^https?:\/\//);
    
    // Check that clicking the link doesn't cause unexpected errors
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        // Filter out expected media loading errors
        const errorText = msg.text();
        if (!errorText.includes('Failed to load resource') && 
            !errorText.includes('Plug-in handled load') &&
            !errorText.includes('Button failed to load')) {
          consoleErrors.push(errorText);
        }
      }
    });
    
    // Click the MRL link
    await mrlLink.click();
    
    // Wait for any async operations
    await page.waitForTimeout(1000);
    
    // Check that no unexpected JavaScript errors occurred
    expect(consoleErrors).toHaveLength(0);
  });
});
