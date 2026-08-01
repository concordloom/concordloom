const { test, expect } = require("./support/test");
const {
  expectContained,
  expectNoHorizontalOverflow,
  expectNoPairwiseOverlap,
  openView,
  visibleBoxes,
} = require("./support/site");

const viewports = [
  { width: 360, height: 800 },
  { width: 390, height: 844 },
  { width: 768, height: 1024 },
  { width: 1024, height: 768 },
  { width: 1440, height: 900 },
];

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
    : ".site-header > .brand, .site-header > .view-tabs, .site-header > .header-actions";
  await expectNoPairwiseOverlap(page.locator(selector), 2);
});

test("hero headline, explanation and actions do not overlap", async ({ page }) => {
  await openView(page, "concept", "ru");
  await expectNoPairwiseOverlap(
    page.locator(
      ".hero-copy h1, .hero-bottom p, .hero-bottom .primary-cta, "
        + ".hero-bottom .secondary-cta",
    ),
    2,
  );
});

test("Atlas is a full-width primary surface with no persistent side panels", async ({ page }) => {
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await openView(page, "atlas", "en", "system-evolution");
    const geometry = await page.evaluate(() => {
      const stage = document.querySelector("[data-atlas-stage]").getBoundingClientRect();
      const workbench = document.querySelector(".atlas-workbench").getBoundingClientRect();
      const header = document.querySelector(".site-header").getBoundingClientRect();
      const visibleHistory = [...document.querySelectorAll(".atlas-history")]
        .filter((element) => {
          const style = getComputedStyle(element);
          const box = element.getBoundingClientRect();
          return style.display !== "none" && style.visibility !== "hidden"
            && box.width > 0 && box.height > 0;
        }).length;
      return {
        headerHeight: header.height,
        stageBackgroundImage: getComputedStyle(
          document.querySelector("[data-atlas-stage]"),
        ).backgroundImage,
        stageWidthRatio: stage.width / innerWidth,
        visibleHistory,
        workbenchHeight: workbench.height,
        viewportHeight: innerHeight,
      };
    });
    expect(
      geometry.stageWidthRatio,
      `${viewport.width}px Atlas leaves permanent side chrome beside the graph`,
    ).toBeGreaterThanOrEqual(0.94);
    expect(geometry.visibleHistory).toBe(0);
    expect(geometry.stageBackgroundImage).not.toContain("url(");
    expect(geometry.workbenchHeight).toBeGreaterThanOrEqual(
      geometry.viewportHeight - geometry.headerHeight - 8,
    );
    await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
    await expectContained(
      page.locator(".node-assembly"),
      page.locator("[data-atlas-stage]"),
    );
    await expectNoHorizontalOverflow(page);
  }
});

test("Atlas node labels stay readable at every accepted width", async ({ page }) => {
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await openView(page, "atlas", "ru", "system-evolution");
    const minimum = viewport.width <= 390 ? 16 : 14;
    const labels = await page.locator(".graph-node .node-label").evaluateAll(
      (elements) => elements.map((element) => {
        const fontSize = Number.parseFloat(getComputedStyle(element).fontSize);
        const matrix = typeof element.getScreenCTM === "function"
          ? element.getScreenCTM()
          : null;
        const scale = matrix ? Math.hypot(matrix.a, matrix.b) : 1;
        return {
          renderedFontSize: fontSize * scale,
          renderedHeight: element.getBoundingClientRect().height,
          text: element.textContent.trim().replace(/\s+/g, " "),
        };
      }),
    );
    expect(labels.length).toBeGreaterThan(0);
    expect(
      labels.filter(({ renderedFontSize, renderedHeight }) =>
        renderedFontSize < minimum || renderedHeight < minimum),
      `${viewport.width}px Atlas labels must render at least ${minimum}px`,
    ).toEqual([]);
  }
});

test("Atlas nodes never overlap at tablet and desktop widths", async ({ page }) => {
  for (const viewport of viewports.filter(({ width }) => width >= 768)) {
    await page.setViewportSize(viewport);
    await openView(page, "atlas", "en");
    await expectNoPairwiseOverlap(page.locator(".node-assembly"), 4);
  }
});

