const { test, expect } = require("./support/test");
const {
  expectContained,
  expectNoPairwiseOverlap,
  openView,
} = require("./support/site");

for (const language of ["en", "ru"]) {
  test(`direct Atlas entry does not steal focus in ${language}`, async ({ page }) => {
    await openView(page, "atlas", language, "system-evolution");
    await expect(page.locator(".graph-node.is-current")).not.toBeFocused();
  });

  test(`Atlas drill-down and back navigation work in ${language}`, async ({ page }) => {
    await openView(page, "atlas", language);
    const rootId = await page.locator(".graph-node.is-current").getAttribute("data-loop-id");
    const child = page.locator(".graph-node:not(.is-current)").first();
    await expect(child).toBeVisible();
    const childId = await child.getAttribute("data-loop-id");
    await child.click();
    await expect(page).toHaveURL(new RegExp(`#atlas/${childId}$`));
    await expect(page.locator(".graph-node.is-current")).toBeFocused();
    await expect(page.locator(".atlas-history li")).toHaveCount(2);
    await page.locator(".atlas-back").click();
    await expect(page).toHaveURL(new RegExp(`#atlas/${rootId}$`));
    await expect(page.locator(".graph-node.is-current")).toBeFocused();
  });

  test(`Atlas graph is keyboard-operable in ${language}`, async ({ page }) => {
    await openView(page, "atlas", language);
    const child = page.locator(".graph-node:not(.is-current)").first();
    const childId = await child.getAttribute("data-loop-id");
    await child.focus();
    await expect(child).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(new RegExp(`#atlas/${childId}$`));
    await expect(page.locator("[data-atlas-inspector]")).toContainText(
      language === "ru" ? /[А-Яа-яЁё]/ : /[A-Za-z]/,
    );
  });
}

test("Atlas labels do not collide or escape the mechanical stage", async ({ page }) => {
  await openView(page, "atlas", "ru");
  await expectNoPairwiseOverlap(page.locator(".node-label"), 4);
  await expectNoPairwiseOverlap(page.locator(".atlas-history li"), 4);
  await expectContained(
    page.locator(".node-label"),
    page.locator(".atlas-stage"),
  );
});

test("Atlas exposes selected state and a useful accessible name", async ({ page }) => {
  await openView(page, "atlas", "en");
  const current = page.locator(".graph-node.is-current");
  await expect(current).toHaveCount(1);
  await expect(current).toHaveAttribute("aria-label", /.+/);
  const child = page.locator(".graph-node:not(.is-current)").first();
  await expect(child).toHaveAttribute("aria-label", /Contained cycles|No contained cycles/);
});
