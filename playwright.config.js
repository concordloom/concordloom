const { defineConfig, devices } = require("@playwright/test");

const shared = {
  baseURL: "http://127.0.0.1:4173",
  colorScheme: "dark",
  locale: "en-US",
  reducedMotion: "no-preference",
  serviceWorkers: "block",
  timezoneId: "UTC",
  trace: "retain-on-failure",
  screenshot: "only-on-failure",
  video: "retain-on-failure",
};

module.exports = defineConfig({
  testDir: "./tests/frontend",
  testMatch: "**/*.spec.js",
  outputDir: ".artifacts/playwright/results",
  snapshotPathTemplate:
    "tests/frontend/__screenshots__/{projectName}/{testFilePath}/{arg}{ext}",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  workers: process.env.CI ? 1 : undefined,
  timeout: 30_000,
  expect: {
    timeout: 5_000,
    toHaveScreenshot: {
      animations: "disabled",
      caret: "hide",
      maxDiffPixelRatio: 0.0001,
      scale: "css",
    },
  },
  reporter: [
    ["line"],
    [
      "html",
      {
        open: "never",
        outputFolder: ".artifacts/playwright/report",
        title: "Concord Loom frontend verification",
      },
    ],
  ],
  use: shared,
  webServer: {
    command: "node tests/frontend/server.mjs",
    url: "http://127.0.0.1:4173/",
    reuseExistingServer: !process.env.CI,
    stdout: "ignore",
    stderr: "pipe",
    timeout: 15_000,
  },
  projects: [
    {
      name: "desktop-chromium",
      testIgnore: [/browser-smoke\.spec\.js/, /visual-evidence\.spec\.js/],
      use: {
        ...devices["Desktop Chrome"],
        ...shared,
        deviceScaleFactor: 1,
        viewport: { width: 1440, height: 1000 },
      },
    },
    {
      name: "mobile-chromium",
      testIgnore: [/browser-smoke\.spec\.js/, /visual-evidence\.spec\.js/],
      use: {
        ...devices["Pixel 5"],
        ...shared,
        deviceScaleFactor: 1,
        viewport: { width: 390, height: 844 },
      },
    },
    {
      name: "firefox-smoke",
      testMatch: /browser-smoke\.spec\.js/,
      use: {
        ...devices["Desktop Firefox"],
        ...shared,
        deviceScaleFactor: 1,
        viewport: { width: 1440, height: 1000 },
      },
    },
    {
      name: "webkit-smoke",
      testMatch: /browser-smoke\.spec\.js/,
      use: {
        ...devices["iPhone 13"],
        ...shared,
        deviceScaleFactor: 1,
        viewport: { width: 390, height: 844 },
      },
    },
    {
      name: "visual-desktop",
      testMatch: /visual-evidence\.spec\.js/,
      use: {
        ...devices["Desktop Chrome"],
        ...shared,
        deviceScaleFactor: 1,
        reducedMotion: "reduce",
        viewport: { width: 2048, height: 1152 },
      },
    },
    {
      name: "visual-mobile",
      testMatch: /visual-evidence\.spec\.js/,
      use: {
        ...devices["Pixel 5"],
        ...shared,
        deviceScaleFactor: 1,
        reducedMotion: "reduce",
        viewport: { width: 390, height: 844 },
      },
    },
  ],
});