test("primary touch controls meet the minimum target size", async ({ page }) => {
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    await openView(page, "atlas", "en");
    const controls = page.locator(
      ".menu-switch, .language-switch, .graph-node, .atlas-up, "
        + "[data-atlas-inspector-close]",
    );
    const boxes = await visibleBoxes(controls);
    const undersized = boxes.filter((box) => box.width < 44 || box.height < 44);
    expect(
      undersized,
      `${width}px controls must be at least 44 × 44 CSS pixels`,
    ).toEqual([]);
  }
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
  const visibleRatio = await page.locator("[data-atlas-stage]").evaluate((element) => {
    const box = element.getBoundingClientRect();
    return (Math.min(innerHeight, box.bottom) - Math.max(0, box.top)) / innerHeight;
  });
  expect(visibleRatio).toBeGreaterThanOrEqual(0.55);
  await expectNoHorizontalOverflow(page);
});

test("all seven run-stage controls keep equal geometry", async ({ page }) => {
  for (const language of ["en", "ru"]) {
    for (const width of [360, 390, 768, 1024, 1440]) {
      await page.setViewportSize({ width, height: width < 800 ? 844 : 900 });
      await openView(page, "concept", language);
      const heights = await page.locator("[data-run-grammar] button").evaluateAll(
        (elements) => elements.map((element) => element.getBoundingClientRect().height),
      );
      expect(heights).toHaveLength(7);
      expect(
        Math.max(...heights) - Math.min(...heights),
        `${language} stage controls differ at ${width}px: ${heights.join(", ")}`,
      ).toBeLessThanOrEqual(1);
    }
  }
});

test("run-stage keyboard selection does not resize the explanation", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openView(page, "concept", "ru");
  const controls = page.locator("[data-run-grammar] button");
  await controls.first().focus();
  const heights = [];
  for (let index = 0; index < 7; index += 1) {
    heights.push(await page.locator(".stage-readout").evaluate(
      (element) => element.getBoundingClientRect().height,
    ));
    if (index < 6) await page.keyboard.press("ArrowRight");
  }
  await expect(controls.last()).toHaveAttribute("aria-pressed", "true");
  expect(Math.max(...heights) - Math.min(...heights)).toBeLessThanOrEqual(1);
});

test("wide Atlas uses the canvas instead of shrinking into the center", async ({
  page,
}) => {
  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 1920, height: 1080 },
  ]) {
    await page.setViewportSize(viewport);
    await openView(page, "atlas", "en");
    const coverage = await page.locator("[data-atlas-graph]").evaluate((svg) => {
      const stage = svg.closest("[data-atlas-stage]").getBoundingClientRect();
      const nodes = [...svg.querySelectorAll(".node-assembly")]
        .map((element) => element.getBoundingClientRect());
      const left = Math.min(...nodes.map((box) => box.left));
      const right = Math.max(...nodes.map((box) => box.right));
      const top = Math.min(...nodes.map((box) => box.top));
      const bottom = Math.max(...nodes.map((box) => box.bottom));
      return {
        height: (bottom - top) / stage.height,
        width: (right - left) / stage.width,
      };
    });
    expect(coverage.width).toBeGreaterThanOrEqual(0.72);
    expect(coverage.height).toBeGreaterThanOrEqual(0.58);
  }
});

test("long-form routes put useful content in the first viewport", async ({ page }) => {
  for (const viewport of [
    { width: 768, height: 1024 },
    { width: 1440, height: 900 },
    { width: 1920, height: 1080 },
  ]) {
    await page.setViewportSize(viewport);
    for (const view of ["theory", "quickstart", "docs"]) {
      await openView(page, view, "ru");
      const hero = await page.locator(`[data-view="${view}"] .reading-hero`)
        .boundingBox();
      expect(hero.height).toBeLessThanOrEqual(Math.min(380, viewport.height * 0.42));
      const useful = view === "docs"
        ? page.locator(".docs-list article").first()
        : page.locator(`[data-view="${view}"] .prose`).first();
      const usefulBox = await useful.boundingBox();
      expect(usefulBox.y).toBeLessThan(viewport.height);
    }
  }
});

test("mobile concept shows real map content in the first viewport", async ({ page }) => {
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: width === 360 ? 800 : 844 });
    await openView(page, "concept", "ru");
    const visiblePreviewNodes = await page.locator(".preview-node").evaluateAll(
      (elements) => elements.filter((element) => {
        const box = element.getBoundingClientRect();
        return box.top < innerHeight && box.bottom > 0;
      }).length,
    );
    expect(visiblePreviewNodes).toBeGreaterThanOrEqual(1);
  }
});
