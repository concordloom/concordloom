const { test, expect } = require("./support/test");
const {
  expectAllVisibleInteractiveTargets,
  expectNoHorizontalOverflow,
  openView,
} = require("./support/site");

async function proposeRoute(page, language = "en") {
  const request = language === "ru"
    ? "Исправить адаптивную вёрстку сайта"
    : "Fix the responsive frontend layout";
  await page.locator("[data-route-preview-request]").fill(request);
  await page.locator("[data-route-preview-submit]").click();
  await expect(page.locator("[data-route-preview-result]")).toBeVisible();
  return request;
}

for (const language of ["en", "ru"]) {
  test(`Route Preview proposes a localized read-only path in ${language}`, async ({ page }) => {
    await openView(page, "atlas", language);
    await proposeRoute(page, language);

    await expect(page.locator("[data-route-preview-message]")).toHaveText(
      language === "ru"
        ? "Путь подобран. Ничего не запущено."
        : "Suggested path found. Nothing has started.",
    );
    await expect(page.locator("[data-route-preview-area]")).toContainText(
      language === "ru" ? "Область задачи" : "Task area",
    );
    await expect(page.locator("[data-route-preview-area] a[href='#atlas/design-site-experience']"))
      .toBeVisible();
    await expect(page.locator("[data-route-preview-list] li")).toHaveCount(7);
    await expect(page.locator("[data-route-preview-list] [aria-current='step']")).toContainText(
      language === "ru" ? "Реализовать интерфейс" : "Implement Frontend Candidate",
    );
    await expect(page.locator("[data-route-preview-list] a[href='#atlas/verify-frontend-candidate']"))
      .toBeVisible();
    await expect(page.locator("[data-route-preview-list] a[href='#atlas/critique-frontend-experience']"))
      .toBeVisible();
    expect(await page.locator(".graph-node.is-proposed-route").count()).toBeGreaterThanOrEqual(1);
    await expect(page.locator("[data-route-preview-result]")).toContainText(
      language === "ru"
        ? "Публичный Атлас работает только для просмотра"
        : "This public Atlas is read-only",
    );
    await expect(page.locator("[data-route-preview-effects]")).toHaveText(
      language === "ru"
        ? /черновик.+отдельная авторизация.+без сети.+изменений за пределами репозитория.+ничего не запущено/i
        : /exact draft.+separate authorization.+no network access.+no changes outside the repository.+nothing is running/i,
    );
    await expect(page.getByRole("button", { name: /start run|запустить/i })).toHaveCount(0);
    await expect(page.getByRole("link", { name: /start run|запустить/i })).toHaveCount(0);
  });
}

for (const language of ["en", "ru"]) {
  test(`Route Preview discloses future publication effects in ${language}`, async ({ page }) => {
    await openView(page, "atlas", language);
    await page.locator("[data-route-preview-request]").fill(
      language === "ru" ? "Опубликовать проверенный сайт" : "Publish the verified site",
    );
    await page.locator("[data-route-preview-submit]").click();
    await expect(page.locator("[data-route-preview-result]")).toBeVisible();
    await expect(page.locator("[data-route-preview-effects]")).toHaveText(
      language === "ru"
        ? /черновик.+авторизация.+передавать данные по сети.+опубликовать сайт в GitHub Pages.+ничего не запущено/i
        : /exact draft.+authorization.+send data over the network.+publish the site to GitHub Pages.+nothing is running/i,
    );
  });
}

