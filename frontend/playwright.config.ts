import { defineConfig, devices } from "@playwright/test";

// End-to-end tests drive the real frontend against the real backend.
// PYTHON: interpreter with the backend requirements (default: backend/.venv).
// CHROMIUM_PATH: optional browser executable (otherwise Playwright's own).
const python = process.env.PYTHON ?? "../backend/.venv/bin/python";

export default defineConfig({
  testDir: "e2e",
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://127.0.0.1:5173",
    viewport: { width: 1440, height: 900 },
    launchOptions: process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {},
  },
  webServer: [
    {
      command: `${python} -m uvicorn app.main:app --port 8000`,
      cwd: "../backend",
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: true,
    },
    {
      command: "npx vite --port 5173 --strictPort",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: true,
    },
  ],
});
