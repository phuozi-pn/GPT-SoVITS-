import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(fileURLToPath(new URL("../..", import.meta.url)));
const apiStarter =
  process.platform === "win32"
    ? `python "${path.join(repoRoot, "scripts/e2e_start_api.py")}"`
    : `bash "${path.join(repoRoot, "scripts/e2e_start_api.sh")}"`;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 60_000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
  },
  webServer: [
    {
      command: apiStarter,
      url: "http://127.0.0.1:8001/health",
      // 始终重启 E2E API，确保 lifespan 迁移（含 020 种子）已应用
      reuseExistingServer: false,
      timeout: 180_000,
      cwd: repoRoot,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        VITE_API_BASE: "http://127.0.0.1:8001",
      },
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
