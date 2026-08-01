const { createHash } = require("node:crypto");
const { spawnSync } = require("node:child_process");
const { readFileSync } = require("node:fs");
const { test, expect } = require("./support/test");
const {
  openView,
  visibleInteractiveTargetFailures,
} = require("./support/site");

test("the canonical baseline updater works from a clean read-only clone", () => {
  const updater = readFileSync(
    "tests/frontend/update-visual-baselines.mjs",
    "utf8",
  );

  expect(updater).toContain('"/work:rw,exec,mode=1777"');
  expect(updater).toContain("dst=/source,readonly");
  expect(updater).toContain("dst=/baselines");
  expect(updater).toContain('"set -euo pipefail"');
  expect(updater).toContain("lstatSync(baselineCursor)");
  expect(updater).toContain("realpathSync(baselineCursor)");
  expect(updater).toContain("relative(repository, baselines)");
  expect(updater).toContain("baselinesRelative.startsWith(`..${sep}`)");
  expect(updater).toContain(
    "find . -mindepth 1 -maxdepth 1",
  );
  expect(updater).toContain("! -name node_modules");
  expect(updater).toContain("! -name .artifacts");
  expect(updater).toContain("tar --null -T - -cf - | tar -C /work -xf -");
  expect(updater).toContain('"--update-snapshots=changed"');
  expect(updater).not.toContain('"--update-snapshots=all"');
  expect(updater).not.toContain("/work/node_modules:rw");
  expect(updater).not.toContain("/work/.artifacts:rw");
});

for (const view of ["concept", "theory", "quickstart", "atlas", "docs"]) {
  test(`direct Russian ${view} entry cannot paint English before localization`, async ({
    page,
  }) => {
    let releaseApp;
    const appGate = new Promise((resolve) => {
      releaseApp = resolve;
    });
    await page.route("**/app.js", async (route) => {
      await appGate;
      await route.continue();
    });

    await page.goto(`/?lang=ru#${view}`, { waitUntil: "commit" });
    await page.waitForSelector("body", { state: "attached" });
    await page.waitForTimeout(150);

    await expect(page.locator("html")).toHaveAttribute("lang", "ru");
    await expect(page.locator("html")).toHaveAttribute(
      "data-language-pending",
      "ru",
    );
    expect(
      await page.evaluate(() => getComputedStyle(document.body).visibility),
    ).toBe("hidden");
    expect(
      await page.evaluate(
        () => performance.getEntriesByName("first-contentful-paint").length,
      ),
      "English content must not become the first contentful paint",
    ).toBe(0);

    releaseApp();
    await page.waitForLoadState("domcontentloaded");
    await expect(page.locator("html")).not.toHaveAttribute(
      "data-language-pending",
      "ru",
    );
    await expect(page.locator(`[data-view="${view}"]`)).toHaveClass(
      /\bis-active\b/,
    );
    await expect(page.locator(".menu-switch")).toContainText("Меню");
    await expect(page.locator(".view-tabs")).toHaveAttribute(
      "aria-label",
      "Основная навигация",
    );
    expect(
      await page.evaluate(() => getComputedStyle(document.body).visibility),
    ).toBe("visible");
  });
}

test("Atlas modal isolates the exact background and exposes one Close", async ({ page }) => {
  await openView(page, "atlas", "en");
  await page.locator('[data-loop-id="system-evolution"]').click();

  const inspector = page.locator("[data-atlas-inspector]");
  await expect(inspector).toBeVisible();
  for (const selector of [
    ".site-header",
    ".atlas-commandbar",
    ".atlas-navigation",
    "[data-atlas-stage]",
    ".evolution-circuit",
    ".full-outline",
    ".site-footer",
  ]) {
    await expect(page.locator(selector)).toHaveAttribute("inert", "");
  }

  const scrim = page.locator("[data-atlas-inspector-scrim]");
  await expect(scrim).toBeVisible();
  await expect(scrim).toHaveAttribute("aria-hidden", "true");
  expect(await scrim.evaluate((element) => element.tabIndex)).toBe(-1);
  await expect(scrim).not.toHaveAttribute("role", "button");
  await expect(
    page.getByRole("button", { name: "Close cycle details" }),
  ).toHaveCount(1);

  await page.keyboard.press("Escape");
  await expect(inspector).toBeHidden();
  for (const selector of [
    ".site-header",
    ".atlas-commandbar",
    ".atlas-navigation",
    "[data-atlas-stage]",
    ".evolution-circuit",
    ".full-outline",
    ".site-footer",
  ]) {
    await expect(page.locator(selector)).not.toHaveAttribute("inert", "");
  }
});

