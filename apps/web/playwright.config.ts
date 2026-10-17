import { defineConfig, devices } from "@playwright/test";
import * as path from "path";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL || "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: "uv run python ../../scripts/run_e2e_server.py",
      url: "http://127.0.0.1:8000/docs",
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
    {
      command: "npm run start",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
    },
  ],
});
