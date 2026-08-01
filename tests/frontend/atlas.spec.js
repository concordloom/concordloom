const { test, expect } = require("./support/test");
const {
  expectContained,
  openView,
} = require("./support/site");

for (const language of ["en", "ru"]) {
  test(`direct Atlas entry does not steal focus in ${language}`, async ({ page }) => {
    await openView(page, "atlas", language, "system-evolution");
    await expect(page.locator(".graph-node.is-current")).not.toBeFocused();
    const inspector = page.locator("[data-atlas-inspector]");
    await expect(inspector).toBeHidden();
    await expect(inspector).toHaveAttribute("role", "dialog");
    await expect(inspector).toHaveAttribute("aria-modal", "true");
    await expect(inspector).toHaveAttribute("aria-hidden", "true");
    await expect(inspector).toHaveAttribute("inert", "");
  });

  test(`Atlas drill-down and back navigation work in ${language}`, async ({ page }) => {
    await openView(page, "atlas", language);
    const rootId = await page.locator(".graph-node.is-current").getAttribute("data-loop-id");
    const child = page.locator('[data-loop-id="system-evolution"]');
    await expect(child).toBeVisible();
    const childId = await child.getAttribute("data-loop-id");
    const rootUrl = page.url();
    await child.click();
    expect(page.url()).toBe(rootUrl);
    const inspector = page.locator("[data-atlas-inspector]");
    await expect(inspector).toBeVisible();
    await expect(page.locator("[data-atlas-inspector-close]")).toBeFocused();
    const openCycle = page.locator(".inspector-open-cycle");
    await expect(openCycle).toBeVisible();
    await openCycle.click();
    await expect(page).toHaveURL(new RegExp(`#atlas/${childId}$`));
    await expect(page.locator(".graph-node.is-current")).toBeFocused();
    await expect(inspector).toBeHidden();
    await expect(page.locator("[data-atlas-up]")).toBeVisible();
    await expect(page.locator("[data-atlas-breadcrumbs] a")).toHaveCount(2);
    await page.locator("[data-atlas-up]").click();
    await expect(page).toHaveURL(new RegExp(`#atlas/${rootId}$`));
    await expect(page.locator(".graph-node.is-current")).toBeFocused();
  });

  test(`Atlas graph is keyboard-operable in ${language}`, async ({ page }) => {
    await openView(page, "atlas", language);
    const child = page.locator('[data-loop-id="system-evolution"]');
    const childId = await child.getAttribute("data-loop-id");
    const rootUrl = page.url();
    await child.focus();
    await expect(child).toBeFocused();
    await page.keyboard.press("Enter");
    expect(page.url()).toBe(rootUrl);
    await expect(page.locator("[data-atlas-inspector]")).toBeVisible();
    await expect(page.locator("[data-atlas-inspector-close]")).toBeFocused();
    await page.locator(".inspector-open-cycle").focus();
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

test("Atlas assemblies stay inside the graph stage", async ({ page }) => {
  await openView(page, "atlas", "ru");
  await expectContained(
    page.locator(".node-assembly"),
    page.locator("[data-atlas-stage]"),
  );
});

test("cycle details exist only on demand and do not resize the graph", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openView(page, "atlas", "en");
  const inspector = page.locator("[data-atlas-inspector]");
  await expect(inspector).toBeHidden();
  await expect(inspector).toHaveAttribute("aria-hidden", "true");
  const before = await page.locator("[data-atlas-stage]").boundingBox();
  const urlBefore = page.url();
  await page.locator(".graph-node.is-current").click();
  await expect(inspector).toBeVisible();
  await expect(inspector).toHaveAttribute("role", "dialog");
  await expect(inspector).toHaveAttribute("aria-modal", "true");
  await expect(inspector).toHaveAttribute("aria-hidden", "false");
  await expect(page.locator("[data-atlas-inspector-close]")).toBeFocused();
  await expect(page.locator(".inspector-open-cycle")).toHaveCount(0);
  expect(page.url()).toBe(urlBefore);
  const after = await page.locator("[data-atlas-stage]").boundingBox();
  expect(after).toEqual(before);
  await page.locator("[data-atlas-inspector-close]").click();
  await expect(inspector).toBeHidden();
  await expect(page.locator(".graph-node.is-current")).toBeFocused();
});

test("cycle details trap focus and Escape restores the node trigger", async ({ page }) => {
  await openView(page, "atlas", "en");
  const trigger = page.locator('[data-loop-id="system-evolution"]');
  await trigger.click();
  const inspector = page.locator("[data-atlas-inspector]");
  const close = page.locator("[data-atlas-inspector-close]");
  await expect(inspector).toBeVisible();
  await expect(close).toBeFocused();

  const lastFocusable = inspector.locator(
    "a[href], button:not([disabled]), summary, [tabindex]:not([tabindex='-1'])",
  ).last();
  await lastFocusable.focus();
  await page.keyboard.press("Tab");
  await expect(close).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(lastFocusable).toBeFocused();

  await page.keyboard.press("Escape");
  await expect(inspector).toBeHidden();
  await expect(trigger).toBeFocused();
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
      await page.locator('[data-loop-id="system-evolution"]').click();
      await expect(page.locator("[data-atlas-inspector]")).toBeVisible();
      await page.locator(".inspector-open-cycle").click();
      await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
    }
  }
});

test("browser Back restores the parent graph without opening details", async ({ page }) => {
  await openView(page, "atlas", "en");
  const rootId = await page.locator(".graph-node.is-current").getAttribute("data-loop-id");
  await page.locator('[data-loop-id="system-evolution"]').click();
  await page.locator(".inspector-open-cycle").click();
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`#atlas/${rootId}$`));
  await expect(page.locator(".graph-node.is-current")).toHaveAttribute(
    "data-loop-id",
    rootId,
  );
  await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
});

test("a nested Atlas hash survives reload and browser Forward", async ({ page }) => {
  await openView(page, "atlas", "ru");
  const rootId = await page.locator(".graph-node.is-current").getAttribute("data-loop-id");
  const child = page.locator('[data-loop-id="system-evolution"]');
  const childId = await child.getAttribute("data-loop-id");
  await child.click();
  await page.locator(".inspector-open-cycle").click();
  await expect(page).toHaveURL(new RegExp(`#atlas/${childId}$`));
  await page.reload();
  await expect(page.locator(".graph-node.is-current")).toHaveAttribute(
    "data-loop-id",
    childId,
  );
  await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
  await page.goBack();
  await expect(page.locator(".graph-node.is-current")).toHaveAttribute(
    "data-loop-id",
    rootId,
  );
  await page.goForward();
  await expect(page.locator(".graph-node.is-current")).toHaveAttribute(
    "data-loop-id",
    childId,
  );
  await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
});
