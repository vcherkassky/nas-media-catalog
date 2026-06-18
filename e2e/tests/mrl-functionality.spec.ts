import { test, expect } from '@playwright/test';
import * as fs from 'fs';

test.describe('VLC button — downloads single-item M3U', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#connection-status')).toContainText('Connected', { timeout: 10000 });
    await page.waitForSelector('.media-item', { timeout: 10000 });
  });

  test('renders on every media item in grid view (visible on hover)', async ({ page }) => {
    const first = page.locator('.media-item').first();
    const btn = first.locator('.mrl-link-btn');

    await first.hover();
    await expect(btn).toBeVisible();
    await expect(btn).toContainText('VLC');
    // After hover, parent opacity should be 1
    await expect(first.locator('.media-actions')).toHaveCSS('opacity', '1');
  });

  test('renders inline (always visible) in list view', async ({ page }) => {
    await page.click('#list-view-btn');
    await expect(page.locator('#media-grid')).toHaveClass(/list-view/);
    const btn = page.locator('.media-item').first().locator('.mrl-link-btn');
    await expect(btn).toBeVisible();
  });

  test('href points at the single-item M3U endpoint', async ({ page }) => {
    const first = page.locator('.media-item').first();
    await first.hover();
    const btn = first.locator('.mrl-link-btn');
    const fileId = await first.getAttribute('data-file-id');

    await expect(btn).toHaveAttribute('href', `/api/media/${fileId}/download.m3u`);
    await expect(btn).toHaveAttribute('download', '');
    await expect(btn).toHaveAttribute('title', /VLC/);
  });

  test('clicking triggers an M3U download with VLC-compatible content', async ({ page }) => {
    const first = page.locator('.media-item').first();
    await first.hover();
    const btn = first.locator('.mrl-link-btn');

    const downloadPromise = page.waitForEvent('download');
    await btn.click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toMatch(/\.vlc\.m3u$/);

    const path = await download.path();
    expect(path).toBeTruthy();
    const body = fs.readFileSync(path!, 'utf-8');
    expect(body.startsWith('#EXTM3U')).toBe(true);
    expect(body).toMatch(/#EXTINF:-1,/);
    expect(body).toMatch(/TO OPEN IN VLC/);
    // Should contain exactly one media URL line (one non-empty line that isn't a directive/comment)
    const urlLines = body.split('\n').filter(l => l && !l.startsWith('#'));
    expect(urlLines.length).toBe(1);
    expect(urlLines[0]).toMatch(/^https?:\/\//);
  });

  test('click does not select the underlying media item', async ({ page }) => {
    const first = page.locator('.media-item').first();
    await first.hover();
    await expect(first).not.toHaveClass(/selected/);

    const downloadPromise = page.waitForEvent('download');
    await first.locator('.mrl-link-btn').click();
    await downloadPromise;

    await expect(first).not.toHaveClass(/selected/);
  });

  test('click does not navigate the catalog page away', async ({ page }) => {
    const startUrl = page.url();
    const first = page.locator('.media-item').first();
    await first.hover();

    const downloadPromise = page.waitForEvent('download');
    await first.locator('.mrl-link-btn').click();
    await downloadPromise;

    expect(page.url()).toBe(startUrl);
    // Media grid still populated — no full reload happened
    await expect(page.locator('.media-item').first()).toBeVisible();
  });

  test('keyboard focus reveals the button (a11y)', async ({ page }) => {
    const first = page.locator('.media-item').first();
    const btn = first.locator('.mrl-link-btn');

    // Focus the link via JS (Tab order from search input is long; focus directly)
    await btn.focus();
    // :focus-within on .media-item should bring opacity to 1
    await expect(first.locator('.media-actions')).toHaveCSS('opacity', '1');
  });

  test('renders for multiple file types', async ({ page }) => {
    const items = page.locator('.media-item');
    const count = Math.min(await items.count(), 5);
    for (let i = 0; i < count; i++) {
      const item = items.nth(i);
      await item.hover();
      const btn = item.locator('.mrl-link-btn');
      await expect(btn).toBeVisible();
      const href = await btn.getAttribute('href');
      expect(href).toMatch(/^\/api\/media\/\d+\/download\.m3u$/);
    }
  });
});
