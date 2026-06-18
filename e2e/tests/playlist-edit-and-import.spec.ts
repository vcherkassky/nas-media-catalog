import { test, expect, Page, APIRequestContext } from '@playwright/test';

const API = 'http://127.0.0.1:8000';

async function createPlaylist(req: APIRequestContext, name: string, count = 2) {
  const media = await req.get(`${API}/media?limit=${count}`);
  const files = await media.json();
  const file_paths = files.slice(0, count).map((f: any) => f.path);
  const res = await req.post(`${API}/playlists`, {
    data: { name, description: '', file_paths },
  });
  expect(res.ok()).toBeTruthy();
  return await res.json();
}

async function deletePlaylistIfExists(req: APIRequestContext, id: number) {
  await req.delete(`${API}/playlists/${id}`).catch(() => {});
}

async function deletePlaylistByName(req: APIRequestContext, name: string) {
  const res = await req.get(`${API}/playlists`);
  const list = await res.json();
  for (const p of list) {
    if (p.name === name) await deletePlaylistIfExists(req, p.id);
  }
}

async function goHome(page: Page) {
  await page.goto('/');
  await expect(page.locator('#connection-status')).toContainText('Connected', { timeout: 10000 });
  await page.waitForSelector('.media-item', { timeout: 10000 });
}

test.describe.configure({ mode: 'serial' });

