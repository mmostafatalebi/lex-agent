import { defineConfig, devices } from "@playwright/test";

// The app runs against Playwright route mocks (not the in-memory mock), so the
// dev server starts with the real-fetch path enabled and a placeholder API URL
// that route interception matches.
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev -- --port 3000",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      NEXT_PUBLIC_USE_MOCK: "false",
      NEXT_PUBLIC_API_URL: "http://localhost:9000",
      NEXT_PUBLIC_REQUIRE_API_KEY: "false",
    },
  },
});
