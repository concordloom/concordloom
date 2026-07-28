const { test, expect } = require("./support/test");
const { openView, siteUrl } = require("./support/site");

const routes = ["concept", "theory", "quickstart", "atlas", "docs"];

for (const language of ["en", "ru"]) {
  test.describe(`${language} routes`, () => {
    for (const view of routes) {
      test(`${view} supports direct entry and reload`, async ({ page }) => {
        await openView(page, view, language);
        await page.reload();
        await expect(page.locator("html")).toHaveAttribute("lang", language);
        await expect(page.locator(`[data-view="${view}"]`)).toHaveClass(/\bis-active\b/);
        await expect(page).toHaveURL(new RegExp(`#${view}(?:$|/)`));
      });
    }
  });
}

test("English is the deterministic first-visit language", async ({ page }) => {
  await page.goto("/#concept");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator('.view-tabs [data-view-link="concept"]')).toHaveText("Concept");
});

test("language switch preserves the current route", async ({ page }) => {
  await page.goto(siteUrl("atlas", "en"));
  await expect(page.locator("[data-atlas-count]")).not.toHaveText("0");
  await page.locator(".language-switch").click();
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await expect(page).toHaveURL(/[?&]lang=ru.*#atlas/);
  await expect(page.locator("[data-view-link=atlas]")).toHaveText("Атлас");
});

test("navigation exposes one current page and preserves URL state", async ({ page }) => {
  await openView(page, "concept", "en");
  for (const view of routes) {
    const target = page.locator(`.view-tabs [data-view-link="${view}"]`);
    if (!(await target.isVisible())) {
      await page.locator(".menu-switch").click();
      await expect(target).toBeVisible();
    }
    await target.click();
    await expect(target).toHaveAttribute(
      "aria-current",
      "page",
    );
    await expect(page.locator(`[data-view="${view}"]`)).toHaveClass(/\bis-active\b/);
    await expect(page).toHaveURL(new RegExp(`#${view}(?:$|/)`));
  }
});

test("lifecycle rail is semantic and changes with site state", async ({ page }) => {
  const activeByView = [];
  for (const view of ["concept", "quickstart", "atlas", "docs"]) {
    await openView(page, view, "en");
    const active = page.locator(".system-rail li.is-active");
    await expect(active).toHaveCount(1);
    await expect(active).toHaveAttribute("aria-current", "step");
    activeByView.push((await active.innerText()).trim());
  }
  expect(
    new Set(activeByView).size,
    `lifecycle is hard-coded instead of reflecting site state: ${activeByView.join(", ")}`,
  ).toBeGreaterThan(1);
});
