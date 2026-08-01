const { expect } = require("@playwright/test");

function siteUrl(view = "concept", language = "en", detail = "") {
  const query = language === "en" ? "" : "?lang=ru";
  const suffix = detail ? `/${encodeURIComponent(detail)}` : "";
  return `/${query}#${view}${suffix}`;
}

async function waitForSite(page) {
  await page.waitForLoadState("domcontentloaded");
  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
    await Promise.all(
      [...document.images].map((image) => {
        if (image.complete) return Promise.resolve();
        return new Promise((resolve) => {
          image.addEventListener("load", resolve, { once: true });
          image.addEventListener("error", resolve, { once: true });
        });
      }),
    );
  });
  await expect(page.locator("[data-atlas-count]")).not.toHaveText("0");
}

async function openView(page, view, language = "en", detail = "") {
  await page.goto(siteUrl(view, language, detail));
  await waitForSite(page);
  await expect(page.locator("html")).toHaveAttribute("lang", language);
  await expect(page.locator(`[data-view="${view}"]`)).toHaveClass(/\bis-active\b/);
}

async function activeView(page) {
  return page.locator("[data-view].is-active");
}

async function visibleBoxes(locator) {
  return locator.evaluateAll((elements) =>
    elements
      .filter((element) => {
        const style = getComputedStyle(element);
        const box = element.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden"
          && box.width > 0 && box.height > 0;
      })
      .map((element) => {
        const box = element.getBoundingClientRect();
        return {
          label:
            element.getAttribute("aria-label")
            || element.textContent?.trim().replace(/\s+/g, " ").slice(0, 80)
            || element.tagName,
          left: box.left,
          top: box.top,
          right: box.right,
          bottom: box.bottom,
          width: box.width,
          height: box.height,
        };
      }),
  );
}

function intersectionArea(first, second) {
  const width = Math.max(0, Math.min(first.right, second.right) - Math.max(first.left, second.left));
  const height = Math.max(0, Math.min(first.bottom, second.bottom) - Math.max(first.top, second.top));
  return width * height;
}

async function expectNoPairwiseOverlap(locator, tolerance = 1) {
  const boxes = await visibleBoxes(locator);
  const collisions = [];
  for (let left = 0; left < boxes.length; left += 1) {
    for (let right = left + 1; right < boxes.length; right += 1) {
      const area = intersectionArea(boxes[left], boxes[right]);
      if (area > tolerance) {
        collisions.push({
          first: boxes[left].label,
          second: boxes[right].label,
          overlapPixels: Math.round(area),
        });
      }
    }
  }
  expect(collisions, "visible elements overlap").toEqual([]);
}

async function expectNoHorizontalOverflow(page) {
  const result = await page.evaluate(() => {
    const viewportWidth = document.documentElement.clientWidth;
    const offenders = [...document.querySelectorAll("body *")]
      .filter((element) => {
        const style = getComputedStyle(element);
        if (style.display === "none" || style.visibility === "hidden") return false;
        const box = element.getBoundingClientRect();
        return box.width > 0 && (box.left < -1 || box.right > viewportWidth + 1);
      })
      .map((element) => ({
        selector:
          element.id ? `#${element.id}` : `${element.tagName.toLowerCase()}.${[...element.classList].join(".")}`,
        text: element.textContent?.trim().replace(/\s+/g, " ").slice(0, 60),
        box: Object.fromEntries(
          ["left", "right", "width"].map((key) => [key, Math.round(element.getBoundingClientRect()[key])]),
        ),
      }))
      .slice(0, 20);
    return {
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth,
      offenders,
    };
  });
  expect(result.documentWidth, JSON.stringify(result, null, 2)).toBeLessThanOrEqual(
    result.viewportWidth + 1,
  );
  return result;
}

async function expectContained(children, container) {
  const outer = await container.boundingBox();
  expect(outer, "container must be visible").not.toBeNull();
  const boxes = await visibleBoxes(children);
  const escaped = boxes.filter(
    (box) =>
      box.left < outer.x - 1
      || box.top < outer.y - 1
      || box.right > outer.x + outer.width + 1
      || box.bottom > outer.y + outer.height + 1,
  );
  expect(escaped, "visible children escape their container").toEqual([]);
}

async function visibleInteractiveTargetFailures(page, minimum = 44) {
  return page.evaluate((targetMinimum) => {
    const proseInline = ".prose p a, .prose li a, .prose td a, .prose dd a";
    return [...document.querySelectorAll(
      "a[href], button:not([disabled]), summary, [role='button'], "
        + "[tabindex]:not([tabindex='-1'])",
    )]
      .filter((element) => {
        if (element.matches(proseInline)) return false;
        if (element.closest("[inert], [aria-hidden='true']")) return false;
        const style = getComputedStyle(element);
        const box = element.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden"
          && box.width > 0 && box.height > 0;
      })
      .map((element) => {
        const box = element.getBoundingClientRect();
        return {
          height: box.height,
          label:
            element.getAttribute("aria-label")
            || element.textContent?.trim().replace(/\s+/g, " ").slice(0, 80)
            || element.tagName,
          tagName: element.tagName,
          width: box.width,
        };
      })
      .filter(({ height, width }) => height < targetMinimum || width < targetMinimum);
  }, minimum);
}

async function expectAllVisibleInteractiveTargets(page, minimum = 44) {
  const undersized = await visibleInteractiveTargetFailures(page, minimum);
  expect(
    undersized,
    `visible interface targets must be at least ${minimum} × ${minimum} CSS pixels`,
  ).toEqual([]);
}

module.exports = {
  activeView,
  expectAllVisibleInteractiveTargets,
  expectContained,
  expectNoHorizontalOverflow,
  expectNoPairwiseOverlap,
  openView,
  siteUrl,
  visibleInteractiveTargetFailures,
  visibleBoxes,
  waitForSite,
};
