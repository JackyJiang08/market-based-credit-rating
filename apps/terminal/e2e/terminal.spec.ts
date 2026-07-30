/** E2E over the built static export: landing IA, command bar, company view,
 *  charts, sensitivity, and an axe accessibility pass on the key pages. */
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("landing: hero, stat cards, AAA callout, top strips — not a table dump", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /honest uncertainty/i }),
  ).toBeVisible();
  // four stat cards, each a link to evidence
  const stats = page.getByRole("region", { name: /headline results/i });
  await expect(stats.getByText("ρ = 0.79")).toBeVisible();
  await expect(stats.getByText("×4,073")).toBeVisible();
  await expect(stats.getByText("τ = 0.956")).toBeVisible();
  await expect(stats.getByText("+5 notches")).toBeVisible();
  // the AAA question is answered before it is asked
  await expect(page.getByText(/why does every big name show aaa/i)).toBeVisible();
  // top strips link into company pages; the full table lives on /universe
  await expect(page.getByText(/safest 10 by riskscore/i)).toBeVisible();
  await page.getByRole("link", { name: /full universe/i }).click();
  await expect(page).toHaveURL(/universe/);
});

test("universe: rated names first, no-estimate group at the bottom", async ({ page }) => {
  await page.goto("/universe/");
  // first data row is rank 1, not an em-dash row
  const firstRank = page.locator("tbody tr").first().locator("td").first();
  await expect(firstRank).toHaveText("1");
  // the subdued divider explains the names without estimates
  await expect(
    page.getByRole("link", { name: /names without estimates — why\?/i }),
  ).toBeVisible();
  // enums are humanized — no SCREAMING_SNAKE in the visible table
  await expect(page.locator("tbody").getByText("SCALE_RESOLVED")).toHaveCount(0);
});

test("command bar: / → type → enter lands on the company view", async ({ page }) => {
  await page.goto("/");
  // wait for hydration: the search button renders client-side
  await page.getByRole("button", { name: /search companies/i }).first().waitFor();
  await page.keyboard.press("/");
  await page.getByPlaceholder(/ticker or company/i).fill("oracle");
  await page.getByRole("option", { name: /ORCL/ }).first().getByRole("button").click();
  await expect(page).toHaveURL(/company\/ORCL/);
  await expect(page.getByRole("heading", { name: /Oracle/ })).toBeVisible();
});

test("company view: interval-attached letter, humanized flags, basis badge", async ({
  page,
}) => {
  await page.goto("/company/ORCL/");
  await expect(page.getByTestId("letter-with-interval").first()).toHaveText("BB (BBB-..BB-)");
  // flags are humanized chips; the machine constant lives in the tooltip, not the chip
  await expect(page.getByText("Weak drift").first()).toBeVisible();
  await expect(page.getByText("WEAKLY_IDENTIFIED")).toHaveCount(0);
  // the basis is an icon-badge with a full aria-label
  await expect(
    page.getByLabel(/derived conversion — basis/i).first(),
  ).toBeVisible();
});

test("charts render: plane with cloud, bridge, ladder", async ({ page }) => {
  await page.goto("/plane/?focus=ORCL");
  await expect(page.locator("svg[aria-label*='iso-rating']")).toBeVisible();
  await expect(page.getByText(/250 replicate points/)).toBeVisible();

  await page.goto("/company/ORCL/?panel=bridge");
  await expect(page.locator("svg[aria-label*='rating bridge']")).toBeVisible();
  await page.goto("/company/ORCL/?panel=ladder");
  await expect(page.locator("svg[aria-label*='interval width']")).toBeVisible();
});

test("plane: base SVG is server-rendered (visible without JS)", async ({ browser }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false });
  const page = await ctx.newPage();
  await page.goto("/plane/");
  await expect(page.locator("svg[aria-label*='iso-rating']")).toBeVisible();
  await ctx.close();
});

test("universe filters are URL state", async ({ page }) => {
  await page.goto("/universe/?sector=Energy");
  await expect(page.getByText(/10 names/)).toBeVisible();
  await expect(page.getByText("CVX").first()).toBeVisible();
});

test("sensitivity: drift slider does NOT move RiskScore; w does", async ({ page }) => {
  await page.goto("/sensitivity/");
  const rs = page.getByTestId("out-riskscore");
  const before = await rs.textContent();
  await page.locator("#eta").fill("0.4");
  await expect(rs).toHaveText(before!); // the whole lesson
  await expect(page.getByText(/does not enter/i)).toBeVisible();
  await page.locator("#w").fill("1");
  await expect(rs).not.toHaveText(before!);
});

test("convention toggle: visible only where both conventions exist", async ({ page }) => {
  await page.goto("/company/ORCL/");
  const panel = page.getByTestId("convention-panel");
  await expect(panel).toBeVisible();
  // documented is the default and says so
  await expect(panel.getByText(/run of record/i).first()).toBeVisible();
  // flip to the reference convention: labeled values + the abs-drift chip
  await panel.getByTestId("convention-reference").click();
  await expect(panel.getByText(/reference convention/i).first()).toBeVisible();
  await expect(page.getByTestId("abs-drift-chip")).toBeVisible();
  await expect(panel.getByText("Abs drift in µ")).toBeVisible();
  // a name outside the eight-name reference set has no toggle
  await page.goto("/company/AAPL/");
  await expect(page.getByTestId("convention-panel")).toHaveCount(0);
});

for (const path of [
  "/",
  "/universe/",
  "/validation/",
  "/company/ORCL/",
  "/sensitivity/",
  "/about/",
]) {
  test(`axe: ${path} has no serious/critical violations`, async ({ page }) => {
    await page.goto(path);
    await page.waitForTimeout(800);
    const results = await new AxeBuilder({ page }).analyze();
    const bad = results.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    );
    expect(bad, JSON.stringify(bad.map((b) => b.id))).toEqual([]);
  });
}
