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

test("language switch preserves the selected Atlas cycle", async ({ page }) => {
  await openView(page, "atlas", "en", "system-evolution");
  await expect(page.locator(".graph-node.is-current")).toHaveAttribute(
    "data-loop-id",
    "system-evolution",
  );
  await page.locator(".language-switch").click();
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await expect(page).toHaveURL(/[?&]lang=ru.*#atlas\/system-evolution$/);
  await expect(page.locator(".graph-node.is-current")).toHaveAttribute(
    "data-loop-id",
    "system-evolution",
  );
  await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
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

test("public header contains no simulated lifecycle progress", async ({ page }) => {
  for (const view of routes) {
    await openView(page, view, "en");
    await expect(page.locator(".site-header .system-rail")).toHaveCount(0);
    await expect(page.locator(".view-tabs a")).toHaveCount(routes.length);
  }
});
