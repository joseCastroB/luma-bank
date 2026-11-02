import { defineConfig, devices } from "@playwright/test";
import { ARCHIVO_SESION } from "./e2e/datos";

// Fuera de apps/frontend: Vite vigila esa carpeta y recargaría la página con cada captura.
const SALIDA = "../../e2e-resultados";

// Las pruebas comparten clientes y saldos: corren en serie, con un solo worker.
export default defineConfig({
  testDir: "./e2e",
  outputDir: `${SALIDA}/artefactos`,
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ["list"],
    ["html", { outputFolder: `${SALIDA}/html`, open: "never" }],
    ["json", { outputFile: `${SALIDA}/resultados.json` }],
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
  projects: [
    { name: "sesion", testMatch: /sesion\.setup\.ts/ },
    { name: "funcional-publico", testMatch: /(publico|registro|login)\.spec\.ts/ },
    {
      name: "funcional-banca",
      testMatch: /banca\.spec\.ts/,
      dependencies: ["sesion"],
      use: { storageState: ARCHIVO_SESION },
    },
    {
      name: "usabilidad",
      testMatch: /usabilidad\.spec\.ts/,
      dependencies: ["sesion"],
      use: { storageState: ARCHIVO_SESION },
    },
  ],
});