test("an interrupted Atlas open cannot reopen or steal focus", async ({ page }) => {
  await page.setViewportSize({ width: 844, height: 390 });
  await openView(page, "atlas", "en");
  const trigger = page.locator('[data-loop-id="system-evolution"]');
  const inspector = page.locator("[data-atlas-inspector]");

  await trigger.evaluate((node) => {
    node.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    document.dispatchEvent(new KeyboardEvent("keydown", {
      bubbles: true,
      cancelable: true,
      key: "Escape",
    }));
  });
  await page.waitForTimeout(100);

  await expect(inspector).toHaveAttribute("aria-hidden", "true");
  await expect(inspector).not.toHaveClass(/\bis-open\b/);
  await expect(page.locator("[data-atlas-inspector-scrim]")).toBeHidden();
  await expect(trigger).toBeFocused();

  for (let attempt = 0; attempt < 10; attempt += 1) {
    await trigger.click();
    await page.keyboard.press("Escape");
    await page.waitForTimeout(25);
    await expect(inspector).toHaveAttribute("aria-hidden", "true");
    await expect(inspector).not.toHaveClass(/\bis-open\b/);
  }
});

test("Atlas close remains visible for its return motion", async ({ page }) => {
  await openView(page, "atlas", "en");
  await page.locator('[data-loop-id="system-evolution"]').click();
  const inspector = page.locator("[data-atlas-inspector]");
  await expect(inspector).toBeVisible();

  const evidence = await inspector.evaluate(async (element) => {
    await Promise.allSettled(element.getAnimations().map((animation) => animation.finished));

    element.querySelector("[data-atlas-inspector-close]").click();
    const ariaHiddenAfterClick = element.getAttribute("aria-hidden");
    const visibilityDuringMotion = getComputedStyle(element).visibility;
    const closingTransition = element
      .getAnimations()
      .find((animation) => animation.transitionProperty === "transform");
    const transitionDuration = closingTransition
      ? closingTransition.effect.getComputedTiming().duration
      : 0;
    const transitionState = closingTransition?.playState ?? "missing";

    if (closingTransition) {
      await closingTransition.finished;
    }
    return {
      ariaHiddenAfterClick,
      finalVisibility: getComputedStyle(element).visibility,
      transitionDuration,
      transitionState,
      visibilityDuringMotion,
    };
  });

  await expect(inspector).toHaveAttribute("aria-hidden", "true");
  expect(evidence.ariaHiddenAfterClick).toBe("true");
  expect(evidence.transitionState).toBe("running");
  expect(evidence.transitionDuration).toBeGreaterThan(0);
  expect(evidence.visibilityDuringMotion).toBe("visible");
  expect(evidence.finalVisibility).toBe("hidden");
  await expect(inspector).toBeHidden();
});

test.describe("JavaScript disabled", () => {
  test.use({ javaScriptEnabled: false });

  for (const viewport of [
    { width: 390, height: 844 },
    { width: 1440, height: 900 },
  ]) {
    test(`reading mode is honest and usable at ${viewport.width}px`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await page.goto("/#concept");
      await expect(page.locator("html")).toHaveClass(/\bno-js\b/);
      await expect(page.locator(".menu-switch")).toBeHidden();
      await expect(page.locator("#primary-nav")).toBeVisible();
      expect(
        await page.locator("#primary-nav a").evaluateAll(
          (links) => links.filter((link) => {
            const box = link.getBoundingClientRect();
            return box.width > 0 && box.height > 0;
          }).length,
        ),
      ).toBeGreaterThanOrEqual(3);

      const hiddenReveals = await page.locator(".reveal").evaluateAll((elements) =>
        elements
          .filter((element) => {
            const box = element.getBoundingClientRect();
            return box.width > 0 && box.height > 0;
          })
          .filter((element) => {
            const style = getComputedStyle(element);
            return Number.parseFloat(style.opacity) < 0.99;
          })
          .map((element) => element.className),
      );
      expect(hiddenReveals).toEqual([]);

      for (const view of ["theory", "quickstart"]) {
        const prose = page.locator(`[data-view="${view}"] .prose`);
        await expect(prose).toBeVisible();
        expect((await prose.innerText()).length).toBeGreaterThan(1_000);
      }
      await expect(page.locator('[data-view="docs"]')).toBeVisible();
      await expect(
        page.getByRole("link", { name: "English documentation" }),
      ).toBeVisible();
      await expect(page.locator(".atlas-view")).toBeHidden();
      const visibleAtlasLinks = await page.locator('a[href^="#atlas"]').evaluateAll(
        (links) => links
          .filter((link) => {
            const box = link.getBoundingClientRect();
            const style = getComputedStyle(link);
            return box.width > 0
              && box.height > 0
              && style.display !== "none"
              && style.visibility !== "hidden";
          })
          .map((link) => ({
            href: link.getAttribute("href"),
            text: link.textContent.trim(),
          })),
      );
      expect(
        visibleAtlasLinks,
        "reading mode must not expose links to the unavailable interactive Atlas",
      ).toEqual([]);
      await expect(page.locator(".hero-map")).toBeHidden();
      await expect(page.locator("[data-atlas-entry]")).toBeHidden();
      const banner = page.locator(".noscript-banner");
      await expect(banner).toBeVisible();
      await expect(banner).toContainText(
        "The interactive Atlas requires JavaScript",
      );
      const bannerRect = await banner.evaluate((element) => {
        const box = element.getBoundingClientRect();
        return {
          bottom: box.bottom,
          height: box.height,
          top: box.top,
        };
      });
      expect(bannerRect.height).toBeGreaterThan(0);
      expect(bannerRect.top).toBeGreaterThanOrEqual(0);
      expect(bannerRect.bottom).toBeLessThanOrEqual(viewport.height);
    });
  }
});

