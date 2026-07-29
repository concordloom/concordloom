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

test("Atlas columns and mechanical node assemblies remain separate", async ({ page }, testInfo) => {
  await openView(page, "atlas", "ru");
  if (testInfo.project.name.includes("desktop")) {
    await expectNoPairwiseOverlap(
      page.locator(".atlas-history, .atlas-stage, .atlas-inspector"),
      2,
    );
  }
  await expectContained(page.locator(".node-assembly"), page.locator(".atlas-stage"));
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
    const context = rect(".context-ring");
    const inspector = document.querySelector(".atlas-inspector");
    const path = rect(".atlas-history");
    return {
      chromeBottom: graph.top,
      documentHeight: document.documentElement.scrollHeight,
      graphRatio: graph.width / innerWidth,
      inspectorRatio: inspector.getBoundingClientRect().width / innerWidth,
      inspectorOverflow: inspector.scrollWidth - inspector.clientWidth,
      contextRatio: context.height / rect(".atlas-graph").height,
      pathRatio: path.width / innerWidth,
      pathWidth: path.width,
      constellationCount:
        Number(document.querySelectorAll(".context-ring").length > 0)
        + Number(document.querySelectorAll(".graph-ring").length > 0),
      nodeCount: document.querySelectorAll(".node-assembly").length,
      bridge: Boolean(document.querySelector(".level-thread")),
      inspectorDial: Boolean(document.querySelector(".inspector-dial img")),
    };
  });
  expect(geometry.chromeBottom / 900).toBeLessThanOrEqual(0.14);
  expect(geometry.documentHeight).toBeLessThanOrEqual(902);
  expect(geometry.graphRatio).toBeGreaterThanOrEqual(0.72);
  expect(geometry.inspectorRatio).toBeGreaterThanOrEqual(0.18);
  expect(geometry.inspectorRatio).toBeLessThanOrEqual(0.22);
  expect(geometry.inspectorOverflow).toBeLessThanOrEqual(1);
  expect(geometry.contextRatio).toBeGreaterThanOrEqual(0.32);
  expect(geometry.pathRatio).toBeLessThanOrEqual(0.1);
  expect(geometry.pathWidth).toBeLessThanOrEqual(160);
  expect(geometry.constellationCount).toBe(2);
  expect(geometry.nodeCount).toBeGreaterThanOrEqual(14);
  expect(geometry.bridge).toBe(true);
  expect(geometry.inspectorDial).toBe(true);
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

test("mobile graph glyphs meet the readable-size contract", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openView(page, "atlas", "ru", "system-evolution");
  const heights = await page.locator(".node-glyph").evaluateAll((glyphs) =>
    glyphs.map((glyph) => glyph.getBoundingClientRect().height),
  );
  expect(Math.min(...heights)).toBeGreaterThanOrEqual(12);
});
