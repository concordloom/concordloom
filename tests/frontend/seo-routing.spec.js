const { test, expect } = require("./support/test");
const { waitForSite } = require("./support/site");

const SITE_ORIGIN = "https://concordloom.github.io/concordloom";

for (const locale of ["en", "ru"]) {
  test(`/${locale}/ opens the interactive site instead of documentation`, async ({ page }) => {
    await page.goto(`/${locale}/`);
    await waitForSite(page);

    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(page.locator(".hero")).toBeVisible();
    await expect(page.locator(".content-hero")).toHaveCount(0);
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
      "href",
      `${SITE_ORIGIN}/${locale}/`,
    );
  });

  test(`/docs/${locale}/ keeps the documentation on its own URL`, async ({ page }) => {
    await page.goto(`/docs/${locale}/`);

    await expect(page.locator("html")).toHaveAttribute("lang", locale);
    await expect(page.locator(".content-hero")).toBeVisible();
    await expect(page.locator(".hero")).toHaveCount(0);
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
      "href",
      `${SITE_ORIGIN}/docs/${locale}/`,
    );
  });
}
