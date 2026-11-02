import { expect, test, type Page } from "@playwright/test";

// La cámara simulada no puede superar la prueba de vida: el flujo se valida hasta ese paso.
// El alta completa (cifrado y creación de la cuenta) la cubre apps/accounts/tests/test_registro_api.py.
test.use({
  permissions: ["camera"],
  launchOptions: {
    args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
  },
});

function dniNuevo() {
  return `7${String(Math.floor(Math.random() * 10_000_000)).padStart(7, "0")}`;
}

async function llegarAlPasoDeDatos(page: Page) {
  const dni = dniNuevo();
  await page.goto("/registro");
  await page.getByLabel("Número de DNI").fill(dni);
  await page.getByRole("button", { name: "Continuar" }).click();
  await expect(page.getByText(`DNI ${dni}`)).toBeVisible();
  await page.getByRole("button", { name: "Sí, soy yo" }).click();
  await expect(page.getByLabel("Correo electrónico")).toBeVisible();
}

test.describe("HU02 Registro y apertura de cuenta", () => {
  test("CP-F06 un DNI con formato inválido no puede continuar", async ({ page }) => {
    await page.goto("/registro");
    await page.getByLabel("Número de DNI").fill("1234");
    await expect(page.getByText("Deben ser exactamente 8 dígitos.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Continuar" })).toBeDisabled();
  });

  test("CP-F07 un DNI válido muestra la identidad para confirmarla", async ({ page }) => {
    const dni = dniNuevo();
    await page.goto("/registro");
    await page.getByLabel("Número de DNI").fill(dni);
    await page.getByRole("button", { name: "Continuar" }).click();
    await expect(page.getByText("Según RENIEC")).toBeVisible();
    await expect(page.getByText(`DNI ${dni}`)).toBeVisible();
    await expect(page.getByText("¿Eres tú?")).toBeVisible();
  });

  test("CP-F08 'No, corregir DNI' vuelve al primer paso", async ({ page }) => {
    await page.goto("/registro");
    await page.getByLabel("Número de DNI").fill(dniNuevo());
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.getByRole("button", { name: "No, corregir DNI" }).click();
    await expect(page.getByLabel("Número de DNI")).toBeVisible();
  });

  test("CP-F09 rechaza a un menor de 18 años", async ({ page }) => {
    await llegarAlPasoDeDatos(page);
    const hace10Anios = new Date();
    hace10Anios.setFullYear(hace10Anios.getFullYear() - 10);
    await page.getByLabel("Correo electrónico").fill("nuevo@lumabank.test");
    await page.getByLabel("Fecha de nacimiento").fill(hace10Anios.toISOString().slice(0, 10));
    await page.getByLabel("Contraseña", { exact: true }).fill("Clave-Larga-2026");
    await page.getByLabel("Repite la contraseña").fill("Clave-Larga-2026");
    await page.getByRole("button", { name: "Continuar" }).click();
    await expect(page.getByText("Debes ser mayor de 18 años para abrir una cuenta.")).toBeVisible();
  });

  test("CP-F10 exige una contraseña larga y que ambas coincidan", async ({ page }) => {
    await llegarAlPasoDeDatos(page);
    await page.getByLabel("Contraseña", { exact: true }).fill("corta");
    await page.getByLabel("Repite la contraseña").fill("distinta");
    await page.getByRole("button", { name: "Continuar" }).click();
    await expect(page.getByText("La contraseña debe tener al menos 12 caracteres.")).toBeVisible();
    await expect(page.getByText("Las contraseñas no coinciden.")).toBeVisible();
    await expect(page.getByText("Ingresa un correo válido.")).toBeVisible();
  });

  test("CP-F11 con datos válidos llega a la prueba de vida", async ({ page }) => {
    await llegarAlPasoDeDatos(page);
    await page.getByLabel("Correo electrónico").fill("nuevo@lumabank.test");
    await page.getByLabel("Fecha de nacimiento").fill("1995-05-20");
    await page.getByLabel("Contraseña", { exact: true }).fill("Clave-Larga-2026");
    await page.getByLabel("Repite la contraseña").fill("Clave-Larga-2026");
    await page.getByRole("button", { name: "Continuar" }).click();
    // No se puede crear la cuenta hasta superar la prueba de vida.
    await expect(page.getByRole("button", { name: "Crear mi cuenta" })).toBeDisabled();
  });
});