test("all localized inspector titles preserve complete words", async ({ page }) => {
  const viewports = [
    { width: 360, height: 800 },
    { width: 390, height: 844 },
    { width: 844, height: 390 },
    { width: 768, height: 1024 },
    { width: 1024, height: 768 },
    { width: 1440, height: 900 },
    { width: 1920, height: 1080 },
  ];
  const failures = [];

  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    await openView(page, "atlas", "ru");
    await page.locator(".graph-node.is-current").click();
    await expect(page.locator("[data-atlas-inspector]")).toBeVisible();
    await page.evaluate(() => document.fonts.ready);

    const result = await page.evaluate(() => {
      const title = document.querySelector("#atlas-inspector-title");
      const labels = [...document.querySelectorAll("[data-atlas-outline] a")]
        .map((link) => link.textContent.trim());
      const brokenWords = [];
      const overflowingTitles = [];

      labels.forEach((label) => {
        title.textContent = label;
        const textNode = title.firstChild;
        for (const match of label.matchAll(/[\p{L}\p{N}]+/gu)) {
          const range = document.createRange();
          range.setStart(textNode, match.index);
          range.setEnd(textNode, match.index + match[0].length);
          const lineRects = [...range.getClientRects()]
            .filter((rect) => rect.width > 0 && rect.height > 0);
          if (lineRects.length !== 1) {
            brokenWords.push({
              label,
              lines: lineRects.length,
              word: match[0],
            });
          }
        }
        if (title.scrollWidth > title.clientWidth + 1) {
          overflowingTitles.push(label);
        }
      });

      return {
        brokenWords,
        labelCount: labels.length,
        overflowingTitles,
      };
    });

    expect(result.labelCount).toBe(65);
    failures.push(...result.brokenWords.map((failure) => ({
      ...failure,
      viewport,
    })));
    failures.push(...result.overflowingTitles.map((label) => ({
      label,
      overflow: true,
      viewport,
    })));
    await page.keyboard.press("Escape");
  }

  expect(
    failures,
    "localized inspector titles must wrap only between complete words",
  ).toEqual([]);
});

test("all visible interface targets meet 44 × 44 at accepted widths", async ({ page }) => {
  const failures = [];
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({
      width,
      height: width === 390 ? 844 : 900,
    });
    for (const view of ["concept", "theory", "quickstart", "atlas", "docs"]) {
      await openView(page, view, "en");
      if (width <= 820) {
        await page.locator(".menu-switch").click();
        await expect(page.locator("#primary-nav")).toBeVisible();
      }
      for (const failure of await visibleInteractiveTargetFailures(page)) {
        failures.push({ ...failure, view, viewportWidth: width });
      }
      if (width <= 820) await page.keyboard.press("Escape");
    }
    if (width === 1440) {
      await openView(page, "concept", "en");
      const tabs = await page.locator(".view-tab").evaluateAll((elements) =>
        elements.map((element) => {
          const box = element.getBoundingClientRect();
          return { height: box.height, width: box.width };
        }),
      );
      expect(tabs).toHaveLength(5);
      expect(tabs.filter(({ height, width: tabWidth }) =>
        height < 44 || tabWidth < 44)).toEqual([]);
    }
  }
  expect(
    failures,
    "visible interface targets must be at least 44 × 44 CSS pixels",
  ).toEqual([]);
});

