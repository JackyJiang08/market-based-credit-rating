/** Records docs/figures/terminal_demo.webm — the README demo.
 *  Run against the built static export:  node scripts/record_demo.mjs
 *
 *  One narrative, scripted pacing (1.5–2s dwells, ~25s total):
 *    landing stat cards → ⌘K, type ORCL → company view, hold on the
 *    interval-attached letter → µ–CCM plane, hold on the ORCL cloud.
 *  2× device pixels at 1280×800 logical so text stays crisp. NEVER a GIF. */
import { chromium } from "@playwright/test";
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PORT = 4182;
const OUT = path.resolve(path.dirname(fileURLToPath(import.meta.url)),
  "../../../docs/figures/terminal_demo.webm");

const server = spawn("npx", ["serve", "out", "-l", String(PORT), "-n"], { stdio: "ignore" });
await new Promise((r) => setTimeout(r, 2500));

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  deviceScaleFactor: 2,
  recordVideo: { dir: "/tmp/demo-video", size: { width: 2560, height: 1600 } },
});
const page = await ctx.newPage();
const dwell = (ms) => page.waitForTimeout(ms);

// 1 — landing: hero + the four stat cards (hold long enough to read one)
await page.goto(`http://localhost:${PORT}/`, { waitUntil: "networkidle" });
await dwell(2000);
await page.mouse.move(640, 430); // over the stat cards
await dwell(1800);

// 2 — command bar: ⌘K, type ORCL at a human pace, enter
await page.keyboard.press("Meta+k");
await dwell(900);
await page.keyboard.type("ORCL", { delay: 260 });
await dwell(1200);
await page.keyboard.press("Enter");

// 3 — company view: hold on the interval-attached letter
await page.waitForURL(/company\/ORCL/);
await page.getByTestId("letter-with-interval").first().waitFor();
await dwell(2000);
const letter = page.getByTestId("letter-with-interval").first();
await letter.hover();
await dwell(2000);
await page.mouse.wheel(0, 420); // drift down to the measures table
await dwell(1800);

// 4 — the µ–CCM plane with the ORCL bootstrap cloud
await page.goto(`http://localhost:${PORT}/plane/?focus=ORCL`, { waitUntil: "networkidle" });
await page.getByText(/replicate points/).waitFor();
await dwell(2200);
await page.mouse.move(760, 420); // rest on the cloud
await dwell(2400);

const video = page.video();
await ctx.close();
const tmp = await video.path();
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.copyFileSync(tmp, OUT);
await browser.close();
server.kill();
console.log(`demo -> ${OUT} (${(fs.statSync(OUT).size / 1024).toFixed(0)} KB)`);