test.describe('Playlist edit mode + M3U round-trip import', () => {
  let createdNames: string[] = [];

  test.afterEach(async ({ request }) => {
    for (const name of createdNames) {
      await deletePlaylistByName(request, name);
    }
    createdNames = [];
  });

  test('enter edit mode → toggle item → save persists change', async ({ page, request }) => {
    const original = await createPlaylist(request, 'edit-test-save', 2);
    createdNames.push(original.name);
    await goHome(page);

    // Edit via sidebar button
    await page.click(`.playlist-item[data-playlist-id="${original.id}"] .edit-playlist-sidebar-btn`);

    // Banner is visible and names the playlist
    const banner = page.locator('#edit-mode-banner');
    await expect(banner).toBeVisible();
    await expect(banner.locator('#edit-mode-banner-name')).toHaveText(original.name);

    // The 2 original items are already selected — find an unselected item and toggle it on
    const unselected = page.locator('.media-item:not(.selected)').first();
    await unselected.click();

    // Save via the panel
    await page.click('#edit-save-btn');

    // Banner gone, toast appears
    await expect(banner).toBeHidden();

    // Verify via API that file_paths grew by 1
    const fresh = await request.get(`${API}/playlists/${original.id}`).then(r => r.json());
    expect(fresh.file_paths.length).toBe(original.file_paths.length + 1);
  });

  test('cancel after toggling does not change the playlist', async ({ page, request }) => {
    const original = await createPlaylist(request, 'edit-test-cancel', 2);
    createdNames.push(original.name);
    await goHome(page);

    await page.click(`.playlist-item[data-playlist-id="${original.id}"] .edit-playlist-sidebar-btn`);

    const unselected = page.locator('.media-item:not(.selected)').first();
    await unselected.click();

    // Cancel — accept the confirm dialog about unsaved changes
    page.once('dialog', d => d.accept());
    await page.click('#edit-cancel-btn');

    await expect(page.locator('#edit-mode-banner')).toBeHidden();

    const fresh = await request.get(`${API}/playlists/${original.id}`).then(r => r.json());
    expect(fresh.file_paths.length).toBe(original.file_paths.length);
  });

  test('save as new creates a separate playlist, original untouched', async ({ page, request }) => {
    const original = await createPlaylist(request, 'edit-test-savenew', 2);
    createdNames.push(original.name);
    createdNames.push(`${original.name} (copy)`);
    await goHome(page);

    await page.click(`.playlist-item[data-playlist-id="${original.id}"] .edit-playlist-sidebar-btn`);

    const unselected = page.locator('.media-item:not(.selected)').first();
    await unselected.click();

    await page.click('#edit-save-as-new-btn');
    // Modal opens with prefilled name; click Create
    await expect(page.locator('#playlist-modal')).toHaveClass(/show/);
    await page.click('#create-playlist-btn');

    // Original unchanged
    const fresh = await request.get(`${API}/playlists/${original.id}`).then(r => r.json());
    expect(fresh.file_paths.length).toBe(original.file_paths.length);

    // New playlist exists
    const all = await request.get(`${API}/playlists`).then(r => r.json());
    const copy = all.find((p: any) => p.name === `${original.name} (copy)`);
    expect(copy).toBeTruthy();
    expect(copy.file_paths.length).toBe(original.file_paths.length + 1);
  });

  test('rename + description persist via PUT', async ({ page, request }) => {
    const original = await createPlaylist(request, 'edit-test-rename', 2);
    const newName = 'edit-test-renamed';
    createdNames.push(original.name);
    createdNames.push(newName);
    await goHome(page);

    await page.click(`.playlist-item[data-playlist-id="${original.id}"] .edit-playlist-sidebar-btn`);

    await page.fill('#edit-playlist-name', newName);
    await page.fill('#edit-playlist-description', 'a new description');
    await page.click('#edit-save-btn');

    await expect(page.locator('#edit-mode-banner')).toBeHidden();

    const fresh = await request.get(`${API}/playlists/${original.id}`).then(r => r.json());
    expect(fresh.name).toBe(newName);
    expect(fresh.description).toBe('a new description');
  });

  test('upload .vlc.m3u round-trips back into a playlist', async ({ page, request }) => {
    const original = await createPlaylist(request, 'edit-test-rt-src', 3);
    createdNames.push(original.name);
    // The imported playlist will have the same name (round-trip), so we need to
    // delete the source first to avoid the unique-name collision.
    const buf = await request.get(`${API}/playlists/${original.id}/download`).then(r => r.body());
    await deletePlaylistIfExists(request, original.id);
    createdNames.push(original.name); // also clean up the round-tripped one

    await goHome(page);

    // Trigger the hidden file input directly
    const input = page.locator('#upload-playlist-input');
    await input.setInputFiles({
      name: `${original.name}.vlc.m3u`,
      mimeType: 'audio/x-mpegurl',
      buffer: buf,
    });

    // After import the UI enters edit mode for the new playlist
    await expect(page.locator('#edit-mode-banner')).toBeVisible({ timeout: 5000 });

    // Confirm via API
    const all = await request.get(`${API}/playlists`).then(r => r.json());
    const imported = all.find((p: any) => p.name === original.name);
    expect(imported).toBeTruthy();
    expect(imported.file_paths.length).toBe(original.file_paths.length);
    expect(new Set(imported.file_paths)).toEqual(new Set(original.file_paths));
  });

  test('upload with one unmatched URL still creates playlist with matched items', async ({ page, request }) => {
    // Build a synthetic .m3u: 2 real URLs + 1 fake
    const media = await request.get(`${API}/media?limit=2`).then(r => r.json());
    const realUrls = media.slice(0, 2).map((f: any) => f.path);
    const fakeUrl = 'http://192.0.2.1/does-not-exist-in-catalog.mp4';
    const m3u = [
      '#EXTM3U',
      '#PLAYLIST:edit-test-partial',
      '#EXTINF:-1,one',
      realUrls[0],
      '#EXTINF:-1,two',
      realUrls[1],
      '#EXTINF:-1,three',
      fakeUrl,
      '',
    ].join('\n');
    createdNames.push('edit-test-partial');

    await goHome(page);

    await page.locator('#upload-playlist-input').setInputFiles({
      name: 'edit-test-partial.m3u',
      mimeType: 'audio/x-mpegurl',
      buffer: Buffer.from(m3u, 'utf-8'),
    });

    await expect(page.locator('#edit-mode-banner')).toBeVisible({ timeout: 5000 });

    const all = await request.get(`${API}/playlists`).then(r => r.json());
    const imported = all.find((p: any) => p.name === 'edit-test-partial');
    expect(imported).toBeTruthy();
    expect(imported.file_paths).toHaveLength(2);
    expect(imported.file_paths).not.toContain(fakeUrl);
  });

  test('upload of a non-M3U file shows an error toast', async ({ page }) => {
    await goHome(page);
    await page.locator('#upload-playlist-input').setInputFiles({
      name: 'not-an-m3u.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('just some text\nwith multiple lines\n'),
    });

    // We expect a toast and NO edit-mode entry
    await expect(page.locator('#toast-container')).toContainText(/Import failed/i, { timeout: 5000 });
    await expect(page.locator('#edit-mode-banner')).toBeHidden();
  });

  test('Edit button on playlist card (Playlists tab) enters edit mode', async ({ page, request }) => {
    const original = await createPlaylist(request, 'edit-test-card', 2);
    createdNames.push(original.name);
    await goHome(page);
    await page.click('.tab-btn[data-tab="playlists"]');
    await page.click(`.playlist-card[data-playlist-id="${original.id}"] .edit-playlist-btn`);
    await expect(page.locator('#edit-mode-banner')).toBeVisible();
    await expect(page.locator('#edit-mode-banner-name')).toHaveText(original.name);
  });
});
