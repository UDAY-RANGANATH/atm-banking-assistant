import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E configuration (Phase 5).
 *
 * Prerequisites (started manually for the prototype):
 *   backend  - uvicorn on 127.0.0.1:8000
 *   frontend - vite dev server on 127.0.0.1:5173 (proxies /api)
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