for (const [language, request, expectedTarget] of [
  ["en", "Fix the broken site", "implement-frontend-surface"],
  ["en", "Make the site responsive", "implement-frontend-surface"],
  ["en", "Fix the site typography", "implement-frontend-surface"],
  ["ru", "Почини вёрстку на телефоне", "implement-frontend-surface"],
  ["ru", "Переделай дизайн сайта", "implement-frontend-surface"],
  ["ru", "Исправь типографику сайта", "implement-frontend-surface"],
  ["en", "Protect the main branch", "maintain-repository-presence"],
  ["ru", "Защити ветку main", "maintain-repository-presence"],
  ["en", "Ship a new release", "plan-release"],
  ["ru", "Сделай новый релиз", "plan-release"],
  ["en", "Review the proposed new rules", "review-successor"],
  ["ru", "Проверь предложенную новую версию правил", "review-successor"],
  ["en", "Activate the reviewed new rules", "activate-successor"],
  ["ru", "Включи проверенную новую версию правил", "activate-successor"],
  ["ru", "Добавь новую функцию", "decide-product"],
]) {
  test(`semantic route ${language}: ${request}`, async ({ page }) => {
    await openView(page, "atlas", language);
    await page.locator("[data-route-preview-request]").fill(request);
    await page.locator("[data-route-preview-submit]").click();
    await expect(page.locator("[data-route-preview-result]")).toBeVisible();
    await expect(
      page.locator(`[data-route-preview-list] a[href='#atlas/${expectedTarget}'][aria-current='step']`),
    ).toBeVisible();
  });
}

for (const [language, request] of [
  ["en", "Reduce model token usage"],
  ["ru", "Сократи расход токенов модели"],
]) {
  test(`token-cost request does not become a threat route in ${language}`, async ({ page }) => {
    await openView(page, "atlas", language);
    await page.locator("[data-route-preview-request]").fill(request);
    await page.locator("[data-route-preview-submit]").click();
    await expect(page.locator("[data-route-preview-result]")).toBeHidden();
    await expect(page.locator("[data-route-preview-message]")).toBeVisible();
  });
}

test("Ctrl+Enter finds a route and raw request text is never persisted", async ({ page }) => {
  await openView(page, "atlas", "en");
  const request = "Fix the responsive frontend layout";
  const input = page.locator("[data-route-preview-request]");
  await input.fill(request);
  await input.press("Control+Enter");
  await expect(page.locator("[data-route-preview-result]")).toBeVisible();
  expect(decodeURIComponent(page.url())).not.toContain(request);
  const persisted = await page.evaluate(() => ({
    keys: Object.keys(localStorage),
    values: Object.values(localStorage),
  }));
  expect(persisted.values).not.toContain(request);
  expect(persisted.keys).not.toContain("route-preview-request");

  await page.reload();
  await expect(page.locator("[data-route-preview-request]")).toHaveValue("");
  await expect(page.locator("[data-route-preview-result]")).toBeHidden();
});

test("an unclear request explains how to recover", async ({ page }) => {
  await openView(page, "atlas", "ru");
  await page.locator("[data-route-preview-request]").fill("банан");
  await page.locator("[data-route-preview-submit]").click();
  await expect(page.locator("[data-route-preview-result]")).toBeHidden();
  await expect(page.locator("[data-route-preview-message]")).toContainText(
    "Назовите конкретный результат",
  );
});

test("keyboard choice hands focus to the proposed route", async ({ page }) => {
  await openView(page, "atlas", "ru");
  const request = page.locator("[data-route-preview-request]");
  await request.fill("опубликовать");
  await request.press("Control+Enter");
  const choice = page.locator("[data-route-preview-choices] button").first();
  await expect(choice).toBeVisible();
  await choice.focus();
  await choice.press("Enter");
  await expect(page.locator("[data-route-preview-result]")).toBeVisible();
  await expect(page.locator("#route-preview-result-title")).toBeFocused();
});

test("Russian route example is not clipped at the 200 percent reflow equivalent", async ({ page }) => {
  await page.setViewportSize({ width: 720, height: 450 });
  await openView(page, "atlas", "ru");
  const geometry = await page.locator("[data-route-preview-request]").evaluate((element) => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }));
  expect(geometry.scrollHeight).toBeLessThanOrEqual(geometry.clientHeight + 1);
});

for (const viewport of [
  { width: 360, height: 800 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
]) {
  test(`Route Preview reflows at ${viewport.width} × ${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await openView(page, "atlas", "en");
    await proposeRoute(page);
    await expectNoHorizontalOverflow(page);
    await expectAllVisibleInteractiveTargets(page);
  });
}
