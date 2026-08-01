const { test, expect } = require("./support/test");

const localized = {
  en: {
    error: /did not load/,
    loading: /Loading/,
    reload: "Reload the page",
  },
  ru: {
    error: /не загрузил/,
    loading: /Загружа/,
    reload: "Обновить страницу",
  },
};

const routeStatuses = {
  atlas: "[data-atlas-status]",
  concept: "[data-hero-status]",
  docs: "[data-docs-status]",
};

async function expectSharedUnavailableState(page) {
  await expect(page.locator("[data-atlas-entry]")).toHaveAttribute(
    "aria-disabled",
    "true",
  );
  await expect(page.locator("[data-atlas-entry]")).toHaveAttribute(
    "tabindex",
    "-1",
  );
  const counts = await page.locator("[data-loop-count], [data-atlas-count]")
    .allTextContents();
  expect(counts).toHaveLength(2);
  expect(counts.every((value) => value.trim() && value.trim() !== "0")).toBe(true);
}

for (const language of ["en", "ru"]) {
  test(`${language} delayed data keeps localized honest status on every route`, async ({ page }) => {
    let releaseData;
    const gate = new Promise((resolve) => {
      releaseData = resolve;
    });
    await page.route("**/data/*.json", async (route) => {
      await gate;
      await route.continue();
    });

    await page.goto(language === "en" ? "/#concept" : "/?lang=ru#concept");
    try {
      if (language === "ru") {
        await expect(page.locator("[data-stage-copy]")).toHaveText(
          "Зафиксировать, что известно и откуда это взято.",
        );
        for (const [view, section] of [
          ["theory", "article"],
          ["quickstart", "quickstart"],
        ]) {
          await page.evaluate((nextView) => {
            location.hash = nextView;
          }, view);
          await expect(page.locator(`[data-content-body="${section}"]`)).toBeHidden();
          await expect(page.locator(`[data-content-status="${section}"]`)).toBeVisible();
          await expect(page.locator(`[data-content-status="${section}"] p`))
            .toContainText("Загружа");
        }
      }
      for (const [view, selector] of Object.entries(routeStatuses)) {
        await page.evaluate((nextView) => {
          location.hash = nextView;
        }, view);
        await expect(page.locator(`[data-view="${view}"]`)).toHaveClass(/\bis-active\b/);
        await expect(page.locator(selector)).toBeVisible();
        await expect(page.locator(`${selector} p`)).toHaveText(
          localized[language].loading,
        );
        await expectSharedUnavailableState(page);
      }
    } finally {
      releaseData();
    }
    await expect(page.locator("[data-docs-status]")).toBeHidden();
  });
}

test.describe("aborted data", () => {
  test.use({
    expectedConsoleErrors: [
      "Failed to load resource: net::ERR_FAILED",
    ],
    expectedRequestFailures: [
      "/data/atlas.json",
      "/data/content.json",
    ],
  });

  for (const language of ["en", "ru"]) {
    test(`${language} data failure offers a localized recovery action`, async ({ page }) => {
      await page.route("**/data/*.json", (route) => route.abort("failed"));
      await page.goto(language === "en" ? "/#concept" : "/?lang=ru#concept");

      if (language === "ru") {
        for (const [view, section] of [
          ["theory", "article"],
          ["quickstart", "quickstart"],
        ]) {
          await page.evaluate((nextView) => {
            location.hash = nextView;
          }, view);
          await expect(page.locator(`[data-content-body="${section}"]`)).toBeHidden();
          await expect(page.locator(`[data-content-status="${section}"] p`))
            .toContainText("не загрузил");
        }
      }
      for (const [view, selector] of Object.entries(routeStatuses)) {
        await page.evaluate((nextView) => {
          location.hash = nextView;
        }, view);
        await expect(page.locator(`[data-view="${view}"]`)).toHaveClass(/\bis-active\b/);
        await expect(page.locator(selector)).toBeVisible();
        await expect(page.locator(`${selector} p`)).toHaveText(
          localized[language].error,
        );
        const reload = page.locator(`${selector} [data-reload-site]`);
        await expect(reload).toBeVisible();
        await expect(reload).toHaveText(localized[language].reload);
        await expectSharedUnavailableState(page);
      }
    });
  }
});
