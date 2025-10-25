import { FullConfig } from '@playwright/test';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Running global teardown...');
  
  // Add any cleanup logic here if needed
  // For example, clearing test data, stopping services, etc.
  
  console.log('✅ Global teardown complete');
}

export default globalTeardown;
