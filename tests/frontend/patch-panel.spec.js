const { test, expect } = require("./support/test");
const {
  expectNoHorizontalOverflow,
  openView,
  visibleBoxes,
} = require("./support/site");
const visualContract = require("../../design/frontend/visual-contract.json");

const routes = visualContract.acceptance.routes;
const viewports = visualContract.acceptance.viewports.map((value) => {
  const [width, height] = value.split("x").map(Number);
  return { width, height, label: value };
});

test("Patch Panel token world is active on every route", async ({ page }) => {
  for (const view of routes) {
    await openView(page, view, "en");
    await expect(page.locator("body")).toHaveAttribute(
      "data-design-system",
      "patch-panel",
    );
    const tokens = await page.evaluate(() => {
      const root = getComputedStyle(document.documentElement);
      const body = getComputedStyle(document.body);
      return {
        page: root.getPropertyValue("--surface-page").trim(),
        panel: root.getPropertyValue("--surface-panel").trim(),
        module: root.getPropertyValue("--surface-module").trim(),
        signal: root.getPropertyValue("--signal").trim(),
        bodyBackgroundImage: body.backgroundImage,
      };
    });
    expect(tokens.page).not.toBe("");
    expect(tokens.panel).not.toBe("");
    expect(tokens.module).not.toBe("");
    expect(tokens.signal).not.toBe("");
    expect(new Set([tokens.page, tokens.panel, tokens.module]).size).toBe(3);
    expect(tokens.bodyBackgroundImage).toBe("none");
  }
});

for (const viewport of viewports) {
  test(`all routes reflow at ${viewport.label}`, async ({ page }) => {
    await page.setViewportSize({
      width: viewport.width,
      height: viewport.height,
    });
    for (const view of routes) {
      await openView(page, view, "ru");
      await expectNoHorizontalOverflow(page);
    }
  });
}

test("primary Patch Panel controls meet the 44px target", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  for (const view of ["concept", "atlas"]) {
    await openView(page, view, "en");
    const boxes = await visibleBoxes(
      page.locator(
        ".site-header a, .site-header button, .primary-cta, .inverse-cta, "
          + ".graph-node, .atlas-back, [data-atlas-inspector-close]",
      ),
    );
    const minimum = visualContract.acceptance.accessibility.minimum_target_css_px;
    const undersized = boxes.filter(
      (box) => box.width < minimum || box.height < minimum,
    );
    expect(undersized, `${view} has undersized primary controls`).toEqual([]);
  }
});

test("long-form readers keep a readable line length", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name.includes("mobile"), "desktop reading measure");
  await page.setViewportSize({ width: 1440, height: 900 });
  for (const view of ["theory", "quickstart"]) {
    await openView(page, view, "en");
    const measure = await page.locator(".prose p").first().evaluate((element) => {
      const style = getComputedStyle(element);
      const probe = document.createElement("span");
      probe.textContent = "0";
      probe.style.cssText = "position:absolute;visibility:hidden;font:inherit";
      element.append(probe);
      const character = probe.getBoundingClientRect().width;
      probe.remove();
      return element.getBoundingClientRect().width / character;
    });
    expect(measure).toBeGreaterThanOrEqual(
      visualContract.acceptance.layout.reading_measure_min_ch,
    );
    expect(measure).toBeLessThanOrEqual(
      visualContract.acceptance.layout.reading_measure_max_ch,
    );
  }
});

test("navigation stacks at the accepted breakpoint", async ({ page }) => {
  const breakpoint = visualContract.acceptance.layout.stack_breakpoint_css_px;
  await page.setViewportSize({ width: breakpoint, height: 900 });
  await openView(page, "concept", "en");
  await expect(page.locator(".menu-switch")).toBeVisible();

  await page.setViewportSize({ width: breakpoint + 1, height: 900 });
  await expect(page.locator(".menu-switch")).toBeHidden();
});
