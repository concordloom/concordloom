const { test, expect } = require("@playwright/test");

test("the retired Patch Panel direction cannot return", async ({ page }) => {
  await page.goto("/?lang=en#concept");
  await expect(page.locator("html")).toHaveAttribute(
    "data-design-system",
    "signal-canvas",
  );
  await expect(page.locator("body")).toHaveAttribute(
    "data-design-system",
    "signal-canvas",
  );
  await expect(page.locator(".patch-panel")).toHaveCount(0);
});
