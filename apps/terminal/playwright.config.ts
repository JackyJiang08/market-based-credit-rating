import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  use: { baseURL: "http://localhost:4180" },
  projects: [
    {
      name: "desktop",
      use: { viewport: { width: 1280, height: 800 } },
      testIgnore: /mobile\.spec\.ts/,
    },
    {
      name: "mobile",
      use: {
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
      testMatch: /mobile\.spec\.ts/,
    },
  ],
  webServer: {
    command: "npx serve out -l 4180 -n",
    port: 4180,
    reuseExistingServer: true,
  },
  reporter: [["list"]],
});
