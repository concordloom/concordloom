const { test: base, expect } = require("@playwright/test");

const test = base.extend({
  diagnostics: [
    async ({ page }, use, testInfo) => {
      const consoleErrors = [];
      const pageErrors = [];
      const requestFailures = [];
      const externalRequests = [];

      page.on("console", (message) => {
        if (message.type() === "error") consoleErrors.push(message.text());
      });
      page.on("pageerror", (error) => pageErrors.push(error.message));
      page.on("requestfailed", (request) => {
        if (!request.failure()?.errorText.includes("ERR_ABORTED")) {
          requestFailures.push(`${request.method()} ${request.url()}: ${request.failure()?.errorText}`);
        }
      });
      await page.route("**/*", async (route) => {
        const url = new URL(route.request().url());
        const local =
          ["127.0.0.1", "localhost"].includes(url.hostname)
          || ["about:", "blob:", "data:"].includes(url.protocol);
        if (!local) {
          externalRequests.push(route.request().url());
          await route.abort("blockedbyclient");
          return;
        }
        await route.continue();
      });

      await use();

      const diagnostics = {
        consoleErrors,
        externalRequests,
        pageErrors,
        requestFailures,
      };
      await testInfo.attach("browser-diagnostics", {
        body: Buffer.from(JSON.stringify(diagnostics, null, 2)),
        contentType: "application/json",
      });
      if (testInfo.status === testInfo.expectedStatus) {
        expect(diagnostics).toEqual({
          consoleErrors: [],
          externalRequests: [],
          pageErrors: [],
          requestFailures: [],
        });
      }
    },
    { auto: true },
  ],
});

module.exports = { test, expect };
