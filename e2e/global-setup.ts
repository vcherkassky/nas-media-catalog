import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting global setup...');
  
  // Wait for services to be ready
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  const baseURL = process.env.BASE_URL || 'http://127.0.0.1:3000';
  const apiURL = process.env.API_URL || 'http://127.0.0.1:8000';
  
  // Wait for UI to be ready
  console.log('⏳ Waiting for UI to be ready...');
  let uiReady = false;
  for (let i = 0; i < 30; i++) {
    try {
      await page.goto(baseURL, { timeout: 5000 });
      uiReady = true;
      break;
    } catch (error) {
      console.log(`UI not ready yet, attempt ${i + 1}/30`);
      await page.waitForTimeout(2000);
    }
  }
  
  if (!uiReady) {
    throw new Error('UI failed to start within timeout');
  }
  
  // Wait for API to be ready
  console.log('⏳ Waiting for API to be ready...');
  let apiReady = false;
  for (let i = 0; i < 30; i++) {
    try {
      const response = await page.request.get(`${apiURL}/health`);
      if (response.ok()) {
        apiReady = true;
        break;
      }
    } catch (error) {
      console.log(`API not ready yet, attempt ${i + 1}/30`);
      await page.waitForTimeout(2000);
    }
  }
  
  if (!apiReady) {
    throw new Error('API failed to start within timeout');
  }
  
  console.log('✅ Services are ready!');
  
  await browser.close();
}

export default globalSetup;
