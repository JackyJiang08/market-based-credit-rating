import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  use: { baseURL: "http://localhost:4180", viewport: { width: 1280, height: 800 } },
  webServer: {
    command: "npx serve out -l 4180 -n",
    port: 4180,
    reuseExistingServer: true,
  },
  reporter: [["list"]],
});
