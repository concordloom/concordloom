const { test, expect } = require("./support/test");
const {
  expectContained,
  expectNoPairwiseOverlap,
  openView,
} = require("./support/site");

for (const language of ["en", "ru"]) {
  test(`direct Atlas entry does not steal focus in ${language}`, async ({ page }) => {
    await openView(page, "atlas", language, "system-evolution");
    await expect(page.locator(".graph-node.is-current")).not.toBeFocused();
    await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
  });

  test(`Atlas drill-down and back navigation work in ${language}`, async ({ page }) => {
    await openView(page, "atlas", language);
    const rootId = await page.locator(".graph-node.is-current").getAttribute("data-loop-id");
    const child = page.locator(".graph-node:not(.is-current)").first();
    await expect(child).toBeVisible();
    const childId = await child.getAttribute("data-loop-id");
    await child.click();
    await expect(page).toHaveURL(new RegExp(`#atlas/${childId}$`));
    await expect(page.locator(".graph-node.is-current")).toBeFocused();
    await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
    await expect(page.locator(".atlas-history li")).toHaveCount(2);
    await expect(page.locator("[data-atlas-up]")).toBeVisible();
    await page.locator(".graph-node.is-current").click();
    await expect(page.locator("[data-atlas-inspector]")).toBeVisible();
    await page.keyboard.press("Escape");
    await page.locator("[data-atlas-up]").click();
    await expect(page).toHaveURL(new RegExp(`#atlas/${rootId}$`));
    await expect(page.locator(".graph-node.is-current")).toBeFocused();
  });

  test(`Atlas graph is keyboard-operable in ${language}`, async ({ page }) => {
    await openView(page, "atlas", language);
    const child = page.locator(".graph-node:not(.is-current)").first();
    const childId = await child.getAttribute("data-loop-id");
    await child.focus();
    await expect(child).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(new RegExp(`#atlas/${childId}$`));
    await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
    await expect(page.locator(".graph-node.is-current")).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("[data-atlas-inspector]")).toBeVisible();
    await expect(page.locator("[data-atlas-inspector]")).toContainText(
      language === "ru" ? /[А-Яа-яЁё]/ : /[A-Za-z]/,
    );
  });
}

test("Atlas assemblies stay inside the mechanical stage", async ({ page }) => {
  await openView(page, "atlas", "ru");
  await expectNoPairwiseOverlap(page.locator(".atlas-history li"), 4);
  await expectContained(
    page.locator(".node-assembly"),
    page.locator(".atlas-stage"),
  );
});

test("cycle details overlay without changing the graph geometry", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openView(page, "atlas", "en");
  const before = await page.locator(".atlas-stage").boundingBox();
  await page.locator(".graph-node.is-current").click();
  await expect(page.locator("[data-atlas-inspector]")).toBeVisible();
  const after = await page.locator(".atlas-stage").boundingBox();
  expect(after).toEqual(before);
  await page.locator("[data-atlas-inspector-close]").click();
  await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
});

test("Atlas exposes selected state and a useful accessible name", async ({ page }) => {
  await openView(page, "atlas", "en");
  const current = page.locator(".graph-node.is-current");
  await expect(current).toHaveCount(1);
  await expect(current).toHaveAttribute("aria-label", /.+/);
  const child = page.locator(".graph-node:not(.is-current)").first();
  await expect(child).toHaveAttribute("aria-label", /Contained cycles|No contained cycles/);
});

test("Atlas renders one unique graph for the selected level", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openView(page, "atlas", "ru");
  for (let depth = 0; depth < 2; depth += 1) {
    const graph = await page.locator("[data-atlas-graph]").evaluate((element) => {
      const ids = [...element.querySelectorAll("[data-loop-id]")]
        .map((node) => node.getAttribute("data-loop-id"));
      return {
        ids,
        levels: element.querySelectorAll(".level-constellation").length,
        legacyContext: element.querySelectorAll(
          ".parent-constellation, .level-thread, .level-thread-arrow",
        ).length,
      };
    });
    expect(new Set(graph.ids).size).toBe(graph.ids.length);
    expect(graph.levels).toBe(1);
    expect(graph.legacyContext).toBe(0);
    if (depth === 0) {
      await page.locator(".graph-node:not(.is-current)").first().click();
      await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
    }
  }
});

test("browser Back restores the parent graph without opening details", async ({ page }) => {
  await openView(page, "atlas", "en");
  const rootId = await page.locator(".graph-node.is-current").getAttribute("data-loop-id");
  await page.locator(".graph-node:not(.is-current)").first().click();
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`#atlas/${rootId}$`));
  await expect(page.locator(".graph-node.is-current")).toHaveAttribute(
    "data-loop-id",
    rootId,
  );
  await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
});
