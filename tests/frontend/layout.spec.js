const { test, expect } = require("./support/test");
const {
  expectContained,
  expectNoHorizontalOverflow,
  expectNoPairwiseOverlap,
  openView,
  visibleBoxes,
} = require("./support/site");

for (const language of ["en", "ru"]) {
  for (const view of ["concept", "quickstart", "atlas", "docs"]) {
    test(`${language} ${view} has no horizontal overflow`, async ({ page }) => {
      await openView(page, view, language);
      await expectNoHorizontalOverflow(page);
    });
  }
}

test("header regions never overlap", async ({ page }, testInfo) => {
  await openView(page, "concept", "ru");
  const mobile = testInfo.project.name.includes("mobile");
  const selector = mobile
    ? ".site-header > .brand, .site-header > .menu-switch, .site-header > .header-actions"
    : ".site-header > .brand, .site-header > .view-tabs, .site-header > .system-rail, .site-header > .header-actions";
  await expectNoPairwiseOverlap(page.locator(selector), 2);
});

test("hero headline, explanation and action do not overlap", async ({ page }) => {
  await openView(page, "concept", "ru");
  await expectNoPairwiseOverlap(
    page.locator(".hero-copy h1, .hero-bottom p, .hero-bottom .primary-cta"),
    2,
  );
});

test("Atlas columns and visible labels remain separate", async ({ page }, testInfo) => {
  await openView(page, "atlas", "ru");
  if (testInfo.project.name.includes("desktop")) {
    await expectNoPairwiseOverlap(
      page.locator(".atlas-history, .atlas-stage, .atlas-inspector"),
      2,
    );
  }
  await expectNoPairwiseOverlap(page.locator(".node-label"), 4);
  await expectContained(page.locator(".node-label"), page.locator(".atlas-stage"));
});

test("primary touch controls meet the minimum target size", async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes("mobile"), "mobile contract");
  await openView(page, "atlas", "en");
  const controls = page.locator(
    ".menu-switch, .language-switch, .graph-node:not(.is-current)",
  );
  const boxes = await visibleBoxes(controls);
  const undersized = boxes.filter((box) => box.width < 44 || box.height < 44);
  expect(undersized, "mobile controls must be at least 44 × 44 CSS pixels").toEqual([]);
});

test("accepted desktop Atlas geometry is enforced at 1440 × 900", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openView(page, "atlas", "ru", "system-evolution");
  const geometry = await page.evaluate(() => {
    const rect = (selector) => document.querySelector(selector).getBoundingClientRect();
    const graph = rect(".atlas-stage");
    const parent = rect(".parent-constellation");
    const inspector = document.querySelector(".atlas-inspector");
    return {
      chromeBottom: graph.top,
      documentHeight: document.documentElement.scrollHeight,
      graphRatio: graph.width / innerWidth,
      inspectorOverflow: inspector.scrollWidth - inspector.clientWidth,
      parentRatio: parent.height / rect(".atlas-graph").height,
    };
  });
  expect(geometry.chromeBottom / 900).toBeLessThanOrEqual(0.14);
  expect(geometry.documentHeight).toBeLessThanOrEqual(902);
  expect(geometry.graphRatio).toBeGreaterThanOrEqual(0.72);
  expect(geometry.inspectorOverflow).toBeLessThanOrEqual(1);
  expect(geometry.parentRatio).toBeGreaterThanOrEqual(0.32);
  await expect(page.locator(".atlas-back")).toBeVisible();
});

test("desktop primary action is visible without scrolling", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openView(page, "concept", "ru");
  const action = await page.locator(".primary-cta").boundingBox();
  expect(action).not.toBeNull();
  expect(action.y + action.height).toBeLessThanOrEqual(900);
});

test("Atlas remains graph-first at the 200 percent reflow equivalent", async ({ page }) => {
  await page.setViewportSize({ width: 720, height: 450 });
  await openView(page, "atlas", "ru", "system-evolution");
  const visibleRatio = await page.locator(".atlas-stage").evaluate((element) => {
    const box = element.getBoundingClientRect();
    return (Math.min(innerHeight, box.bottom) - Math.max(0, box.top)) / innerHeight;
  });
  expect(visibleRatio).toBeGreaterThanOrEqual(0.55);
});

test("mobile graph labels meet the readable-size contract", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openView(page, "atlas", "ru", "system-evolution");
  const heights = await page.locator(".node-label").evaluateAll((labels) =>
    labels.map((label) => label.getBoundingClientRect().height),
  );
  expect(Math.min(...heights)).toBeGreaterThanOrEqual(12);
});
