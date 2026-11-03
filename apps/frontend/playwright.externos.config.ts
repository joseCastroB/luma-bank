import { defineConfig, devices } from "@playwright/test";

const SALIDA = "../../e2e-resultados/externos";

// Separado de la suite E2E: depende de servicios de terceros por internet.
export default defineConfig({
  testDir: "./e2e",
  testMatch: /externos\.spec\.ts/,
  outputDir: `${SALIDA}/artefactos`,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  reporter: [
    ["list"],
    ["html", { outputFolder: `${SALIDA}/html`, open: "never" }],
    ["junit", { outputFile: `${SALIDA}/junit.xml` }],
  ],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    locale: "es-PE",
    timezoneId: "America/Lima",
    screenshot: "on",
    trace: "retain-on-failure",
  },
});
