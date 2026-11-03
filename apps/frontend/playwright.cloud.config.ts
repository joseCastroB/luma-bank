import { defineConfig, devices } from "@playwright/test";

export const FRONT_CLOUD = process.env.E2E_BASE_URL ?? "https://luma-bank-68g4.onrender.com";
export const API_CLOUD = process.env.E2E_API_URL ?? "https://luma-bank-api.onrender.com";

const SALIDA = "../../e2e-resultados/cloud";

// Render apaga los servicios sin uso: la primera respuesta puede tardar cerca de un minuto.
export default defineConfig({
  testDir: "./e2e",
  testMatch: /cloud\.spec\.ts/,
  outputDir: `${SALIDA}/artefactos`,
  workers: 1,
  timeout: 120_000,
  retries: 1,
  forbidOnly: Boolean(process.env.CI),
  reporter: [
    ["list"],
    ["html", { outputFolder: `${SALIDA}/html`, open: "never" }],
    ["json", { outputFile: `${SALIDA}/resultados.json` }],
    ["junit", { outputFile: `${SALIDA}/junit.xml` }],
  ],
  use: {
    ...devices["Desktop Chrome"],
    baseURL: FRONT_CLOUD,
    locale: "es-PE",
    timezoneId: "America/Lima",
    navigationTimeout: 90_000,
    screenshot: "on",
    trace: "retain-on-failure",
  },
});
