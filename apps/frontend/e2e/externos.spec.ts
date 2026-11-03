/** Modelos de reconocimiento facial en los CDN reales. Un fallo puede ser del proveedor. */

import { expect, test, type Page } from "@playwright/test";

const ERROR_DE_MODELOS = "No se pudieron cargar los modelos de reconocimiento facial.";

test.use({
  permissions: ["camera"],
  launchOptions: {
    args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
  },
});

async function llegarALaPruebaDeVida(page: Page) {
  const dni = `7${String(Math.floor(Math.random() * 10_000_000)).padStart(7, "0")}`;
  await page.goto("/registro");
  await page.getByLabel("Número de DNI").fill(dni);
  await page.getByRole("button", { name: "Continuar" }).click();
  await page.getByRole("button", { name: "Sí, soy yo" }).click();
  await page.getByLabel("Correo electrónico").fill("nuevo@lumabank.test");
  await page.getByLabel("Fecha de nacimiento").fill("1995-05-20");
  await page.getByLabel("Contraseña", { exact: true }).fill("Clave-Larga-2026");
  await page.getByLabel("Repite la contraseña").fill("Clave-Larga-2026");
  await page.getByRole("button", { name: "Continuar" }).click();
}

test.describe("Modelos de reconocimiento facial", () => {
  test.setTimeout(120_000);

  test("CP-I01 jsDelivr y Google Cloud Storage entregan los modelos", async ({ page }) => {
    const respuestas: { url: string; ok: boolean }[] = [];
    page.on("response", (r) => {
      if (/cdn\.jsdelivr\.net|storage\.googleapis\.com/.test(r.url())) {
        respuestas.push({ url: r.url(), ok: r.ok() });
      }
    });

    await llegarALaPruebaDeVida(page);

    for (const recurso of [
      /face-api@[^/]+\/model\/ssd_mobilenetv1_model-weights_manifest\.json$/,
      /face-api@[^/]+\/model\/face_recognition_model-weights_manifest\.json$/,
      /tasks-vision@[^/]+\/wasm\/vision_wasm.*\.wasm$/,
      /storage\.googleapis\.com\/.*face_landmarker\.task$/,
    ]) {
      await expect
        .poll(() => respuestas.find((r) => recurso.test(r.url))?.ok, {
          message: `Sin respuesta correcta para ${recurso}`,
          timeout: 90_000,
        })
        .toBe(true);
    }
    expect(respuestas.filter((r) => !r.ok)).toEqual([]);
    await expect(page.getByText(ERROR_DE_MODELOS)).toBeHidden();
  });

  test("CP-I02 si el CDN no responde, se avisa al usuario", async ({ page }) => {
    await page.route(/cdn\.jsdelivr\.net|storage\.googleapis\.com/, (route) => route.abort());
    await llegarALaPruebaDeVida(page);
    await expect(page.getByText(ERROR_DE_MODELOS)).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole("button", { name: "Crear mi cuenta" })).toBeDisabled();
  });
});
