const AxeBuilder = require("@axe-core/playwright").default;
const { test, expect } = require("./support/test");
const { openView } = require("./support/site");

for (const language of ["en", "ru"]) {
  for (const view of ["concept", "quickstart", "atlas", "docs"]) {
    test(`${language} ${view} has no automatic WCAG A/AA violations`, async ({ page }) => {
      await openView(page, view, language);
      const result = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa"])
        .analyze();
      expect(result.violations).toEqual([]);
    });
  }

  test(`${language} nested Atlas has no automatic WCAG A/AA violations`, async ({ page }) => {
    await openView(page, "atlas", language, "system-evolution");
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    expect(result.violations).toEqual([]);
  });
}

test("skip link reaches the main content", async ({ page }) => {
  await openView(page, "concept", "en");
  await page.keyboard.press("Tab");
  const skip = page.locator(".skip-link");
  await expect(skip).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
});

test("mobile menu exposes, closes and restores focus", async ({ page }, testInfo) => {
  test.skip(!testInfo.project.name.includes("mobile"), "mobile contract");
  await openView(page, "concept", "ru");
  const trigger = page.locator(".menu-switch");
  await trigger.click();
  await expect(trigger).toHaveAttribute("aria-expanded", "true");
  await expect(page.locator("#primary-nav")).toHaveClass(/\bis-open\b/);
  await page.keyboard.press("Escape");
  await expect(trigger).toHaveAttribute("aria-expanded", "false");
  await expect(trigger).toBeFocused();
});

test.describe("reduced motion", () => {
  test.use({ reducedMotion: "reduce" });

  test("Atlas drill-down leaves no running animations", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await openView(page, "atlas", "en");
    await expect
      .poll(() =>
        page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches),
      )
      .toBe(true);
    await page.locator(".graph-node:not(.is-current)").first().click();
    await page.waitForTimeout(100);
    const running = await page.evaluate(() =>
      document
        .getAnimations()
        .filter((animation) => animation.playState === "running")
        .map((animation) => {
          const target = animation.effect?.target;
          return {
            className:
              typeof target?.className === "string"
                ? target.className
                : target?.getAttribute?.("class") || "",
            duration: animation.effect?.getComputedTiming().duration,
            name: animation.animationName || "",
            tagName: target?.tagName || "",
          };
        }),
    );
    expect(running).toEqual([]);
  });
});