test("mobile and tablet Atlas connectors use clear trunks and branches", async ({ page }) => {
  for (const width of [390, 768, 1024]) {
    await page.setViewportSize({
      width,
      height: width === 390 ? 844 : 900,
    });
    await openView(page, "atlas", "en");
    const geometry = await page.locator("[data-atlas-graph]").evaluate((svg) => {
      const children = svg.querySelectorAll(".graph-node:not(.is-current)").length;
      const trunks = [...svg.querySelectorAll(".graph-link.graph-trunk")];
      const branches = [...svg.querySelectorAll(".graph-link.graph-branch")];
      const rectangles = [...svg.querySelectorAll(".node-case")].map((element) => {
        const box = element.getBoundingClientRect();
        return {
          bottom: box.bottom - 3,
          left: box.left + 3,
          right: box.right - 3,
          top: box.top + 3,
        };
      });
      const collisions = [];
      [...trunks, ...branches].forEach((path, pathIndex) => {
        const length = path.getTotalLength();
        const matrix = path.getScreenCTM();
        if (!matrix) return;
        for (let distance = 4; distance < length - 4; distance += 4) {
          const point = path.getPointAtLength(distance);
          const screen = new DOMPoint(point.x, point.y).matrixTransform(matrix);
          const rectangleIndex = rectangles.findIndex((box) =>
            screen.x > box.left && screen.x < box.right
            && screen.y > box.top && screen.y < box.bottom);
          if (rectangleIndex >= 0) {
            collisions.push({ pathIndex, rectangleIndex });
            break;
          }
        }
      });
      return {
        branchCount: branches.length,
        children,
        collisions,
        trunkCount: trunks.length,
      };
    });
    expect(geometry.trunkCount, `${width}px must use one shared trunk`).toBe(1);
    expect(
      geometry.branchCount,
      `${width}px must use one branch per child`,
    ).toBe(geometry.children);
    expect(
      geometry.collisions,
      `${width}px connectors cross a cycle card`,
    ).toEqual([]);
  }
});

for (const language of ["en", "ru"]) {
  test(`${language} mobile Docs has useful density above the fold`, async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openView(page, "docs", language);
    const density = await page.evaluate(() => {
      const hero = document.querySelector(".docs-view .reading-hero").getBoundingClientRect();
      const content = [...document.querySelectorAll(
        ".docs-view .reading-hero > :not([hidden])",
      )].map((element) => element.getBoundingClientRect());
      const contentTop = Math.min(...content.map((box) => box.top));
      const contentBottom = Math.max(...content.map((box) => box.bottom));
      const firstDocument = document.querySelector(".docs-list article")
        .getBoundingClientRect();
      return {
        emptyHeroSpace: hero.height - (contentBottom - contentTop),
        firstDocumentTop: firstDocument.top,
        groupCount: document.querySelectorAll(".docs-group").length,
        heroHeight: hero.height,
      };
    });
    expect(density.groupCount).toBeGreaterThanOrEqual(4);
    expect(density.heroHeight).toBeLessThanOrEqual(340);
    expect(density.emptyHeroSpace).toBeLessThanOrEqual(160);
    expect(density.firstDocumentTop).toBeLessThan(844);
    await expect(
      page.locator(".docs-list a .ui-icon-external").first(),
    ).toBeVisible();
  });
}

