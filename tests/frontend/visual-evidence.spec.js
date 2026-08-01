const { test, expect } = require("./support/test");
const {
  expectNoHorizontalOverflow,
  openView,
} = require("./support/site");

const routes = ["concept", "theory", "quickstart", "atlas", "docs"];

for (const language of ["en", "ru"]) {
  for (const view of routes) {
    test(`${language} ${view} Signal Canvas visual contract`, async ({ page }) => {
      await openView(page, view, language);
      await expectNoHorizontalOverflow(page);
      await expect(page.locator("body")).toHaveAttribute(
        "data-design-system",
        "signal-canvas",
      );

      if (view === "atlas") {
        await expect(page.locator(".graph-node.is-current")).toHaveCount(1);
        await expect(page.locator(".node-assembly")).not.toHaveCount(0);
        await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
      }

      await expect(page).toHaveScreenshot(`${language}-${view}.png`, {
        animations: "disabled",
        caret: "hide",
        fullPage: false,
        scale: "css",
      });
    });
  }

  test(`${language} nested Atlas visual contract`, async ({ page }) => {
    await openView(page, "atlas", language, "system-evolution");
    await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
    await expect(page).toHaveScreenshot(`${language}-atlas-nested.png`, {
      animations: "disabled",
      caret: "hide",
      fullPage: false,
      scale: "css",
    });
  });

  test(`${language} Atlas details drawer visual contract`, async ({ page }) => {
    await openView(page, "atlas", language);
    await page.locator('[data-loop-id="system-evolution"]').click();
    await expect(page.locator("[data-atlas-inspector]")).toBeVisible();
    await expect(page.locator(".inspector-open-cycle")).toBeVisible();
    await expect(page).toHaveScreenshot(`${language}-atlas-details.png`, {
      animations: "disabled",
      caret: "hide",
      fullPage: false,
      scale: "css",
    });
  });

  test(`${language} component workshop visual contract`, async ({ page }) => {
    await page.goto("/workshop/");
    if (language === "ru") {
      await page.locator("[data-workshop-language-switch]").click();
    }
    await expect(page.locator("body")).toHaveAttribute(
      "data-design-system",
      "signal-canvas",
    );
    await expectNoHorizontalOverflow(page);
    const states = page.locator("#atlas-states");
    const stale = states.locator('[data-node-state="stale"]');
    await stale.scrollIntoViewIfNeeded();
    await expect(stale).toBeVisible();
    await expect(page).toHaveScreenshot(`${language}-workshop.png`, {
      animations: "disabled",
      caret: "hide",
      fullPage: false,
      scale: "css",
    });
  });
}
