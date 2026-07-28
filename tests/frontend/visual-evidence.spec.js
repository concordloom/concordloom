const path = require("node:path");
const { test, expect } = require("./support/test");
const {
  expectNoHorizontalOverflow,
  openView,
} = require("./support/site");

const reference = path.resolve(
  __dirname,
  "../../design/frontend/reference/signal-constellation-concept.png",
);

for (const language of ["en", "ru"]) {
  for (const view of ["concept", "atlas"]) {
    test(`${language} ${view} visual review evidence`, async ({ page }, testInfo) => {
      await openView(page, view, language);
      await expectNoHorizontalOverflow(page);
      await testInfo.attach("approved-concept-reference", {
        path: reference,
        contentType: "image/png",
      });
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
      expect(screenshot.byteLength).toBeGreaterThan(50_000);
    });
  }
}
