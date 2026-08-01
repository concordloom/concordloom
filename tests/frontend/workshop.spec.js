const AxeBuilder = require("@axe-core/playwright").default;
const { test, expect } = require("./support/test");
const {
  expectNoHorizontalOverflow,
  expectNoPairwiseOverlap,
  visibleBoxes,
} = require("./support/site");

test("dependency-free workshop exposes every Signal Canvas lifecycle state", async ({ page }) => {
  await page.goto("/workshop/");
  await expect(page.locator("h1")).toContainText("Signal Canvas");
  await expect(page.locator("body")).toHaveAttribute(
    "data-design-system",
    "signal-canvas",
  );
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
  await page.locator("[data-workshop-language-switch]").click();
  await expectNoHorizontalOverflow(page);
  await expectNoPairwiseOverlap(page.locator(".workshop-node-label"), 2);
  await expectNoPairwiseOverlap(page.locator(".system-rail li"), 2);
  await expect(page.locator(".system-rail")).toBeVisible();
  await expect(page.locator("h1")).toContainText("Signal Canvas");
  await expect(page.locator("h1")).toContainText(/[А-Яа-яЁё]/);
  await expect(page.locator("#rail-title")).toHaveText("Цикл изменений");
  await expect(page.locator("#atlas-title")).toHaveText("Состояния модуля цикла");
  await expect(page.locator(".system-rail")).toHaveAttribute(
    "aria-label",
    "Цикл изменений",
  );
  await expect(page.locator("[data-phase-control=publish]")).toHaveText("Публикация");
  await expect(page.locator(".workshop-node")).toHaveCount(9);
  await expect(page.locator('[data-node-state="loading"]')).toHaveAttribute(
    "aria-busy",
    "true",
  );
  await expect(page.locator('[data-node-state="error"]')).toContainText(
    "Принятые данные недоступны",
  );
  await expect(page.locator('[data-node-state="stale"]')).toContainText(
    "Показана сохранённая карта",
  );
  await expect(page.locator('[data-node-state="stale"]')).toHaveAttribute(
    "role",
    "status",
  );

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

for (const language of ["en", "ru"]) {
  test(`workshop ${language} states are accessible and keyboard-real`, async ({ page }) => {
    await page.goto("/workshop/");
    if (language === "ru") {
      await page.locator("[data-workshop-language-switch]").click();
    }

    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(result.violations).toEqual([]);

    const focusState = page.locator('[data-node-state="focus"]');
    await focusState.focus();
    await page.keyboard.press("Shift+Tab");
    await page.keyboard.press("Tab");
    await expect(focusState).toBeFocused();
    const outline = await focusState.evaluate(
      (element) => getComputedStyle(element).outlineStyle,
    );
    expect(outline).not.toBe("none");

    await expect(page.locator('[data-node-state="loading"]')).toHaveAttribute(
      "role",
      "status",
    );
    await expect(page.locator('[data-node-state="error"]')).toHaveAttribute(
      "role",
      "alert",
    );
    const stale = page.locator('[data-node-state="stale"]');
    await expect(stale).toHaveAttribute("role", "status");
    await expect(stale).toContainText(
      language === "en" ? "This is the saved map" : "Показана сохранённая карта",
    );
  });
}

test("workshop reflows and keeps controls touchable", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 800 });
  await page.goto("/workshop/");
  await page.locator("[data-workshop-language-switch]").click();
  await expectNoHorizontalOverflow(page);
  const boxes = await visibleBoxes(
    page.locator(
      ".workshop-language button, [data-phase-control], "
        + ".workshop-node:not(:disabled)",
    ),
  );
  expect(
    boxes.filter((box) => box.width < 44 || box.height < 44),
    "workshop controls must be at least 44 × 44 CSS pixels",
  ).toEqual([]);
});

test("mobile lifecycle readout shows one complete step without label collisions", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/workshop/");
  await page.locator("[data-workshop-language-switch]").click();

  const rail = page.locator(".workshop-rail");
  const visibleSteps = rail.locator("li:visible");
  await expect(visibleSteps).toHaveCount(1);
  await expect(visibleSteps).toHaveAttribute("data-phase", "map");
  await expect(visibleSteps.locator(".workshop-progress-count"))
    .toHaveText("Шаг 1 из 5");
  await expect(visibleSteps.locator("span")).toHaveText("Карта");

  const readable = await visibleSteps.evaluate((step) => {
    const stepBox = step.getBoundingClientRect();
    const countBox = step.querySelector("small").getBoundingClientRect();
    const labelBox = step.querySelector("span").getBoundingClientRect();
    const contained = [countBox, labelBox].every(
      (box) => box.left >= stepBox.left && box.right <= stepBox.right,
    );
    const separated = countBox.right + 8 <= labelBox.left;
    return contained && separated;
  });
  expect(readable, "count and label must be contained and visibly separated")
    .toBe(true);

  await page.locator("[data-phase-control=publish]").click();
  await expect(visibleSteps).toHaveCount(1);
  await expect(visibleSteps).toHaveAttribute("data-phase", "publish");
  await expect(visibleSteps.locator(".workshop-progress-count"))
    .toHaveText("Шаг 4 из 5");
  await expect(visibleSteps.locator("span")).toHaveText("Релиз");
  await expectNoHorizontalOverflow(page);
});
