const { test, expect } = require("./support/test");
const {
  expectNoHorizontalOverflow,
  openView,
  visibleBoxes,
} = require("./support/site");

const routes = ["concept", "theory", "quickstart", "atlas", "docs"];
const viewports = [
  { width: 360, height: 800 },
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1024, height: 768 },
  { width: 1440, height: 900 },
];

test("Signal Canvas is the single design system on every route", async ({ page }) => {
  for (const view of routes) {
    await openView(page, view, "en");
    await expect(page.locator("html")).toHaveAttribute(
      "data-design-system",
      "signal-canvas",
    );
    await expect(page.locator("body")).toHaveAttribute(
      "data-design-system",
      "signal-canvas",
    );
    const tokens = await page.evaluate(() => {
      const root = getComputedStyle(document.documentElement);
      const body = getComputedStyle(document.body);
      return {
        page: root.getPropertyValue("--surface-page").trim(),
        panel: root.getPropertyValue("--surface-panel").trim(),
        void: root.getPropertyValue("--surface-void").trim(),
        signal: root.getPropertyValue("--signal").trim(),
        info: root.getPropertyValue("--info").trim(),
        bodyBackgroundImage: body.backgroundImage,
      };
    });
    expect(tokens.page).not.toBe("");
    expect(tokens.panel).not.toBe("");
    expect(tokens.void).not.toBe("");
    expect(tokens.signal).not.toBe("");
    expect(tokens.info).not.toBe("");
    expect(new Set([tokens.page, tokens.panel, tokens.void]).size).toBe(3);
    expect(tokens.bodyBackgroundImage).toBe("none");
  }
});

for (const viewport of viewports) {
  test(`all routes reflow at ${viewport.width} × ${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    for (const language of ["en", "ru"]) {
      for (const view of routes) {
        await openView(page, view, language);
        await expectNoHorizontalOverflow(page);
      }
    }
  });
}

test("primary controls remain touchable at both phone widths", async ({ page }) => {
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    for (const view of ["concept", "atlas"]) {
      await openView(page, view, "en");
      const boxes = await visibleBoxes(
        page.locator(
          ".site-header a, .site-header button, .primary-cta, .secondary-cta, "
            + ".graph-node, .atlas-up, [data-atlas-inspector-close]",
        ),
      );
      const undersized = boxes.filter(
        (box) => box.width < 44 || box.height < 44,
      );
      expect(
        undersized,
        `${view} has controls smaller than 44 × 44 CSS pixels at ${width}px`,
      ).toEqual([]);
    }
  }
});

test("long-form readers keep a 65–75 character measure", async ({ page }) => {
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
    expect(measure).toBeGreaterThanOrEqual(65);
    expect(measure).toBeLessThanOrEqual(75);
  }
});

test("navigation stacks at the product breakpoint", async ({ page }) => {
  await page.setViewportSize({ width: 820, height: 900 });
  await openView(page, "concept", "en");
  await expect(page.locator(".menu-switch")).toBeVisible();

  await page.setViewportSize({ width: 821, height: 900 });
  await expect(page.locator(".menu-switch")).toBeHidden();
});
