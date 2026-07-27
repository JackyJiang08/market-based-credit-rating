/** Commits the docs/figures screenshots: landing, universe, plane.
 *  Run against the built static export:  node scripts/shoot_figures.mjs
 *  (starts its own server on :4181; deviceScaleFactor 2 for crisp README use) */
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";

const PORT = 4181;
const server = spawn("npx", ["serve", "out", "-l", String(PORT), "-n"], { stdio: "ignore" });
await new Promise((r) => setTimeout(r, 2500));

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1280, height: 860 },
  deviceScaleFactor: 2,
});

const shots = [
  ["/", "../../../docs/figures/terminal_landing.png"],
  ["/universe/", "../../../docs/figures/terminal_universe.png"],
  ["/plane/?focus=ORCL", "../../../docs/figures/terminal_mu_ccm_plane.png"],
];
for (const [path, out] of shots) {
  await page.goto(`http://localhost:${PORT}${path}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: new URL(out, import.meta.url).pathname });
  console.log(`shot ${path} -> ${out}`);
}

await browser.close();
server.kill();
