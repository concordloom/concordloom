const { test, expect } = require("./support/test");
const {
  expectContained,
  expectNoHorizontalOverflow,
  expectNoPairwiseOverlap,
  openView,
  visibleBoxes,
} = require("./support/site");

for (const language of ["en", "ru"]) {
  for (const view of ["concept", "theory", "quickstart", "atlas", "docs"]) {
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

test("accepted desktop Atlas remains a graph-first Patch Panel", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openView(page, "atlas", "ru", "system-evolution");
  const geometry = await page.evaluate(() => {
    const rect = (selector) => document.querySelector(selector).getBoundingClientRect();
    const graph = rect(".atlas-stage");
    return {
      graphHeightRatio: graph.height / innerHeight,
      graphRatio: graph.width / innerWidth,
      stageBackgroundImage: getComputedStyle(document.querySelector(".atlas-stage")).backgroundImage,
      currentCount: document.querySelectorAll(".graph-node.is-current").length,
      nodeCount: document.querySelectorAll(".node-assembly").length,
    };
  });
  expect(geometry.graphHeightRatio).toBeGreaterThanOrEqual(0.6);
  expect(geometry.graphRatio).toBeGreaterThanOrEqual(0.62);
  expect(geometry.stageBackgroundImage).toBe("none");
  expect(geometry.currentCount).toBe(1);
  await expect(page.locator(".context-ring, .graph-ring")).toHaveCount(0);
  expect(geometry.nodeCount).toBeGreaterThanOrEqual(5);
  await page.locator(".graph-node.is-current").click();
  await expect(page.locator("[data-atlas-inspector]")).toBeVisible();
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

test("mobile Atlas labels retain a readable rendered scale", async ({ page }) => {
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    await openView(page, "atlas", "ru", "system-evolution");
    const labels = await page.locator(".graph-node:not(.is-current) .node-label").evaluateAll(
      (elements) => elements.flatMap((element) => {
        const matrix = element.getScreenCTM();
        const scale = matrix ? Math.hypot(matrix.a, matrix.b) : 0;
        const fontSize = Number.parseFloat(getComputedStyle(element).fontSize);
        return [...element.querySelectorAll("tspan")].map((line) => ({
          renderedFontSize: fontSize * scale,
          renderedHeight: line.getBoundingClientRect().height,
          text: line.textContent,
        }));
      }),
    );
    expect(labels.length).toBeGreaterThan(0);
    expect(
      labels.filter(({ renderedFontSize, renderedHeight }) =>
        renderedFontSize < 12 || renderedHeight < 12),
      `${width}px Atlas labels are visually undersized`,
    ).toEqual([]);
    await expectNoHorizontalOverflow(page);
  }
});