test("design-system.css contains no raw color literals", async ({ browser }) => {
  const css = readFileSync("site/design-system.css", "utf8");
  const app = readFileSync("site/app.js", "utf8");
  const contract = JSON.parse(
    readFileSync("design/frontend/visual-contract.json", "utf8"),
  );
  const packageData = JSON.parse(readFileSync("package.json", "utf8"));
  const packageLock = JSON.parse(readFileSync("package-lock.json", "utf8"));
  const manifest = JSON.parse(
    readFileSync("design/frontend/baselines/manifest.json", "utf8"),
  );
  const playwrightConfig = readFileSync("playwright.config.js", "utf8");
  const workflow = readFileSync(".github/workflows/frontend.yml", "utf8");
  const offenders = css.split("\n").flatMap((line, index) => {
    const literals = [
      ...line.matchAll(/#[0-9a-f]{3,8}\b/gi),
      ...line.matchAll(/\b(?:rgb|hsl)a?\(/gi),
      ...line.matchAll(/:\s*(?:black|white|red|blue|green|yellow|gray|grey)\b/gi),
    ];
    return literals.map((match) => ({
      line: index + 1,
      literal: match[0],
    }));
  });
  expect(offenders).toEqual([]);
  expect(app).not.toMatch(/[↗→＋]/u);
  expect(contract.baseline_policy.ci_may_update).toBe(false);
  expect(contract.baseline_policy.font_fallback_icons_forbidden).toBe(true);
  expect(contract.baseline_policy.canonical_renderer).toMatchObject({
    browser: "chromium",
    browser_revision: "1234",
    browser_version: "151.0.7922.34",
    generation_command: "npm run test:frontend:evidence:update",
    playwright_version: "1.62.0",
  });
  expect(
    contract.baseline_policy.canonical_renderer.container_image,
  ).toContain("@sha256:");
  expect(
    packageLock.packages["node_modules/@playwright/test"].version,
  ).toBe(contract.baseline_policy.canonical_renderer.playwright_version);
  expect(browser.version()).toBe(
    contract.baseline_policy.canonical_renderer.browser_version,
  );
  expect(packageData.scripts["test:frontend:evidence:update"]).toBe(
    "node tests/frontend/update-visual-baselines.mjs",
  );
  expect(playwrightConfig).toContain('updateSnapshots: "none"');
  expect(playwrightConfig).toContain("maxDiffPixelRatio: 0.0001");
  expect(workflow).toContain(
    ".artifacts/playwright/signal-canvas-report",
  );
  expect(workflow).toContain(
    ".artifacts/playwright/signal-canvas-results",
  );
  expect(workflow).toContain(
    `image: ${contract.baseline_policy.canonical_renderer.container_image}`,
  );
  expect(workflow).not.toMatch(/\.artifacts\/playwright\/(?:report|results)\n/);
  expect(workflow).not.toContain("test:frontend:evidence:update");
  expect(manifest.renderer.container_image).toBe(
    contract.baseline_policy.canonical_renderer.container_image,
  );
  expect(manifest.renderer.source_files).toHaveLength(
    contract.baseline_policy.canonical_renderer.source_files.length,
  );
  for (const source of manifest.renderer.source_files) {
    const actual = `sha256:${createHash("sha256")
      .update(readFileSync(source.path))
      .digest("hex")}`;
    expect(source.sha256, source.path).toBe(actual);
  }
  const refusal = spawnSync(
    process.execPath,
    ["tests/frontend/update-visual-baselines.mjs"],
    {
      encoding: "utf8",
      env: { ...process.env, CI: "1" },
    },
  );
  expect(refusal.status).toBe(2);
  expect(`${refusal.stdout}${refusal.stderr}`).toContain(
    "Refusing to update accepted visual baselines in CI",
  );
});

test("Russian Atlas keeps human copy in the primary interface", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openView(page, "atlas", "ru", "system-evolution");

  const provenance = page.locator("[data-atlas-provenance]");
  await expect(provenance).toHaveText("Из принятой карты проекта");
  await expect(provenance).not.toContainText("sha256:");

  const visibleCopy = await page.locator("#atlas").innerText();
  expect(visibleCopy).not.toMatch(/\b(?:Atlas|CLI|runner)\b/);

  await page.locator(".graph-node.is-current").click();
  const humanDetails = await page.locator("[data-atlas-inspector]").innerText();
  expect(humanDetails).not.toMatch(
    /\b(?:Atlas|CLI|runner|Playwright|HTTP|DOM)\b/,
  );
  await page.locator(".technical-details").evaluate((details) => {
    details.open = true;
  });
  await expect(page.locator(".technical-details code").last()).toContainText(
    "sha256:",
  );
  await expect(page.locator("[data-atlas-binding]")).not.toHaveAttribute(
    "title",
    /sha256:/,
  );
  await page.keyboard.press("Escape");

  for (const [cycle, expectedOutput] of [
    [
      "project-atlas",
      "Детерминированная проекция Атласа только для чтения.",
    ],
    [
      "maintain-automation",
      "Плагин, инструкция для помощника или набор проверок с явными ограничениями.",
    ],
    [
      "maintain-frontend-verification",
      "Зафиксированный набор браузерных проверок доступности с отдельно принятыми эталонными снимками.",
    ],
    [
      "verify-live-release",
      "Данные о сетевом ответе и структуре страницы, а также снимки экрана.",
    ],
    [
      "maintain-component-workshop",
      "Локальная мастерская с компонентами в обычном состоянии, с длинным текстом, при загрузке, без данных, с ошибкой и с устаревшими данными.",
    ],
  ]) {
    await openView(page, "atlas", "ru", cycle);
    await page.locator(".graph-node.is-current").click();
    await expect(
      page.locator(".inspector-contract > div:nth-child(2) dd"),
    ).toHaveText(expectedOutput);
    await page.keyboard.press("Escape");
  }
});

test("roadmap prioritization is explained in plain EN and RU", async ({ page }) => {
  for (const [language, purpose, output, forbidden] of [
    [
      "en",
      "Choose what to do first based on goals, time and available resources.",
      "A list of next steps in execution order.",
      /bounded outcomes/i,
    ],
    [
      "ru",
      "Выбрать, что делать сначала, с учётом целей, сроков и доступных ресурсов.",
      "Список следующих шагов в порядке выполнения.",
      /ограниченн(?:ые|ых|ыми).+ограничен/i,
    ],
  ]) {
    await openView(page, "atlas", language, "prioritize-roadmap");
    await page.locator(".graph-node.is-current").click();
    const inspector = page.locator("[data-atlas-inspector]");
    await expect(inspector.locator(".inspector-purpose")).toHaveText(purpose);
    await expect(
      inspector.locator(".inspector-contract > div:nth-child(2) dd"),
    ).toHaveText(output);
    expect(await inspector.innerText()).not.toMatch(forbidden);
    await page.keyboard.press("Escape");
  }
});

test("mobile Atlas path never clips its current Russian label", async ({ page }) => {
  for (const width of [360, 390]) {
    await page.setViewportSize({ width, height: 844 });
    await openView(page, "atlas", "ru", "system-evolution");
    const current = page.locator(".atlas-breadcrumbs [aria-current=page]");
    await expect(current).toHaveText("Эволюция системы");
    const geometry = await current.evaluate((element) => ({
      clientHeight: element.clientHeight,
      clientWidth: element.clientWidth,
      scrollHeight: element.scrollHeight,
      scrollWidth: element.scrollWidth,
    }));
    expect(geometry.scrollWidth).toBeLessThanOrEqual(geometry.clientWidth + 1);
    expect(geometry.scrollHeight).toBeLessThanOrEqual(geometry.clientHeight + 1);
  }
});

test("phone landscape Atlas keeps every root and nested node inside the stage", async ({
  page,
}) => {
  await page.setViewportSize({ width: 844, height: 390 });
  for (const language of ["en", "ru"]) {
    for (const cycle of [undefined, "system-evolution"]) {
      await openView(page, "atlas", language, cycle);
      await expect(page.locator("[data-atlas-stage]")).toHaveAttribute(
        "data-layout",
        "landscape",
      );
      const geometry = await page.locator("[data-atlas-stage]").evaluate((stage) => {
        const stageBox = stage.getBoundingClientRect();
        const nodes = [...stage.querySelectorAll(".node-hit")].map((node) => {
          const box = node.getBoundingClientRect();
          return {
            bottom: box.bottom,
            left: box.left,
            right: box.right,
            top: box.top,
          };
        });
        return {
          clipped: nodes.filter((box) =>
            box.left < stageBox.left - 1
            || box.right > stageBox.right + 1
            || box.top < stageBox.top - 1
            || box.bottom > stageBox.bottom + 1
            || box.bottom > innerHeight + 1),
          nodeCount: nodes.length,
          stageBottom: stageBox.bottom,
        };
      });
      expect(geometry.nodeCount).toBeGreaterThan(1);
      expect(geometry.stageBottom).toBeLessThanOrEqual(391);
      expect(
        geometry.clipped,
        `${language}/${cycle || "root"} has clipped landscape nodes`,
      ).toEqual([]);
    }
  }
});

test("phone landscape details expose the primary action before the fold", async ({
  page,
}) => {
  await page.setViewportSize({ width: 844, height: 390 });
  await openView(page, "atlas", "ru");
  await page.locator('[data-loop-id="system-evolution"]').click();
  const action = page.locator(".inspector-open-cycle");
  await expect(action).toBeVisible();
  await expect(action.locator(".ui-icon-arrow-right")).toHaveCount(1);
  await expect(page.locator(".inspector-dial .ui-icon-plus")).toHaveCount(1);
  const box = await action.boundingBox();
  expect(box.y + box.height).toBeLessThanOrEqual(390);
  await expect(page.locator(".inspector-more-cue")).toBeVisible();
});
