/** E2E over the built static export: command bar, company view, charts,
 *  sensitivity, and an axe accessibility pass on the key pages. */
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("command bar: / → type → enter lands on the company view", async ({ page }) => {
  await page.goto("/");
  // wait for hydration: the search button renders client-side
  await page.getByRole("button", { name: /search companies/i }).waitFor();
  await page.keyboard.press("/");
  await page.getByPlaceholder(/ticker or company/i).fill("oracle");
  await page.getByRole("option", { name: /ORCL/ }).first().getByRole("button").click();
  await expect(page).toHaveURL(/company\/ORCL/);
  await expect(page.getByRole("heading", { name: /Oracle/ })).toBeVisible();
});

test("company view renders the interval-attached letter and flags", async ({ page }) => {
  await page.goto("/company/ORCL/");
  await expect(page.getByTestId("letter-with-interval").first()).toHaveText("BB (BBB-..BB-)");
  await expect(page.getByText("WEAKLY_IDENTIFIED").first()).toBeVisible();
  await expect(page.getByText(/derived conversion/i).first()).toBeVisible();
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

test("universe filters are URL state", async ({ page }) => {
  await page.goto("/?sector=Energy");
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

for (const path of ["/", "/company/ORCL/", "/sensitivity/", "/about/"]) {
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
