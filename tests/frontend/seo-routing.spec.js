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

test("language switch uses localized canonical routes and preserves the current view", async ({ page }) => {
  await page.goto("/en/#quickstart");
  await waitForSite(page);

  await page.locator(".language-switch").click();
  await expect.poll(() => new URL(page.url()).pathname).toBe("/ru/");
  await expect.poll(() => new URL(page.url()).hash).toBe("#quickstart");
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  expect(new URL(page.url()).searchParams.has("lang")).toBe(false);

  await page.locator(".language-switch").click();
  await expect.poll(() => new URL(page.url()).pathname).toBe("/en/");
  await expect.poll(() => new URL(page.url()).hash).toBe("#quickstart");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  expect(new URL(page.url()).searchParams.has("lang")).toBe(false);
});

test("legacy localized lang query redirects to the matching canonical route", async ({ page }) => {
  await page.goto("/en/?lang=ru#quickstart");
  await page.waitForURL("**/ru/#quickstart");
  await waitForSite(page);

  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  expect(new URL(page.url()).searchParams.has("lang")).toBe(false);
});
