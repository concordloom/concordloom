const { test, expect } = require("./support/test");
const { waitForSite } = require("./support/site");

const SITE_ORIGIN = "https://concordloom.github.io/concordloom";
const PUBLIC_DOC_SLUGS = [
  "concepts",
  "architecture",
  "spec-v0.1",
  "trust-model",
  "quickstart",
  "article",
  "atlas",
  "codex-plugin",
  "how-to-help",
  "repository-trial",
  "ai-agent-governance",
  "decisions",
  "release",
  "writing",
  "design-system",
  "frontend-cycle-proposal",
];

const HOME_METADATA = {
  en: {
    title: "Concord Loom — map and govern development loops",
    description:
      "Open-source framework for mapping and governing bounded development loops across people, AI agents, tools, and repositories.",
  },
  ru: {
    title: "Concord Loom — карта и контроль циклов разработки",
    description:
      "Открытый фреймворк для картирования и управления ограниченными циклами разработки с участием людей, ИИ-агентов, инструментов и репозиториев.",
  },
};

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
    await expect(page).toHaveTitle(HOME_METADATA[locale].title);
    await expect(page.locator('meta[name="description"]')).toHaveAttribute(
      "content",
      HOME_METADATA[locale].description,
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

for (const locale of ["en", "ru"]) {
  test(`/${locale}/ public documentation pages are crawlable and language-paired`, async ({ page }) => {
    for (const slug of PUBLIC_DOC_SLUGS) {
      const response = await page.request.get(`/docs/${locale}/${slug}/`);
      expect(response.status(), `${locale}/${slug} must be published`).toBe(200);
      const body = await response.text();
      expect(body).toContain(`<html lang="${locale}"`);
      expect(body).toContain(
        `<link rel="canonical" href="${SITE_ORIGIN}/docs/${locale}/${slug}/">`,
      );
      expect(body).toContain(
        `<link rel="alternate" hreflang="en" href="${SITE_ORIGIN}/docs/en/${slug}/">`,
      );
      expect(body).toContain(
        `<link rel="alternate" hreflang="ru" href="${SITE_ORIGIN}/docs/ru/${slug}/">`,
      );
      expect((body.match(/<h1\b/g) || []).length, `${locale}/${slug} needs one h1`).toBe(1);
      expect(body).toMatch(/<title>[^<]+ \| Concord Loom<\/title>/);
      expect(body).toMatch(/<meta name="description" content="[^\"]+">/);
    }
  });
}

test("sitemap lists every canonical page once and pairs localized documentation", async ({ page }) => {
  const response = await page.request.get("/sitemap.xml");
  expect(response.status()).toBe(200);
  const sitemap = await response.text();
  expect(sitemap).toContain('xmlns:xhtml="http://www.w3.org/1999/xhtml"');

  const locations = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((match) => match[1]);
  expect(locations).toHaveLength(37);
  expect(new Set(locations).size).toBe(locations.length);
  expect(locations).toContain(`${SITE_ORIGIN}/`);

  for (const locale of ["en", "ru"]) {
    expect(locations).toContain(`${SITE_ORIGIN}/${locale}/`);
    expect(locations).toContain(`${SITE_ORIGIN}/docs/${locale}/`);
    for (const slug of PUBLIC_DOC_SLUGS) {
      expect(locations).toContain(`${SITE_ORIGIN}/docs/${locale}/${slug}/`);
    }
  }
});

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
