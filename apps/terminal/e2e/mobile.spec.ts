/** Mobile pass (390×844): the table collapses to cards, the command bar is
 *  reachable via a visible button, and axe stays clean. */
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("universe collapses to cards on a phone", async ({ page }) => {
  await page.goto("/universe/");
  // the desktop table is hidden; the card list is what renders
  await expect(page.locator("table").first()).toBeHidden();
  const cards = page.getByRole("list", { name: /universe \(cards\)/i });
  await expect(cards).toBeVisible();
  const first = cards.getByRole("listitem").first();
  // a card carries rank, ticker, RiskScore, and the interval-attached letter
  await expect(first.getByText(/#1\b/)).toBeVisible();
  await expect(first.getByTestId("letter-with-interval")).toBeVisible();
  await first.getByRole("button").click();
  await expect(page).toHaveURL(/company\//);
});

test("command bar is reachable via a visible button on mobile", async ({ page }) => {
  await page.goto("/");
  const trigger = page.getByRole("button", { name: /search companies/i }).first();
  await expect(trigger).toBeVisible();
  await trigger.click();
  await page.getByPlaceholder(/ticker or company/i).fill("ORCL");
  await page.getByRole("option", { name: /ORCL/ }).first().getByRole("button").click();
  await expect(page).toHaveURL(/company\/ORCL/);
});

test("charts scroll horizontally instead of overflowing the page", async ({ page }) => {
  await page.goto("/plane/");
  await expect(page.locator("svg[aria-label*='iso-rating']")).toBeVisible();
  // the page body itself must not scroll horizontally
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
});

for (const path of ["/", "/universe/"]) {
  test(`axe (mobile): ${path} has no serious/critical violations`, async ({ page }) => {
    await page.goto(path);
    await page.waitForTimeout(800);
    const results = await new AxeBuilder({ page }).analyze();
    const bad = results.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    );
    expect(bad, JSON.stringify(bad.map((b) => b.id))).toEqual([]);
  });
}
