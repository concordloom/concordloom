const { test, expect } = require("./support/test");
const {
  expectNoHorizontalOverflow,
  expectNoPairwiseOverlap,
} = require("./support/site");

test("dependency-free workshop exposes every lifecycle state", async ({ page }) => {
  await page.goto("/workshop/");
  await expect(page.locator("h1")).toHaveText("Signal Constellation Workshop");
  const controls = page.locator("[data-phase-control]");
  await expect(controls).toHaveCount(5);
  for (const control of await controls.all()) {
    const phase = await control.getAttribute("data-phase-control");
    await control.click();
    await expect(page.locator(`.system-rail [data-phase="${phase}"]`)).toHaveClass(
      /\bis-active\b/,
    );
    await expect(page.locator(`.system-rail [data-phase="${phase}"]`)).toHaveAttribute(
      "aria-current",
      "step",
    );
  }
});

test("workshop stress states do not overlap or overflow", async ({ page }) => {
  await page.goto("/workshop/");
  await page.locator("[data-language=ru]").click();
  await expectNoHorizontalOverflow(page);
  await expectNoPairwiseOverlap(page.locator(".workshop-node-label"), 2);
  await expectNoPairwiseOverlap(page.locator(".system-rail li"), 2);
  await expect(page.locator(".system-rail")).toBeVisible();
  await expect(page.locator("h1")).toHaveText("Стенд «Созвездие сигналов»");
  await expect(page.locator("#rail-title")).toHaveText("Цикл изменений");
  await expect(page.locator("#atlas-title")).toHaveText("Состояния механических узлов");
  await expect(page.locator("[data-phase-control=publish]")).toHaveText("Публикация");

  const railTextIsContained = await page.locator(".system-rail li span").evaluateAll(
    (labels) => labels.every((label) => {
      const text = label.getBoundingClientRect();
      const cell = label.closest("li").getBoundingClientRect();
      return text.left >= cell.left - 1 && text.right <= cell.right + 1;
    }),
  );
  expect(railTextIsContained).toBe(true);

  const controlsBottom = await page.locator(".workshop-controls").evaluate(
    (element) => element.getBoundingClientRect().bottom,
  );
  const stressTop = await page.locator(".workshop-panel").nth(1).evaluate(
    (element) => element.getBoundingClientRect().top,
  );
  expect(controlsBottom).toBeLessThanOrEqual(stressTop);

  const contrast = await page.locator("[data-phase-control=map]").evaluate((element) => {
    const parse = (color) => color.match(/\d+/g).slice(0, 3).map(Number);
    const luminance = (rgb) => {
      const channels = rgb.map((value) => {
        const channel = value / 255;
        return channel <= 0.04045
          ? channel / 12.92
          : ((channel + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
    };
    const style = getComputedStyle(element);
    const foreground = luminance(parse(style.color));
    const background = luminance(parse(style.backgroundColor));
    return (Math.max(foreground, background) + 0.05) /
      (Math.min(foreground, background) + 0.05);
  });
  expect(contrast).toBeGreaterThanOrEqual(4.5);
});
