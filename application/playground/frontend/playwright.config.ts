import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:8766",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    ...devices["Desktop Chrome"],
    viewport: { width: 1440, height: 1000 },
    reducedMotion: "reduce",
  },
  webServer: {
    command:
      "PYTHONPATH=../../..:../../../environment/runtime:../../../packages/playground/src:.. ../../../.venv/bin/python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8766 --workers 1",
    url: "http://127.0.0.1:8766/api/health",
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
  },
});
