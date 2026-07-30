const path = require("node:path");
const { test, expect } = require("./support/test");
const {
  expectNoHorizontalOverflow,
  openView,
} = require("./support/site");
const visualContract = require("../../design/frontend/visual-contract.json");

const references = [
  {
    name: "patch-panel-concept",
    path: path.resolve(
      __dirname,
      "../../design/frontend/startup-atlas-concepts/playful/04-patch-panel/index.html",
    ),
    contentType: "text/html",
  },
  {
    name: "patch-panel-style",
    path: path.resolve(
      __dirname,
      "../../design/frontend/startup-atlas-concepts/playful/04-patch-panel/style.css",
    ),
    contentType: "text/css",
  },
  {
    name: "accepted-visual-contract",
    path: path.resolve(
      __dirname,
      "../../design/frontend/visual-contract.json",
    ),
    contentType: "application/json",
  },
];

for (const language of ["en", "ru"]) {
  for (const view of visualContract.acceptance.routes) {
    test(`${language} ${view} Patch Panel review evidence`, async ({ page }, testInfo) => {
      await openView(page, view, language);
      await expectNoHorizontalOverflow(page);
      await expect(page.locator("body")).toHaveAttribute(
        "data-design-system",
        "patch-panel",
      );
      if (view === "atlas") {
        await expect(page.locator(".graph-node.is-current")).toHaveCount(1);
        await expect(page.locator(".node-assembly")).not.toHaveCount(0);
        await expect(page.locator("[data-atlas-inspector]")).toBeHidden();
        const stageImage = await page.locator(".atlas-stage").evaluate(
          (element) => getComputedStyle(element).backgroundImage,
        );
        expect(stageImage).toBe("none");
      }
      for (const reference of references) {
        await testInfo.attach(reference.name, {
          path: reference.path,
          contentType: reference.contentType,
        });
      }
      const screenshot = await page.screenshot({
        animations: "disabled",
        caret: "hide",
        fullPage: false,
        scale: "css",
      });
      await testInfo.attach(`${language}-${view}-${testInfo.project.name}`, {
        body: screenshot,
        contentType: "image/png",
      });
      expect(screenshot.byteLength).toBeGreaterThan(25_000);
    });
  }
}
