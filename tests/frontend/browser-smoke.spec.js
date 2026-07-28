const AxeBuilder = require("@axe-core/playwright").default;
const { test, expect } = require("./support/test");
const { expectNoHorizontalOverflow, openView } = require("./support/site");

test("critical Atlas route works in the secondary browser", async ({ page }) => {
  await openView(page, "atlas", "ru");
  await expect(page.locator(".graph-node.is-current")).toHaveCount(1);
  await expect(page.locator("[data-atlas-inspector]")).toContainText(/[А-Яа-яЁё]/);
  await expectNoHorizontalOverflow(page);
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(result.violations).toEqual([]);
});
